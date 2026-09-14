"""End-to-end orchestration for the BebiBem demand analysis."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from . import figures as figure_builders
from .capacity import capacity_frame, demand_in_cases
from .classification import (
    evaluate_classifier,
    fit_regime_classifier,
    select_classification_features,
)
from .clustering import cluster_months, cluster_series, seasonal_index_matrix
from .config import (
    DEFAULT_INPUT,
    DEFAULT_OUTDIR,
    FIGURE_FORMATS,
    HOLDOUT_YEAR,
    MIN_OBS_FOR_ML,
    SEED,
)
from .features import build_features
from .forecast import fit_final, forecast_recursive, forecast_tables
from .interpolation import fill_gaps_linear, polynomial_equation_label, polynomial_fit
from .io_data import InputError, load_demand
from .models import build_estimators, cross_validate_temporal, metrics, select_best
from .plotting import save_figure
from .regression import (
    RegressionFit,
    exponential_regression_loglinear,
    exponential_regression_normal_equation,
    linear_regression_normal_equation,
)
from .smoothing import moving_average_table, validate_windows


def _validate_output_directory(outdir: Path) -> None:
    try:
        outdir.mkdir(parents=True, exist_ok=True)
        probe = outdir / ".bebibem-write-test"
        probe.touch(exist_ok=False)
        probe.unlink()
    except OSError as error:
        raise InputError(f"diretório de saída não gravável: {outdir}") from error


LOGGER = logging.getLogger(__name__)
CANONICAL_STEPS = (
    "load",
    "interp",
    "ma",
    "cluster",
    "features",
    "ml",
    "forecast",
    "capacity",
    "plots",
)
STEP_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "load": (),
    "interp": ("load",),
    "ma": ("load",),
    "cluster": ("load",),
    "features": ("load", "cluster"),
    "ml": ("load", "cluster", "features"),
    "forecast": ("load", "cluster", "features", "ml"),
    "capacity": ("load", "forecast"),
    "plots": ("load",),
}
PRODUCT_ORDER = ("suco_premium", "geleia_de_frutas", "doce_de_frutas")
MODEL_NAMES = (
    "ridge",
    "random_forest",
    "gradient_boosting",
    "linear_normal_equation",
    "exponential_loglinear",
    "exponential_normal_equation",
)


@dataclass(frozen=True)
class PipelineConfig:
    """Runtime options for the complete or partial pipeline."""

    input: Path = DEFAULT_INPUT
    outdir: Path = DEFAULT_OUTDIR
    formats: tuple[str, ...] = FIGURE_FORMATS
    poly_degree: int | None = None
    ma_windows: tuple[int, ...] = (3, 12)
    horizon_years: int = 1
    k_months: int | None = None
    units_per_case: int | None = None
    steps: tuple[str, ...] | None = None
    seed: int = SEED
    log_level: str = "WARNING"
    timeseries: bool = False


@dataclass
class PipelineResult:
    """Artifacts and business output produced by :func:`run`."""

    figures: list[Path] = field(default_factory=list)
    tables: list[Path] = field(default_factory=list)
    annual_forecast: pd.DataFrame = field(default_factory=pd.DataFrame)
    warnings: list[str] = field(default_factory=list)
    timeseries_metrics: pd.DataFrame = field(default_factory=pd.DataFrame)


def _requested_steps(requested: Iterable[str] | str | None) -> list[str]:
    if requested is None:
        return list(CANONICAL_STEPS)
    values = requested.split(",") if isinstance(requested, str) else list(requested)
    normalized = [str(value).strip().lower() for value in values if str(value).strip()]
    if len(normalized) == 0:
        return list(CANONICAL_STEPS)
    unknown = sorted(set(normalized).difference(CANONICAL_STEPS))
    if unknown:
        raise InputError(
            f"etapa(s) inválida(s): {unknown}; etapas válidas: {', '.join(CANONICAL_STEPS)}"
        )
    return normalized


def resolve_steps(requested: Iterable[str] | str | None) -> list[str]:
    """Resolve requested pipeline stages into canonical order with dependencies."""
    selected = set(_requested_steps(requested))
    pending = list(selected)
    while pending:
        step = pending.pop()
        for dependency in STEP_DEPENDENCIES[step]:
            if dependency in selected:
                continue
            selected.add(dependency)
            pending.append(dependency)
            LOGGER.info("etapa incluída automaticamente: %s (dependência de %s)", dependency, step)
    return [step for step in CANONICAL_STEPS if step in selected]


def _write_table(frame: pd.DataFrame, table_dir: Path, name: str, paths: list[Path]) -> Path:
    table_dir.mkdir(parents=True, exist_ok=True)
    path = table_dir / name
    frame.to_csv(path, index=False, lineterminator="\n")
    paths.append(path)
    return path


def _eligible_cluster_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep product histories with two annual cycles for clustering."""
    counts = frame.groupby("produto").size()
    eligible = counts[counts >= MIN_OBS_FOR_ML].index
    return frame.loc[frame["produto"].isin(eligible)].copy()


