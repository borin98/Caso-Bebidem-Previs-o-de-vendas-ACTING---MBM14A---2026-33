"""Motor do POC: janela móvel de 12 meses, 9 modelos, vencedor único e previsão futura.

Reusa só funções públicas de ``bebibem``. Não usa helpers presos a ano fixo
(``split_train_holdout``, ``backtest_timeseries_product``, ``HOLDOUT_YEAR``).
"""

from __future__ import annotations

import logging
import warnings
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import numpy as np
import pandas as pd
from bebibem.clustering import cluster_months, seasonal_index_matrix
from bebibem.config import MIN_OBS_FOR_ML, SEED
from bebibem.features import build_features
from bebibem.forecast import fit_final, forecast_recursive, validate_horizon_years
from bebibem.io_data import InputError
from bebibem.models import build_estimators, metrics, select_best
from bebibem.regression import (
    RegressionFit,
    exponential_regression_loglinear,
    exponential_regression_normal_equation,
    linear_regression_normal_equation,
)
from bebibem.timeseries import (
    TimeSeriesModelResult,
    fourier_regression,
    holt_winters_multiplicative,
    sarima_forecast,
)

HOLDOUT_MONTHS = 12
MIN_HISTORY_MONTHS = MIN_OBS_FOR_ML + HOLDOUT_MONTHS

MODEL_CATALOG: tuple[dict[str, str], ...] = (
    {"modelo": "ridge", "label": "Ridge", "familia": "ml"},
    {"modelo": "random_forest", "label": "Random Forest", "familia": "ml"},
    {"modelo": "gradient_boosting", "label": "Gradient Boosting", "familia": "ml"},
    {"modelo": "linear_normal_equation", "label": "Regressão linear", "familia": "classica"},
    {"modelo": "exponential_loglinear", "label": "Exponencial (log-linear)", "familia": "classica"},
    {
        "modelo": "exponential_normal_equation",
        "label": "Exponencial (equação normal)",
        "familia": "classica",
    },
    {
        "modelo": "holt_winters_multiplicative",
        "label": "Holt-Winters multiplicativo",
        "familia": "series_temporais",
    },
    {"modelo": "sarima", "label": "SARIMA", "familia": "series_temporais"},
    {"modelo": "fourier_harmonic", "label": "Harmônicos de Fourier", "familia": "series_temporais"},
)
CATALOG_BY_MODEL = {spec["modelo"]: spec for spec in MODEL_CATALOG}

CLASSICAL: dict[str, Callable[[np.ndarray, np.ndarray], RegressionFit]] = {
    "linear_normal_equation": linear_regression_normal_equation,
    "exponential_loglinear": exponential_regression_loglinear,
    "exponential_normal_equation": exponential_regression_normal_equation,
}
TIME_SERIES: dict[str, Callable[..., TimeSeriesModelResult]] = {
    "holt_winters_multiplicative": holt_winters_multiplicative,
    "sarima": sarima_forecast,
    "fourier_harmonic": fourier_regression,
}

REASONS = {
    "not_applicable": "Histórico com valores ≤ 0: o modelo exige vendas positivas",
    "insufficient_data": "Dados insuficientes para o ajuste",
    "dados_insuficientes": "Dados insuficientes para o ajuste",
    "valores_nao_positivos": "Histórico com valores ≤ 0: o modelo multiplicativo exige vendas "
    "positivas",
}
NO_MAPE_REASON = "MAPE indefinido: todos os meses de teste têm venda zero"
TRUNCATION_PREFIX = "previsão negativa truncada"


def period(value: object) -> str:
    """Format a month as ``YYYY-MM``."""
    return pd.Timestamp(value).strftime("%Y-%m")


def tidy_frame(rows: pd.DataFrame) -> pd.DataFrame:
    """Convert stored rows (produto, produto_label, periodo, unidades) to the bebibem tidy frame."""
    dates = pd.to_datetime(rows["periodo"].astype(str), format="%Y-%m")
    return pd.DataFrame(
        {
            "produto": rows["produto"].astype(str),
            "produto_label": rows["produto_label"].astype(str),
            "ano": dates.dt.year,
            "mes": dates.dt.month,
            "data": dates,
            "unidades": pd.to_numeric(rows["unidades"], errors="coerce").astype(float),
        }
    )