def _month_cluster_table(matrix: pd.DataFrame, result: object) -> pd.DataFrame:
    """Serialize candidate scores and month assignments in one stable table."""
    columns = ["mes", *matrix.columns, "cluster", "k", "silhouette", "selecionado", "status"]
    rows: list[dict[str, object]] = []
    scores = getattr(result, "scores", {})
    selected_k = int(getattr(result, "k", 0))
    selected_score = float(getattr(result, "silhouette", np.nan))
    for candidate, score in sorted(scores.items()):
        rows.append(
            {
                "mes": pd.NA,
                **{column: pd.NA for column in matrix.columns},
                "cluster": pd.NA,
                "k": candidate,
                "silhouette": score,
                "selecionado": candidate == selected_k,
                "status": "candidato",
            }
        )
    assignments = result.labels if result is not None else pd.Series(dtype="object")
    if len(assignments) == 0:
        rows.append(
            {
                "mes": pd.NA,
                **{column: pd.NA for column in matrix.columns},
                "cluster": pd.NA,
                "k": selected_k,
                "silhouette": selected_score,
                "selecionado": False,
                "status": getattr(result, "reason", "skipped"),
            }
        )
    for month, label in assignments.items():
        values = matrix.loc[month].to_dict() if month in matrix.index else {}
        rows.append(
            {
                "mes": month,
                **values,
                "cluster": label,
                "k": selected_k,
                "silhouette": selected_score,
                "selecionado": True,
                "status": "atribuicao",
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _product_series(frame: pd.DataFrame, product: str, value_column: str = "unidades") -> pd.Series:
    selected = frame.loc[frame["produto"].eq(product)].sort_values("data")
    values = selected[value_column].astype(float)
    return pd.Series(values.to_numpy(), index=pd.DatetimeIndex(selected["data"]), name=product)


def _interpolation_table(frame: pd.DataFrame, degree: int | None) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for product, group in frame.groupby("produto", sort=False):
        values = fill_gaps_linear(_product_series(frame, product))
        x_values = np.arange(len(values), dtype=float)
        fit = polynomial_fit(x_values, values.to_numpy(), degree=degree)
        equation = polynomial_equation_label(fit.coefs_desc, fit.degree, fit.r2, fit.r2_adj)
        candidate_rmse = dict(zip(fit.candidates["degree"], fit.candidates["rmse"], strict=True))
        rows.append(
            {
                "produto": product,
                "grau": fit.degree,
                "grau_fonte": fit.degree_source,
                "rmse_holdout": fit.rmse_holdout,
                "r2": fit.r2,
                "r2_adj": fit.r2_adj,
                "equacao": equation,
                **{
                    f"rmse_grau_{candidate}": candidate_rmse.get(candidate, np.nan)
                    for candidate in range(1, 6)
                },
                **{f"coef_{position}": value for position, value in enumerate(fit.coefs_desc)},
            }
        )
    return pd.DataFrame(rows)


def _fill_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for product, group in result.groupby("produto", sort=False):
        ordered = group.sort_values("data")
        values = fill_gaps_linear(_product_series(result, product))
        result.loc[ordered.index, "unidades"] = values.to_numpy()
    return result


def _feature_table(features: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for product, values in features.items():
        result = values.reset_index(names="data").copy()
        result.insert(0, "produto", product)
        rows.append(result)
    if len(rows) == 0:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def _classical_fit(name: str, x_values: np.ndarray, target: np.ndarray) -> RegressionFit:
    builders = {
        "linear_normal_equation": lambda: linear_regression_normal_equation(x_values, target),
        "exponential_loglinear": lambda: exponential_regression_loglinear(x_values, target),
        "exponential_normal_equation": lambda: exponential_regression_normal_equation(
            x_values, target
        ),
    }
    return builders[name]()


def _classical_cv(name: str, x_values: np.ndarray, target: np.ndarray) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    splitter = TimeSeriesSplit(n_splits=3)
    for fold, (train_index, test_index) in enumerate(splitter.split(x_values), start=1):
        fit = _classical_fit(name, x_values[train_index], target[train_index])
        predicted = fit.predict(x_values[test_index])
        result = metrics(target[test_index], predicted)
        rows.append({"fold": fold, **result})
    return pd.DataFrame(rows)


def _backtest_product(
    product: str,
    frame: pd.DataFrame,
    product_features: pd.DataFrame,
    month_clusters: pd.Series,
    seed: int,
    warnings: list[str],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, pd.Series]]:
    history = _product_series(frame, product)
    target = history.to_numpy(dtype=float)
    dates = history.index
    train_history = history.loc[history.index.year < HOLDOUT_YEAR]
    holdout = history.loc[history.index.year == HOLDOUT_YEAR]
    results: list[dict[str, object]] = []
    cv_rows: list[dict[str, object]] = []
    predictions: dict[str, pd.Series] = {}
    if len(history) < 24:
        warning = f"{product}: insufficient_data para ML"
        warnings.append(warning)
        LOGGER.warning(warning)
        for name in MODEL_NAMES:
            results.append(
                {
                    "produto": product,
                    "modelo": name,
                    "metric_note": "insufficient_data",
                    "mape": np.nan,
                    "mad": np.nan,
                }
            )
        return results, cv_rows, predictions

    train_features = product_features.loc[product_features.index.year < HOLDOUT_YEAR]
    train_y = history.reindex(train_features.index).to_numpy(dtype=float)
    holdout_y = holdout.to_numpy(dtype=float)
    estimators = build_estimators(seed)
    for name, estimator in estimators.items():
        cv = cross_validate_temporal(estimator, train_features, train_y, n_splits=3)
        cv.insert(0, "modelo", name)
        cv.insert(0, "produto", product)
        cv_rows.extend(cv.to_dict("records"))
        fitted = fit_final(estimator, train_features, train_y)
        predicted = forecast_recursive(
            fitted, train_history, month_clusters, horizon_years=1, start="2024-01"
        )
        predicted = predicted.reindex(holdout.index)
        predictions[name] = predicted
        results.append(
            {"produto": product, "modelo": name, **metrics(holdout_y, predicted.to_numpy())}
        )

    x_values = np.arange(len(history), dtype=float)
    train_mask = dates.year < HOLDOUT_YEAR
    test_mask = dates.year == HOLDOUT_YEAR
    for name in MODEL_NAMES[3:]:
        cv = _classical_cv(name, x_values[train_mask], target[train_mask])
        cv.insert(0, "modelo", name)
        cv.insert(0, "produto", product)
        cv_rows.extend(cv.to_dict("records"))
        fit = _classical_fit(name, x_values[train_mask], target[train_mask])
        predicted = fit.predict(x_values[test_mask])
        predictions[name] = pd.Series(predicted, index=holdout.index, name=name)
        result = {"produto": product, "modelo": name, **metrics(holdout_y, predicted)}
        if fit.applicable is False:
            result.update(
                {"mape": np.nan, "mad": np.nan, "metric_note": fit.note or "not_applicable"}
            )
            warning = f"{product}/{name}: not_applicable"
            warnings.append(warning)
            LOGGER.warning(warning)
        results.append(result)
    return results, cv_rows, predictions


def _regression_table(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, dict[str, RegressionFit]]]:
    rows: list[dict[str, object]] = []
    fits_by_product: dict[str, dict[str, RegressionFit]] = {}
    for product in frame["produto"].drop_duplicates():
        history = _product_series(frame, product)
        x_values = np.arange(len(history), dtype=float)
        fits = {
            name: _classical_fit(name, x_values, history.to_numpy(dtype=float))
            for name in MODEL_NAMES[3:]
        }
        fits_by_product[product] = fits
        for name, fit in fits.items():
            rows.append(
                {
                    "produto": product,
                    "modelo": name,
                    "coeficientes": ",".join(f"{value:.12g}" for value in fit.coefs),
                    "r2": fit.r2,
                    "equacao": fit.equation,
                    "metric_note": fit.note or "",
                }
            )
    return pd.DataFrame(rows), fits_by_product


def _classification_table(
    frame: pd.DataFrame,
    features: Mapping[str, pd.DataFrame],
    month_clusters: pd.Series,
    seed: int,
    warnings: list[str],
) -> tuple[pd.DataFrame, dict[str, object]]:
    rows: list[dict[str, object]] = []
    results: dict[str, object] = {}
    for product, product_features in features.items():
        history = _product_series(frame, product)
        labels = (
            history.index.month.to_series(index=history.index)
            .map(month_clusters)
            .eq("alta")
            .astype(int)
        )
        labels.index = history.index
        aligned = labels.reindex(product_features.index)
        classification_features = select_classification_features(product_features)
        train_mask = classification_features.index.year < HOLDOUT_YEAR
        test_mask = classification_features.index.year == HOLDOUT_YEAR
        model = fit_regime_classifier(
            classification_features.loc[train_mask],
            aligned.loc[train_mask],
            seed=seed,
        )
        result = evaluate_classifier(
            model,
            classification_features.loc[test_mask],
            aligned.loc[test_mask],
        )
        results[product] = result
        matrix = result.confusion
        rows.append(
            {
                "produto": product,
                "acuracia": result.metrics["accuracy"],
                "precisao": result.metrics["precision"],
                "recall": result.metrics["recall"],
                "f1": result.metrics["f1"],
                "vp": int(matrix[1, 1]),
                "vn": int(matrix[0, 0]),
                "fp": int(matrix[0, 1]),
                "fn": int(matrix[1, 0]),
            }
        )
        if result.skipped:
            note = result.reason or "skipped"
            warning = f"{product}: {note} na classificação"
            warnings.append(warning)
            LOGGER.warning(warning)
    return pd.DataFrame(
        rows,
        columns=["produto", "acuracia", "precisao", "recall", "f1", "vp", "vn", "fp", "fn"],
    ), results


def _forecast_classical(
    fit: RegressionFit,
    history: pd.Series,
    horizon_years: int,
    warnings: list[str],
) -> pd.Series:
    horizon = horizon_years * 12
    dates = pd.date_range(history.index[-1] + pd.DateOffset(months=1), periods=horizon, freq="MS")
    x_values = np.arange(len(history), len(history) + horizon, dtype=float)
    predicted = fit.predict(x_values)
    product = str(history.name or "produto_desconhecido")
    for index in np.flatnonzero(predicted < 0):
        target_date = dates[index]
        warning = f"previsão negativa truncada para {product} em {target_date:%Y-%m}"
        warnings.append(warning)
        LOGGER.warning(warning)
        predicted[index] = 0.0
    return pd.Series(predicted, index=dates, name=history.name)


def _save(
    figure: object,
    name: str,
    figure_dir: Path,
    formats: Sequence[str],
    output: list[Path],
) -> None:
    try:
        output.extend(save_figure(figure, name, figure_dir, formats=formats))
    finally:
        plt.close(figure)


def _ordered_products(frame: pd.DataFrame) -> list[str]:
    available = frame["produto"].drop_duplicates().astype(str).tolist()
    known = [product for product in PRODUCT_ORDER if product in available]
    extras = [product for product in available if product not in PRODUCT_ORDER]
    return known + extras


def _write_figures(
    stages: set[str],
    frame: pd.DataFrame,
    figure_dir: Path,
    formats: Sequence[str],
    interpolation_degrees: Mapping[str, int],
    month_matrix: pd.DataFrame | None,
    month_result: object,
    series_result: object,
    backtests: Mapping[str, Mapping[str, pd.Series]],
    error_metrics: pd.DataFrame | None,
    regression_fits: Mapping[str, Mapping[str, RegressionFit]],
    classification_results: Mapping[str, object],
    forecasts: Mapping[str, pd.Series],
    best_models: Mapping[str, str],
    annual: pd.DataFrame | None,
    capacity: pd.DataFrame | None,
    demand_forecast: pd.DataFrame | None,
    units_per_case: int | None,
    output: list[Path],
) -> None:
    products = _ordered_products(frame)
    if "plots" not in stages:
        return
    for position, product in enumerate(products, start=1):
        if "load" in stages:
            _save(
                figure_builders.fig_points_product(frame, product),
                f"pontos/{position:02d}_pontos_{product}",
                figure_dir,
                formats,
                output,
            )
    if "load" in stages:
        _save(
            figure_builders.fig_points_all(frame), "pontos/04_pontos_todos", figure_dir, formats, output
        )
    if "interp" in stages:
        for position, product in enumerate(products, start=5):
            _save(
                figure_builders.fig_interpolation(
                    frame, product, degree=interpolation_degrees.get(product)
                ),
                f"interpolacao/{position:02d}_interpolacao_{product}",
                figure_dir,
                formats,
                output,
            )
    if "ma" in stages:
        for position, product in enumerate(products, start=8):
            _save(
                figure_builders.fig_moving_average(frame, product),
                f"media_movel/{position:02d}_media_movel_{product}",
                figure_dir,
                formats,
                output,
            )
    if "cluster" in stages:
        _save(
            figure_builders.fig_month_clusters(month_matrix, month_result),
            "clusters/11_clusters_meses",
            figure_dir,
            formats,
            output,
        )
        _save(
            figure_builders.fig_series_clusters(frame, series_result),
            "clusters/12_clusters_series",
            figure_dir,
            formats,
            output,
        )
    if "ml" in stages:
        for position, product in enumerate(products, start=13):
            predictions = backtests.get(product, {})
            prediction_frame = pd.DataFrame(
                [
                    {"produto": product, "data": date, "modelo": model, "previsao": value}
                    for model, series in predictions.items()
                    for date, value in series.items()
                ]
            )
            _save(
                figure_builders.fig_backtest(frame, prediction_frame, product),
                f"backtest_comparativo/{position:02d}_backtest_{product}",
                figure_dir,
                formats,
                output,
            )
        _save(
            figure_builders.fig_metrics_bar(error_metrics),
            "metricas/16_metricas_mape",
            figure_dir,
            formats,
            output,
        )
        _save(
            figure_builders.fig_error_table(error_metrics),
            "metricas/17_tabela_erros",
            figure_dir,
            formats,
            output,
        )
        for position, product in enumerate(products, start=18):
            _save(
                figure_builders.fig_regression(frame, regression_fits.get(product), product),
                f"regressao_classica/{position:02d}_regressao_{product}",
                figure_dir,
                formats,
                output,
            )
        for position, product in enumerate(products, start=21):
            _save(
                figure_builders.fig_confusion_matrix(classification_results.get(product)),
                f"classificacao/{position:02d}_confusao_{product}",
                figure_dir,
                formats,
                output,
            )
    if "forecast" in stages:
        forecast_frame, _ = forecast_tables(
            forecasts, best_models, error_metrics if error_metrics is not None else pd.DataFrame()
        )
        for position, product in enumerate(products, start=24):
            _save(
                figure_builders.fig_forecast_product(
                    frame,
                    forecast_frame,
                    product,
                    best_models.get(product),
                    holdout_metrics=error_metrics,
                    best_models=best_models,
                ),
                f"previsao/{position:02d}_previsao_{product}",
                figure_dir,
                formats,
                output,
            )
        _save(
            figure_builders.fig_forecast_all(frame, forecast_frame, best_models, error_metrics),
            "previsao/27_previsao_todos",
            figure_dir,
            formats,
            output,
        )
        for position, product in enumerate(products, start=29):
            _save(
                figure_builders.fig_forecast_2025_bar(forecast_frame, product, best_models),
                f"previsao/{position:02d}_previsao_2025_{product}",
                figure_dir,
                formats,
                output,
            )
        _save(
            figure_builders.fig_forecast_2025_total_bar(forecast_frame),
            "previsao/32_previsao_2025_total",
            figure_dir,
            formats,
            output,
        )
    if "capacity" in stages:
        _save(
            figure_builders.fig_capacity(capacity, demand_forecast, units_per_case),
            "capacidade/28_capacidade_case",
            figure_dir,
            formats,
            output,
        )


def run(config: PipelineConfig | None = None) -> PipelineResult:
    """Run selected pipeline stages and persist their artifacts."""
    runtime = PipelineConfig() if config is None else config
    stages = resolve_steps(runtime.steps)
    if runtime.poly_degree is not None and (runtime.poly_degree < 1 or runtime.poly_degree > 5):
        raise InputError("grau inválido; intervalo válido: 1 a 5")
    validate_windows(runtime.ma_windows, 36)
    if runtime.units_per_case is not None and runtime.units_per_case <= 0:
        raise InputError("units_per_case deve ser maior que zero")
    from .forecast import validate_horizon_years
    from .plotting import validate_formats

    formats = validate_formats(runtime.formats)
    validate_horizon_years(runtime.horizon_years)
    _validate_output_directory(Path(runtime.outdir))
    logging.getLogger().setLevel(getattr(logging, runtime.log_level.upper(), logging.WARNING))
    table_dir = Path(runtime.outdir) / "tables"
    figure_dir = Path(runtime.outdir) / "figures"
    result = PipelineResult()
    analysis_frame = pd.DataFrame()
    month_matrix = None
    month_result = None
    evaluation_month_result = None
    series_result = None
    feature_map: dict[str, pd.DataFrame] = {}
    forecast_feature_map: dict[str, pd.DataFrame] = {}
    interpolation_degrees: dict[str, int] = {}
    error_metrics = None
    backtests: dict[str, dict[str, pd.Series]] = {}
    best_models: dict[str, str] = {}
    forecasts: dict[str, pd.Series] = {}
    regression_fits: dict[str, dict[str, RegressionFit]] = {}
    classification_results: dict[str, object] = {}
    capacity = None
    demand_cases = None
    monthly_forecast = pd.DataFrame()
    cv_accumulator = pd.DataFrame()
    annual = pd.DataFrame()
    if "load" in stages:
        frame = load_demand(Path(runtime.input))
        analysis_frame = _fill_frame(frame)
        _write_table(frame, table_dir, "demand_tidy.csv", result.tables)
    if "interp" in stages:
        interpolation_frame = _interpolation_table(frame, runtime.poly_degree)
        for row in interpolation_frame.itertuples():
            interpolation_degrees[row.produto] = int(row.grau)
        _write_table(interpolation_frame, table_dir, "interpolation_fit.csv", result.tables)
    if "ma" in stages:
        moving_frame = moving_average_table(analysis_frame, runtime.ma_windows)
        _write_table(moving_frame, table_dir, "moving_average.csv", result.tables)
    if "cluster" in stages:
        cluster_frame = _eligible_cluster_frame(analysis_frame)
        month_matrix = seasonal_index_matrix(cluster_frame)
        month_result = cluster_months(month_matrix, k=runtime.k_months, seed=runtime.seed)
        evaluation_frame = cluster_frame.loc[cluster_frame["ano"] < HOLDOUT_YEAR]
        evaluation_matrix = seasonal_index_matrix(evaluation_frame)
        evaluation_month_result = cluster_months(
            evaluation_matrix,
            k=runtime.k_months,
            seed=runtime.seed,
        )
        series_result = cluster_series(cluster_frame, seed=runtime.seed)
        _write_table(
            _month_cluster_table(month_matrix, month_result),
            table_dir,
            "clustering_months.csv",
            result.tables,
        )
        series_rows = series_result.labels.rename("cluster").reset_index()
        series_rows["k"] = series_result.k
        series_rows["silhouette"] = series_result.silhouette
        series_rows["status"] = series_result.reason or "atribuicao"
        if len(series_rows) == 0:
            series_rows = pd.DataFrame(
                [
                    {
                        "produto": pd.NA,
                        "ano": pd.NA,
                        "cluster": pd.NA,
                        "k": series_result.k,
                        "silhouette": series_result.silhouette,
                        "status": series_result.reason or "skipped",
                    }
                ],
                columns=["produto", "ano", "cluster", "k", "silhouette", "status"],
            )
        _write_table(series_rows, table_dir, "clustering_series.csv", result.tables)
    if "features" in stages:
        evaluation_labels = (
            evaluation_month_result.labels
            if evaluation_month_result is not None
            else pd.Series(dtype="object")
        )
        forecast_labels = (
            month_result.labels if month_result is not None else pd.Series(dtype="object")
        )
        for product in analysis_frame["produto"].drop_duplicates():
            product_frame = analysis_frame.loc[analysis_frame["produto"].eq(product)]
            feature_map[product] = build_features(product_frame, evaluation_labels)
            forecast_feature_map[product] = build_features(product_frame, forecast_labels)
        _write_table(_feature_table(feature_map), table_dir, "features.csv", result.tables)
    if "ml" in stages:
        evaluation_labels = (
            evaluation_month_result.labels
            if evaluation_month_result is not None
            else pd.Series(dtype="object")
        )
        for product, product_features in feature_map.items():
            product_results, cv_rows, product_backtests = _backtest_product(
                product,
                analysis_frame,
                product_features,
                evaluation_labels,
                runtime.seed,
                result.warnings,
            )
            backtests[product] = product_backtests
            product_frame = pd.DataFrame(product_results)
            error_metrics = (
                product_frame
                if error_metrics is None
                else pd.concat([error_metrics, product_frame], ignore_index=True)
            )
            cv_accumulator = pd.concat([cv_accumulator, pd.DataFrame(cv_rows)], ignore_index=True)
            applicable = product_frame.dropna(subset=["mape"])
            if len(applicable) > 0:
                best_models[product] = select_best(applicable)
        error_metrics = pd.DataFrame() if error_metrics is None else error_metrics
        from .models import metrics_table

        error_metrics = metrics_table(error_metrics)
        _write_table(cv_accumulator, table_dir, "cv_metrics.csv", result.tables)
        _write_table(error_metrics, table_dir, "error_metrics.csv", result.tables)
        regression_frame, regression_fits = _regression_table(analysis_frame)
        _write_table(regression_frame, table_dir, "regression_fit.csv", result.tables)
        classification_frame, classification_results = _classification_table(
            analysis_frame,
            feature_map,
            evaluation_labels,
            runtime.seed,
            result.warnings,
        )
        _write_table(classification_frame, table_dir, "regime_classification.csv", result.tables)
    if "forecast" in stages:
        forecast_labels = (
            month_result.labels if month_result is not None else pd.Series(dtype="object")
        )
        for product, model_name in best_models.items():
            history = _product_series(analysis_frame, product)
            if model_name in MODEL_NAMES[:3]:
                estimator = build_estimators(runtime.seed)[model_name]
                full_features = forecast_feature_map[product]
                target = history.reindex(full_features.index)
                estimator = fit_final(estimator, full_features, target)
                forecasts[product] = forecast_recursive(
                    estimator, history, forecast_labels, runtime.horizon_years
                )
                continue
            fit = _classical_fit(
                model_name, np.arange(len(history), dtype=float), history.to_numpy(dtype=float)
            )
            forecasts[product] = _forecast_classical(
                fit,
                history,
                runtime.horizon_years,
                result.warnings,
            )
        monthly_forecast, annual = forecast_tables(
            forecasts,
            best_models,
            error_metrics if error_metrics is not None else pd.DataFrame(),
        )
        _write_table(monthly_forecast, table_dir, "forecast_monthly.csv", result.tables)
        _write_table(annual, table_dir, "forecast_annual.csv", result.tables)
    if "capacity" in stages:
        capacity = capacity_frame()
        if forecasts:
            monthly_forecast, _ = forecast_tables(
                forecasts,
                best_models,
                error_metrics if error_metrics is not None else pd.DataFrame(),
            )
            demand_cases = demand_in_cases(monthly_forecast, runtime.units_per_case)
        capacity_output = capacity.rename(
            columns={"produto": "linha", "antes": "capacidade_antes", "depois": "capacidade_depois"}
        )
        capacity_output["demanda_caixas"] = np.nan
        capacity_output["demanda_caixas_total"] = np.nan
        if demand_cases is not None and len(demand_cases) > 0:
            product_peak = demand_cases.groupby("produto")["caixas"].max()
            product_total = demand_cases.groupby("produto")["caixas"].sum()
            capacity_output["demanda_caixas"] = capacity_output["linha"].map(product_peak)
            capacity_output["demanda_caixas_total"] = capacity_output["linha"].map(product_total)
            total_mask = capacity_output["linha"].eq("total")
            monthly_peak = demand_cases.groupby(["ano", "mes"])["caixas"].sum().max()
            capacity_output.loc[total_mask, "demanda_caixas"] = monthly_peak
            capacity_output.loc[total_mask, "demanda_caixas_total"] = demand_cases["caixas"].sum()
        _write_table(capacity_output, table_dir, "capacity_vs_demand.csv", result.tables)
    _write_figures(
        set(stages),
        frame,
        figure_dir,
        formats,
        interpolation_degrees,
        month_matrix,
        month_result,
        series_result,
        backtests,
        error_metrics,
        regression_fits,
        classification_results,
        forecasts,
        best_models,
        annual,
        capacity,
        monthly_forecast,
        runtime.units_per_case,
        result.figures,
    )
    if runtime.timeseries:
        from .timeseries import generate_and_save_timeseries_artifacts

        ts_artifacts = generate_and_save_timeseries_artifacts(
            analysis_frame,
            runtime.outdir,
            formats=formats,
            horizon_years=runtime.horizon_years,
        )
        result.timeseries_metrics = ts_artifacts["metrics"]
    result.annual_forecast = annual if "forecast" in stages else pd.DataFrame()
    return result