def validate_history(frame: pd.DataFrame) -> list[str]:
    """Return PT-BR problems: gaps, fewer than 36 months, products ending in different months."""
    problems: list[str] = []
    ends: dict[str, pd.Timestamp] = {}
    for product, group in frame.groupby("produto", sort=False):
        dates = pd.DatetimeIndex(group.dropna(subset=["unidades"])["data"]).sort_values()
        if len(dates) == 0:
            problems.append(f"{product}: nenhum mês com venda informada")
            continue
        expected = pd.date_range(dates.min(), dates.max(), freq="MS")
        missing = expected.difference(dates)
        if len(missing) > 0:
            months = ", ".join(period(value) for value in missing)
            problems.append(f"{product}: meses faltantes no meio da série: {months}")
        if len(dates) < MIN_HISTORY_MONTHS:
            problems.append(
                f"histórico insuficiente: {product} tem {len(dates)} meses; "
                f"mínimo {MIN_HISTORY_MONTHS}"
            )
        ends[str(product)] = dates.max()
    if len(set(ends.values())) > 1:
        detail = ", ".join(f"{product} termina em {period(end)}" for product, end in ends.items())
        problems.append(f"produtos terminam em meses diferentes: {detail}")
    return problems


class _TruncationCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if message.startswith(TRUNCATION_PREFIX) is False:
            return
        self.messages.append(message)


@contextmanager
def _captured_truncations() -> Iterator[list[str]]:
    """Collect ``forecast_recursive`` truncation warnings (it clips negatives and only logs)."""
    logger = logging.getLogger("bebibem.forecast")
    collector = _TruncationCollector()
    logger.addHandler(collector)
    try:
        yield collector.messages
    finally:
        logger.removeHandler(collector)


def _points(index: pd.DatetimeIndex, values: np.ndarray) -> list[dict[str, object]]:
    return [
        {"periodo": period(date), "valor": float(value)}
        for date, value in zip(index, values, strict=True)
    ]


def _month_labels(frame: pd.DataFrame, seed: int) -> pd.Series:
    return cluster_months(seasonal_index_matrix(frame), seed=seed).labels


def _clip_future(
    values: np.ndarray, index: pd.DatetimeIndex, product: str, model: str, avisos: list[str]
) -> np.ndarray:
    negatives = np.flatnonzero(values < 0)
    for position in negatives:
        avisos.append(f"{TRUNCATION_PREFIX} para {product} em {period(index[position])} ({model})")
    return np.where(values < 0, 0.0, values)


def _ml_outcomes(
    product_frame: pd.DataFrame,
    history: pd.Series,
    holdout_start: pd.Timestamp,
    future_index: pd.DatetimeIndex,
    labels: tuple[pd.Series, pd.Series],
    seed: int,
    avisos: list[str],
) -> dict[str, dict[str, object]]:
    evaluation_labels, forecast_labels = labels
    train_history = history.loc[history.index < holdout_start]
    holdout_index = history.index[history.index >= holdout_start]
    evaluation_features = build_features(product_frame, evaluation_labels)
    train_features = evaluation_features.loc[evaluation_features.index < holdout_start]
    train_y = history.reindex(train_features.index)
    full_features = build_features(product_frame, forecast_labels)
    full_y = history.reindex(full_features.index)
    horizon_years = len(future_index) // 12
    outcomes: dict[str, dict[str, object]] = {}
    for name, estimator in build_estimators(seed).items():
        with _captured_truncations() as truncated:
            fitted = fit_final(estimator, train_features, train_y)
            predicted = forecast_recursive(
                fitted,
                train_history,
                evaluation_labels,
                horizon_years=1,
                start=period(holdout_start),
            ).reindex(holdout_index)
            final = fit_final(build_estimators(seed)[name], full_features, full_y)
            future = forecast_recursive(
                final, history, forecast_labels, horizon_years, start=period(future_index[0])
            )
        avisos.extend(f"{message} ({name})" for message in truncated)
        outcomes[name] = {
            "holdout": predicted.to_numpy(dtype=float),
            "future": future.to_numpy(dtype=float),
            "motivo": None,
        }
    return outcomes


def _classical_outcomes(
    history: pd.Series,
    holdout_start: pd.Timestamp,
    future_index: pd.DatetimeIndex,
    avisos: list[str],
) -> dict[str, dict[str, object]]:
    target = history.to_numpy(dtype=float)
    x_values = np.arange(len(history), dtype=float)
    train_mask = history.index < holdout_start
    future_x = np.arange(len(history), len(history) + len(future_index), dtype=float)
    outcomes: dict[str, dict[str, object]] = {}
    for name, builder in CLASSICAL.items():
        train_fit = builder(x_values[train_mask], target[train_mask])
        if train_fit.applicable is False:
            outcomes[name] = {"motivo": _note_reason(train_fit.note)}
            continue
        full_fit = builder(x_values, target)
        if full_fit.applicable is False:
            outcomes[name] = {"motivo": _note_reason(full_fit.note)}
            continue
        future = full_fit.predict(future_x)
        outcomes[name] = {
            "holdout": train_fit.predict(x_values[~train_mask]),
            "future": _clip_future(future, future_index, str(history.name), name, avisos),
            "motivo": None,
        }
    return outcomes


def _note_reason(note: str | None) -> str:
    text = note or "not_applicable"
    if text.startswith("erro_ajuste"):
        return f"Falha no ajuste: {text.removeprefix('erro_ajuste: ')}"
    return REASONS.get(text, text)


def _time_series_reason(result: TimeSeriesModelResult) -> str | None:
    if result.applicable is False:
        return _note_reason(result.note)
    if len(result.forecast) == 0:
        return _note_reason(result.note)
    return None


def _time_series_outcomes(
    history: pd.Series,
    holdout_start: pd.Timestamp,
    future_index: pd.DatetimeIndex,
    avisos: list[str],
) -> dict[str, dict[str, object]]:
    train = history.loc[history.index < holdout_start]
    outcomes: dict[str, dict[str, object]] = {}
    for name, fitter in TIME_SERIES.items():
        evaluation = fitter(train, horizon=HOLDOUT_MONTHS)
        reason = _time_series_reason(evaluation)
        if reason is not None:
            outcomes[name] = {"motivo": reason}
            continue
        final = fitter(history, horizon=len(future_index))
        reason = _time_series_reason(final)
        if reason is not None:
            outcomes[name] = {"motivo": reason}
            continue
        future = final.forecast.to_numpy(dtype=float)[: len(future_index)]
        outcomes[name] = {
            "holdout": evaluation.forecast.to_numpy(dtype=float)[:HOLDOUT_MONTHS],
            "future": _clip_future(future, future_index, str(history.name), name, avisos),
            "motivo": None,
        }
    return outcomes


def _empty_model(spec: dict[str, str], reason: str) -> dict[str, object]:
    return {
        **spec,
        "aplicavel": False,
        "motivo": reason,
        "mad": None,
        "mse": None,
        "rmse": None,
        "mape": None,
        "mpe": None,
        "n_zeros": 0,
        "rank": None,
        "vencedor": False,
        "holdout_previsto": [],
        "previsao": [],
    }


def _model_row(
    spec: dict[str, str],
    outcome: dict[str, object],
    holdout: pd.Series,
    future_index: pd.DatetimeIndex,
) -> dict[str, object]:
    if outcome["motivo"] is not None:
        return _empty_model(spec, str(outcome["motivo"]))
    predicted = np.asarray(outcome["holdout"], dtype=float)
    result = metrics(holdout.to_numpy(dtype=float), predicted)
    if np.isfinite(result["mape"]) is False:
        return _empty_model(spec, NO_MAPE_REASON)
    return {
        **spec,
        "aplicavel": True,
        "motivo": None,
        "mad": float(result["mad"]),
        "mse": float(result["mse"]),
        "rmse": float(result["rmse"]),
        "mape": float(result["mape"]),
        "mpe": float(result["mpe"]),
        "n_zeros": int(result["n_zeros"]),
        "rank": None,
        "vencedor": False,
        "holdout_previsto": _points(holdout.index, predicted),
        "previsao": _points(future_index, np.asarray(outcome["future"], dtype=float)),
    }


def _rank_models(product: str, rows: list[dict[str, object]]) -> str:
    """Rank by successive ``select_best`` (lowest MAPE, ties < 0.5 p.p. by MAD); return winner."""
    applicable = pd.DataFrame(
        [{"modelo": row["modelo"], "mape": row["mape"], "mad": row["mad"]} for row in rows]
    ).dropna(subset=["mape"])
    if len(applicable) == 0:
        raise InputError(f"nenhum modelo aplicável para {product}")
    by_model = {str(row["modelo"]): row for row in rows}
    position = 1
    while len(applicable) > 0:
        best = select_best(applicable)
        by_model[best]["rank"] = position
        position += 1
        applicable = applicable.loc[applicable["modelo"] != best]
    winner = next(name for name, row in by_model.items() if row["rank"] == 1)
    by_model[winner]["vencedor"] = True
    return winner


def _evaluate_product(
    data: pd.DataFrame,
    product: str,
    holdout_start: pd.Timestamp,
    horizon_years: int,
    labels: tuple[pd.Series, pd.Series],
    seed: int,
    avisos: list[str],
) -> dict[str, object]:
    product_frame = data.loc[data["produto"].eq(product)].sort_values("data")
    history = pd.Series(
        product_frame["unidades"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(product_frame["data"]),
        name=product,
    )
    holdout = history.loc[history.index >= holdout_start]
    future_index = pd.date_range(
        history.index[-1] + pd.DateOffset(months=1), periods=12 * horizon_years, freq="MS"
    )
    outcomes = {
        **_ml_outcomes(product_frame, history, holdout_start, future_index, labels, seed, avisos),
        **_classical_outcomes(history, holdout_start, future_index, avisos),
        **_time_series_outcomes(history, holdout_start, future_index, avisos),
    }
    rows = [
        _model_row(spec, outcomes[spec["modelo"]], holdout, future_index) for spec in MODEL_CATALOG
    ]
    winner = _rank_models(product, rows)
    return {
        "produto": product,
        "label": str(product_frame["produto_label"].iloc[0]),
        "janela": {
            "treino_fim": period(holdout_start - pd.DateOffset(months=1)),
            "holdout_inicio": period(holdout_start),
            "holdout_fim": period(history.index[-1]),
        },
        "observado": _points(history.index, history.to_numpy(dtype=float)),
        "vencedor": winner,
        "modelos": rows,
    }


def evaluate_and_forecast(
    frame: pd.DataFrame, horizon_years: int = 2, seed: int = SEED
) -> dict[str, object]:
    """Evaluate the 9 models on the last 12 observed months and forecast ``12 × h`` months ahead."""
    validate_horizon_years(horizon_years)
    problems = validate_history(frame)
    if len(problems) > 0:
        raise InputError("; ".join(problems))
    data = frame.dropna(subset=["unidades"]).copy()
    data["data"] = pd.to_datetime(data["data"])
    last = pd.Timestamp(data["data"].max())
    holdout_start = last - pd.DateOffset(months=HOLDOUT_MONTHS - 1)
    avisos: list[str] = []
    with warnings.catch_warnings():
        # statsmodels emits convergence/frequency warnings on every fit; they are not actionable
        warnings.simplefilter("ignore")
        labels = (
            _month_labels(data.loc[data["data"] < holdout_start], seed),
            _month_labels(data, seed),
        )
        products = [
            _evaluate_product(
                data, str(product), holdout_start, horizon_years, labels, seed, avisos
            )
            for product in data["produto"].drop_duplicates()
        ]
    return {
        "ultimo_observado": period(last),
        "horizon_years": horizon_years,
        "avisos": avisos,
        "produtos": products,
    }
