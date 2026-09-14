"""Matplotlib figure builders for the BebiBem demand analysis.

Figure builders deliberately return only :class:`matplotlib.figure.Figure` objects.
Exporting figures is owned by :func:`bebibem.plotting.save_figure` in the pipeline.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from .config import HOLDOUT_YEAR, MONTH_AXIS_LABEL, global_month_index, month_index
from .formulas import FORMULAS, metric_footnote
from .interpolation import (
    fill_gaps_linear,
    linear_interpolation,
    polynomial_equation_label,
    polynomial_fit,
)
from .plotting import annotate_equation, apply_style
from .smoothing import moving_average

_PRODUCT_COLUMN = "produto"
_VALUE_COLUMN = "unidades"
_DATE_COLUMN = "data"
_MONTH_AXIS_LABEL = MONTH_AXIS_LABEL


def _new_figure() -> tuple[Figure, Any]:
    apply_style()
    return plt.subplots(figsize=(10, 6))


def _as_frame(data: pd.DataFrame | pd.Series | None) -> pd.DataFrame:
    if data is None:
        return pd.DataFrame()
    if isinstance(data, pd.Series):
        frame = data.rename(_VALUE_COLUMN).to_frame()
        frame.index.name = _DATE_COLUMN
        return frame.reset_index()
    return data.copy()


def _product_values(frame: pd.DataFrame) -> list[str]:
    if _PRODUCT_COLUMN not in frame.columns:
        return [""]
    return [str(value) for value in frame[_PRODUCT_COLUMN].dropna().drop_duplicates()]


def _product_frame(data: pd.DataFrame | pd.Series | None, product: str | None) -> pd.DataFrame:
    frame = _as_frame(data)
    if product is None or _PRODUCT_COLUMN not in frame.columns:
        return frame.sort_values(_DATE_COLUMN) if _DATE_COLUMN in frame.columns else frame
    return frame.loc[frame[_PRODUCT_COLUMN].astype(str).eq(str(product))].sort_values(_DATE_COLUMN)


def _product_label(frame: pd.DataFrame, product: str | None = None) -> str:
    if "produto_label" in frame.columns:
        labels = frame["produto_label"].dropna().astype(str)
        if len(labels) > 0:
            return str(labels.iloc[0])
    if product is not None:
        return str(product)
    if _PRODUCT_COLUMN in frame.columns and len(frame) > 0:
        return str(frame[_PRODUCT_COLUMN].iloc[0])
    return "Produto"


def _dates(frame: pd.DataFrame) -> pd.DatetimeIndex:
    if _DATE_COLUMN in frame.columns:
        return pd.DatetimeIndex(pd.to_datetime(frame[_DATE_COLUMN]))
    if {"ano", "mes"}.issubset(frame.columns):
        return pd.DatetimeIndex(pd.to_datetime(frame[["ano", "mes"]].assign(dia=1)))
    return pd.date_range("2022-01-01", periods=len(frame), freq="MS")


_global_month_index = global_month_index
_month_index = month_index


def _values(frame: pd.DataFrame) -> np.ndarray:
    if _VALUE_COLUMN not in frame.columns:
        return np.full(len(frame), np.nan, dtype=float)
    return frame[_VALUE_COLUMN].to_numpy(dtype=float)


def _observed(axis: Any, dates: pd.DatetimeIndex, values: np.ndarray, **kwargs: Any) -> None:
    valid = np.isfinite(values)
    if bool(valid.any()) is False:
        return
    axis.scatter(dates[valid], values[valid], **kwargs)


def _empty_message(axis: Any, title: str) -> None:
    axis.set_title(title)
    axis.text(0.5, 0.5, "Sem dados disponíveis", transform=axis.transAxes, ha="center", va="center")


def fig_points_product(data: pd.DataFrame | pd.Series | None, product: str | None = None) -> Figure:
    """Build one observed-points figure for a product."""
    frame = _product_frame(data, product)
    label = _product_label(frame, product)
    figure, axis = _new_figure()
    if len(frame) == 0:
        _empty_message(axis, f"Pontos observados — {label}")
        return figure
    month_idx = _month_index(_dates(frame))
    values = _values(frame)
    _observed(axis, month_idx, values, color="#1769aa", label="Observado", zorder=3)
    axis.set_title(f"Pontos observados — {label}")
    axis.set_xlabel(_MONTH_AXIS_LABEL)
    axis.set_ylabel("Unidades")
    axis.legend()
    return figure


def fig_points_all(data: pd.DataFrame | None) -> Figure:
    """Build one figure with observed points for all products."""
    frame = _as_frame(data)
    figure, axis = _new_figure()
    products = _product_values(frame)
    if len(frame) == 0 or len(products) == 0:
        _empty_message(axis, "Pontos observados — todas as linhas")
        return figure
    for product in products:
        group = _product_frame(frame, product)
        _observed(
            axis,
            _month_index(_dates(group)),
            _values(group),
            label=_product_label(group, product),
            zorder=3,
        )
    axis.set_title("Pontos observados — todas as linhas")
    axis.set_xlabel(_MONTH_AXIS_LABEL)
    axis.set_ylabel("Unidades")
    axis.legend()
    return figure


def fig_interpolation(
    data: pd.DataFrame | pd.Series | None,
    product: str | None = None,
    degree: int | None = None,
    poly_degree: int | None = None,
) -> Figure:
    """Plot observed points and linear/polynomial interpolation curves."""
    if degree is None:
        degree = poly_degree
    frame = _product_frame(data, product)
    label = _product_label(frame, product)
    figure, axis = _new_figure()
    if len(frame) < 2:
        _empty_message(axis, f"Interpolação — {label}")
        axis.text(0.5, -0.18, "x = 0 em 2022-01", transform=axis.transAxes, ha="center")
        return figure
    dates = _dates(frame)
    values = _values(frame)
    positions = _month_index(dates)
    valid = np.isfinite(values)
    if valid.sum() < 2:
        _empty_message(axis, f"Interpolação — {label}")
        return figure
    observed_values = values[valid]
    observed_positions = positions[valid]
    _observed(axis, positions, values, color="#1769aa", label="Observado", zorder=4)
    dense_positions, dense_linear = linear_interpolation(
        observed_positions, observed_values, points_per_step=10
    )
    axis.plot(dense_positions, dense_linear, color="#d95f02", label="Interpolação linear")
    filled = fill_gaps_linear(pd.Series(values)).to_numpy(dtype=float)
    fit = polynomial_fit(positions, filled, degree=degree)
    dense_poly_positions = np.linspace(positions[0], positions[-1], max(2, len(positions) * 10 - 9))
    source_label = {"auto": "auto", "forced": "--poly-degree"}.get(
        fit.degree_source, fit.degree_source
    )
    axis.plot(
        dense_poly_positions,
        fit.evaluate(dense_poly_positions),
        color="#1b9e77",
        label=f"Polinomial (grau {fit.degree}, {source_label})",
    )
    equation = polynomial_equation_label(fit.coefs_desc, fit.degree, fit.r2, fit.r2_adj)
    annotate_equation(axis, equation)
    axis.set_title(f"Interpolação — {label}")
    axis.set_xlabel(_MONTH_AXIS_LABEL)
    axis.set_ylabel("Unidades")
    axis.legend()
    footer = f"x = 0 em 2022-01\n${FORMULAS['poly_fit']}$"
    figure.text(0.5, 0.01, footer, ha="center", va="bottom", fontsize=8)
    figure.subplots_adjust(bottom=0.22)
    return figure


def _moving_average_or_nan(values: pd.Series, window: int) -> pd.Series:
    if len(values) < window:
        return pd.Series(np.full(len(values), np.nan), index=values.index, dtype=float)
    return moving_average(values, window)


def _centered_moving_average_or_nan(values: pd.Series, window: int) -> pd.Series:
    if len(values) < window:
        return pd.Series(np.full(len(values), np.nan), index=values.index, dtype=float)
    return moving_average(values, window, centered=True)


def fig_moving_average(data: pd.DataFrame | pd.Series | None, product: str | None = None) -> Figure:
    """Plot observed values with trailing and centered twelve-month averages."""
    frame = _product_frame(data, product)
    label = _product_label(frame, product)
    figure, axis = _new_figure()
    if len(frame) == 0:
        _empty_message(axis, f"Médias móveis — {label}")
        return figure
    month_idx = _month_index(_dates(frame))
    values = pd.Series(_values(frame), index=frame.index, dtype=float)
    _observed(axis, month_idx, values.to_numpy(), color="#1769aa", label="Observado", zorder=4)
    axis.plot(month_idx, _moving_average_or_nan(values, 3), color="#d95f02", label="MA(3)")
    axis.plot(month_idx, _moving_average_or_nan(values, 12), color="#1b9e77", label="MA(12) trailing")
    axis.plot(
        month_idx,
        _centered_moving_average_or_nan(values, 12),
        color="#7570b3",
        linestyle="--",
        label="MA(12) centrada 2×12",
    )
    axis.set_xlabel(_MONTH_AXIS_LABEL)
    return figure


def _result_value(result: Any, name: str, default: Any) -> Any:
    if result is None:
        return default
    return getattr(result, name, default)


def _regime_colors(labels: Sequence[object]) -> dict[object, str]:
    palette = ["#d73027", "#fc8d59", "#91bfdb", "#4575b4", "#1a9850"]
    return {
        label: palette[index % len(palette)] for index, label in enumerate(dict.fromkeys(labels))
    }


def fig_month_clusters(matrix: pd.DataFrame | None, result: Any = None) -> Figure:
    """Plot monthly seasonal profiles coloured by their seasonal regime."""
    frame = pd.DataFrame() if matrix is None else matrix.copy()
    figure, axis = _new_figure()
    labels = _result_value(result, "labels", pd.Series(dtype="object"))
    if len(frame) == 0:
        _empty_message(axis, "Perfis sazonais por regime")
        return figure
    regimes = [labels.get(month, "") for month in frame.index]
    colors = _regime_colors(regimes)
    for product in frame.columns:
        axis.plot(
            frame.index, frame[product], marker="o", color="#555555", alpha=0.45, label=str(product)
        )
    for regime in dict.fromkeys(regimes):
        members = [
            month for month, label in zip(frame.index, regimes, strict=True) if label == regime
        ]
        if len(members) == 0:
            continue
        axis.scatter(
            members,
            frame.loc[members].mean(axis=1),
            color=colors[regime],
            label=str(regime),
            zorder=4,
        )
    k = _result_value(result, "k", len(set(regimes)))
    silhouette = _result_value(result, "silhouette", float("nan"))
    axis.set_title(f"Perfis sazonais por regime (k={k}, silhouette={silhouette:.3f})")
    axis.set_xlabel("Mês")
    axis.set_ylabel("Índice sazonal")
    axis.legend()
    return figure


def fig_series_clusters(data: pd.DataFrame | None, result: Any = None) -> Figure:
    """Plot each product-year seasonal profile coloured by series cluster."""
    frame = _as_frame(data)
    figure, axis = _new_figure()
    if len(frame) == 0 or not {"produto", "ano", "mes", "unidades"}.issubset(frame.columns):
        _empty_message(axis, "Séries produto-ano por cluster")
        return figure
    labels = _result_value(result, "labels", pd.Series(dtype="object"))
    colors = _regime_colors(list(labels.dropna().unique())) if len(labels) > 0 else {}
    for (product, year), group in frame.groupby(["produto", "ano"], sort=False):
        key = (product, year)
        cluster = labels.get(key, labels.get(f"{product}_{year}", ""))
        line_color = colors.get(cluster, "#777777")
        label = f"{_product_label(group, product)} {year} (cluster {cluster})"
        ordered = group.sort_values("mes")
        axis.plot(ordered["mes"], ordered["unidades"], marker="o", color=line_color, label=label)
    k = _result_value(result, "k", "")
    silhouette = _result_value(result, "silhouette", float("nan"))
    axis.set_title(f"Séries produto-ano por cluster (k={k}, silhouette={silhouette:.3f})")
    axis.set_xlabel("Mês")
    axis.set_ylabel("Unidades")
    axis.legend(fontsize=8)
    return figure


def _prediction_frame(predictions: Any, product: str | None = None) -> pd.DataFrame:
    if predictions is None:
        return pd.DataFrame()
    if isinstance(predictions, pd.Series):
        return predictions.rename("previsao").to_frame()
    if isinstance(predictions, dict):
        rows = []
        for model, values in predictions.items():
            series = values if isinstance(values, pd.Series) else pd.Series(values)
            index = pd.to_datetime(series.index)
            rows.extend(
                {"data": date, "modelo": model, "previsao": value}
                for date, value in zip(index, series, strict=True)
            )
        return pd.DataFrame(rows)
    frame = predictions.copy()
    if "data" in frame.columns:
        frame["data"] = pd.to_datetime(frame["data"])
    if product is not None and "produto" in frame.columns:
        frame = frame.loc[frame["produto"].astype(str).eq(str(product))]
    return frame


def fig_backtest(
    actual: pd.DataFrame | pd.Series | None,
    predictions: Any = None,
    product: str | None = None,
    holdout_year: int = HOLDOUT_YEAR,
) -> Figure:
    """Plot every observed point (2022-2024) with the holdout backtest predictions overlaid."""
    actual_frame = _product_frame(actual, product)
    figure, axis = _new_figure()
    label = _product_label(actual_frame, product)
    if len(actual_frame) == 0:
        _empty_message(axis, f"Backtest {holdout_year} — {label}")
        return figure
    dates = _dates(actual_frame)
    values = _values(actual_frame)
    _observed(axis, _month_index(dates), values, color="#111111", label="Observado", zorder=4)
    holdout_mask = dates.year == holdout_year
    if bool(holdout_mask.any()):
        holdout_t = _month_index(dates[holdout_mask])
        axis.axvspan(
            holdout_t.min(),
            holdout_t.max(),
            color="#dddddd",
            alpha=0.3,
            label=f"Holdout ({holdout_year})",
            zorder=1,
        )
    prediction_frame = _prediction_frame(predictions, product)
    if len(prediction_frame) > 0:
        value_column = (
            "previsao" if "previsao" in prediction_frame.columns else "unidades_previstas"
        )
        if value_column in prediction_frame.columns:
            model_column = "modelo" if "modelo" in prediction_frame.columns else None
            model_values = (
                prediction_frame[model_column].drop_duplicates() if model_column else ["Modelo"]
            )
            for model in model_values:
                selected = (
                    prediction_frame
                    if model_column is None
                    else prediction_frame.loc[prediction_frame[model_column].eq(model)]
                )
                raw_x = selected["data"] if "data" in selected.columns else selected.index
                axis.plot(
                    _month_index(raw_x),
                    selected[value_column],
                    label=str(model),
                )
    axis.set_title(f"Backtest {holdout_year} — {label}")
    axis.set_xlabel(_MONTH_AXIS_LABEL)
    axis.set_ylabel("Unidades")
    axis.legend()
    return figure


def fig_best_model_fit(
    observed: pd.DataFrame | pd.Series | None,
    prediction_frame: pd.DataFrame | None,
    product: str | None = None,
    holdout_year: int = HOLDOUT_YEAR,
) -> Figure:
    """Plot the overall-best model's continuous output against observed points, T=0..47.

    ``prediction_frame`` must already carry the winning model's own reconstruction for every
    month it covers: in-sample fit for the training years, out-of-sample backtest for the
    holdout year, genuine forecast beyond history — one continuous curve, so the gap to the
    black observed dots is visible everywhere, not only inside the holdout window.
    """
    actual_frame = _product_frame(observed, product)
    figure, axis = _new_figure()
    label = _product_label(actual_frame, product)
    if len(actual_frame) == 0:
        _empty_message(axis, f"Melhor modelo — {label}")
        return figure
    dates = _dates(actual_frame)
    values = _values(actual_frame)
    _observed(axis, _month_index(dates), values, color="#111111", label="Observado", zorder=5, s=28)
    holdout_mask = dates.year == holdout_year
    if bool(holdout_mask.any()):
        holdout_t = _month_index(dates[holdout_mask])
        axis.axvspan(
            holdout_t.min(),
            holdout_t.max(),
            color="#dddddd",
            alpha=0.35,
            label=f"Holdout ({holdout_year})",
            zorder=1,
        )
    pred_frame = _forecast_plot_frame(prediction_frame)
    if product is not None and "produto" in pred_frame.columns:
        pred_frame = pred_frame.loc[pred_frame["produto"].astype(str).eq(str(product))]
    model_name = None
    if len(pred_frame) > 0 and "data" in pred_frame.columns:
        pred_frame = pred_frame.sort_values("data")
        value_column = (
            "unidades_previstas" if "unidades_previstas" in pred_frame.columns else "previsao"
        )
        if "modelo" in pred_frame.columns and pred_frame["modelo"].notna().any():
            model_name = str(pred_frame["modelo"].dropna().iloc[0])
        pred_dates = pd.to_datetime(pred_frame["data"])
        t_pred = _month_index(pred_dates)
        future_mask = (pred_dates.dt.year > holdout_year).to_numpy()
        if future_mask.any():
            future_t = t_pred[future_mask]
            axis.axvspan(
                future_t.min(),
                future_t.max(),
                color="#cfe8f3",
                alpha=0.35,
                label=f"Previsão {int(pred_dates.dt.year.max())}",
                zorder=1,
            )
        axis.plot(
            t_pred,
            pred_frame[value_column],
            color="#d95f02",
            linewidth=2.2,
            marker="o",
            markersize=3,
            label=f"Previsto ({model_name})" if model_name else "Previsto",
            zorder=4,
        )
    title = f"Melhor modelo — {label}"
    if model_name:
        title += f" ({model_name})"
    axis.set_title(title)
    axis.set_xlabel(MONTH_AXIS_LABEL)
    axis.set_ylabel("Unidades")
    axis.legend(loc="upper left", framealpha=0.9)
    axis.grid(True, alpha=0.3)
    axis.xaxis.set_major_locator(MaxNLocator(integer=True))
    return figure


def _metric_column(frame: pd.DataFrame, metric: str) -> str | None:
    candidates = {"mape": ("mape", "MAPE"), "mad": ("mad", "MAD")}
    for column in candidates.get(metric, (metric,)):
        if column in frame.columns:
            return column
    return None


def fig_metrics_bar(metrics: pd.DataFrame | None) -> Figure:
    """Plot MAPE bars by model and product, highlighting each winner."""
    frame = pd.DataFrame() if metrics is None else metrics.copy()
    figure, axis = _new_figure()
    metric_column = _metric_column(frame, "mape")
    if len(frame) == 0 or metric_column is None:
        _empty_message(axis, "MAPE por modelo")
        return figure
    frame["_label"] = frame.apply(
        lambda row: f"{row.get('produto', '')} — {row.get('modelo', '')}", axis=1
    )
    winners = frame.get("vencedor", pd.Series(False, index=frame.index)).astype(bool)
    colors = ["#d73027" if winner else "#9ecae1" for winner in winners]
    axis.bar(frame["_label"], frame[metric_column], color=colors)
    axis.set_title("MAPE por modelo e produto")
    axis.set_ylabel("MAPE (%)")
    axis.tick_params(axis="x", rotation=60)
    return figure


def fig_error_table(metrics: pd.DataFrame | None) -> Figure:
    """Render holdout metrics as a figure-table with formula footnotes."""
    frame = pd.DataFrame() if metrics is None else metrics.copy()
    figure, axis = _new_figure()
    axis.axis("off")
    columns = ["produto", "modelo", "mad", "mse", "rmse", "mape", "mpe"]
    available = [column for column in columns if column in frame.columns]
    if len(frame) == 0 or len(available) == 0:
        _empty_message(axis, "Tabela de erros")
        return figure
    body = frame[available].copy()
    for column in ["mad", "mse", "rmse", "mape", "mpe"]:
        if column in body.columns:
            body[column] = body[column].map(lambda value: f"{float(value):.4f}")
    widths = {
        "produto": 0.18,
        "modelo": 0.34,
        "mad": 0.10,
        "mse": 0.10,
        "rmse": 0.10,
        "mape": 0.10,
        "mpe": 0.10,
    }
    table = axis.table(
        cellText=body.values,
        colLabels=available,
        loc="center",
        cellLoc="center",
        colWidths=[widths[column] for column in available],
        bbox=[0.0, 0.13, 1.0, 0.74],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    winners = frame.get("vencedor", pd.Series(False, index=frame.index)).astype(bool)
    for row_number, winner in enumerate(winners, start=1):
        if winner:
            for column_number in range(len(available)):
                table[(row_number, column_number)].set_facecolor("#fee0d2")
    axis.set_title("Tabela de erros no holdout")
    figure.text(
        0.5, 0.02, metric_footnote(["mad", "mse", "rmse", "mape", "mpe"]), ha="center", fontsize=7
    )
    return figure


def fig_combined_error_table(metrics: pd.DataFrame | None) -> Figure:
    """Render the unified comparison table across every model (ML/classical + time series).

    Expects a ``grupo`` column distinguishing model families and a ``vencedor_geral`` column
    flagging the true best model per product across all families combined (see
    ``bebibem.models.select_overall_best``) — unlike ``fig_error_table``'s per-family
    ``vencedor``, which never compares across families.
    """
    frame = pd.DataFrame() if metrics is None else metrics.copy()
    figure, axis = _new_figure()
    axis.axis("off")
    columns = ["produto", "modelo", "grupo", "mad", "mse", "rmse", "mape", "mpe"]
    available = [column for column in columns if column in frame.columns]
    if len(frame) == 0 or "modelo" not in available:
        _empty_message(axis, "Tabela comparativa de todos os modelos")
        return figure
    body = frame[available].copy()
    for column in ["mad", "mse", "rmse", "mape", "mpe"]:
        if column in body.columns:
            body[column] = body[column].map(lambda value: f"{float(value):.4f}")
    widths = {
        "produto": 0.13,
        "modelo": 0.22,
        "grupo": 0.16,
        "mad": 0.11,
        "mse": 0.11,
        "rmse": 0.11,
        "mape": 0.11,
        "mpe": 0.11,
    }
    table = axis.table(
        cellText=body.values,
        colLabels=available,
        loc="center",
        cellLoc="center",
        colWidths=[widths[column] for column in available],
        bbox=[0.0, 0.13, 1.0, 0.74],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    winners = frame.get("vencedor_geral", pd.Series(False, index=frame.index)).astype(bool)
    for row_number, winner in enumerate(winners, start=1):
        if winner:
            for column_number in range(len(available)):
                table[(row_number, column_number)].set_facecolor("#fee0d2")
    axis.set_title("Tabela comparativa de erros — todos os modelos (ML/regressão + séries temporais)")
    figure.text(
        0.5, 0.02, metric_footnote(["mad", "mse", "rmse", "mape", "mpe"]), ha="center", fontsize=7
    )
    return figure


def fig_forecast_2025_summary_table(summary: pd.DataFrame | None) -> Figure:
    """Render the final 2025 total-per-product table, including the grand-total row.

    Expects ``produto_label``, ``modelo`` and ``unidades_previstas_total`` columns; a row whose
    ``modelo`` is ``"—"`` is treated as the grand-total row and highlighted.
    """
    frame = pd.DataFrame() if summary is None else summary.copy()
    figure, axis = _new_figure()
    axis.axis("off")
    columns = ["produto_label", "modelo", "unidades_previstas_total"]
    available = [column for column in columns if column in frame.columns]
    if len(frame) == 0 or "unidades_previstas_total" not in available:
        _empty_message(axis, "Previsão total 2025 por produto e total geral")
        return figure
    body = frame[available].copy()
    body["unidades_previstas_total"] = body["unidades_previstas_total"].map(
        lambda value: f"{int(value)}"
    )
    widths = {"produto_label": 0.4, "modelo": 0.4, "unidades_previstas_total": 0.2}
    table = axis.table(
        cellText=body.values,
        colLabels=["Produto", "Modelo vencedor", "Total previsto 2025"],
        loc="center",
        cellLoc="center",
        colWidths=[widths[column] for column in available],
        bbox=[0.0, 0.2, 1.0, 0.6],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    is_total_row = frame["modelo"].astype(str).eq("—")
    for row_number, is_total in enumerate(is_total_row, start=1):
        if is_total:
            for column_number in range(len(available)):
                cell = table[(row_number, column_number)]
                cell.set_facecolor("#fee0d2")
                cell.set_text_props(fontweight="bold")
    axis.set_title("Previsão total 2025 por produto e total geral")
    return figure


def _fit_regressions(values: np.ndarray) -> dict[str, Any]:
    from .regression import exponential_regression_loglinear, linear_regression_normal_equation

    x_values = np.arange(len(values), dtype=float)
    return {
        "linear_normal_equation": linear_regression_normal_equation(x_values, values),
        "exponential_loglinear": exponential_regression_loglinear(x_values, values),
    }


def fig_regression(
    data: pd.DataFrame | pd.Series | None,
    fits: Any = None,
    product: str | None = None,
) -> Figure:
    """Plot classical linear and equivalent exponential fits once each."""
    if isinstance(fits, str) and product is None:
        product = fits
        fits = None
    frame = _product_frame(data, product)
    label = _product_label(frame, product)
    figure, axis = _new_figure()
    if len(frame) == 0:
        _empty_message(axis, f"Regressões — {label}")
        return figure
    month_idx = _month_index(_dates(frame))
    values = _values(frame)
    valid = np.isfinite(values)
    if valid.sum() == 0:
        _empty_message(axis, f"Regressões — {label}")
        return figure
    _observed(axis, month_idx, values, color="#111111", label="Observado", zorder=4)
    observed_values = values[valid]
    observed_positions = np.flatnonzero(valid).astype(float)
    selected_fits = _fit_regressions(observed_values) if fits is None else fits
    if isinstance(selected_fits, (list, tuple)):
        selected_fits = {fit.name: fit for fit in selected_fits}
    if "exponential_loglinear" in selected_fits and "exponential_normal_equation" in selected_fits:
        equivalent_fit = selected_fits["exponential_loglinear"]
        selected_fits = {
            name: fit
            for name, fit in selected_fits.items()
            if name not in {"exponential_loglinear", "exponential_normal_equation"}
        }
        selected_fits["exponential_equivalent"] = equivalent_fit
    dense_positions = np.linspace(observed_positions[0], observed_positions[-1], 200)
    for name, fit in selected_fits.items():
        if fit is None:
            continue
        if getattr(fit, "applicable", True) is False:
            axis.text(0.02, 0.96, f"{name}: not_applicable", transform=axis.transAxes, va="top")
            continue
        curve = fit.predict(dense_positions)
        display_name = (
            "exponencial (loglinear/equação normal equivalente)"
            if name == "exponential_equivalent"
            else str(name)
        )
        axis.plot(dense_positions, curve, label=display_name)
        equation = f"{fit.equation}\nR² = {fit.r2:.4f}"
        axis.text(
            0.02,
            0.96 - 0.13 * list(selected_fits).index(name),
            equation,
            transform=axis.transAxes,
            va="top",
        )
    axis.set_title(f"Regressões — {label}")
    axis.set_xlabel(_MONTH_AXIS_LABEL)
    axis.set_ylabel("Unidades")
    axis.legend()
    return figure


def fig_confusion_matrix(result: Any = None, matrix: np.ndarray | None = None) -> Figure:
    """Render a two-by-two regime confusion matrix with absolute counts."""
    if matrix is None and isinstance(result, np.ndarray):
        matrix = result
    if matrix is None:
        matrix = _result_value(result, "confusion", np.zeros((2, 2), dtype=int))
    values = np.asarray(matrix, dtype=int).reshape(2, 2)
    figure, axis = _new_figure()
    image = axis.imshow(values, cmap="Blues")
    del image
    for row in range(2):
        for column in range(2):
            axis.text(
                column, row, str(values[row, column]), ha="center", va="center", color="black"
            )
    axis.set_xticks([0, 1], labels=["Predito: não alta", "Predito: alta"])
    axis.set_yticks([0, 1], labels=["Real: não alta", "Real: alta"])
    axis.set_title("Matriz de confusão — regime sazonal")
    figure.colorbar(axis.images[0], ax=axis, fraction=0.046, pad=0.04)
    figure.text(
        0.5, 0.01, metric_footnote(["accuracy", "precision_recall", "f1"]), ha="center", fontsize=8
    )
    return figure


def _forecast_plot_frame(forecast: Any) -> pd.DataFrame:
    if forecast is None:
        return pd.DataFrame()
    if isinstance(forecast, pd.Series):
        series = forecast.copy()
        series.index = pd.to_datetime(series.index)
        return pd.DataFrame(
            {"data": series.index, "unidades_previstas": series.to_numpy(dtype=float)}
        )
    frame = forecast.copy() if isinstance(forecast, pd.DataFrame) else pd.DataFrame(forecast)
    if "data" in frame.columns:
        frame["data"] = pd.to_datetime(frame["data"])
        return frame
    if {"ano", "mes"}.issubset(frame.columns):
        frame["data"] = pd.to_datetime(
            frame[["ano", "mes"]].assign(day=1).rename(columns={"ano": "year", "mes": "month"})
        )
        return frame
    if isinstance(frame.index, pd.DatetimeIndex):
        frame = frame.reset_index(names="data")
        frame["data"] = pd.to_datetime(frame["data"])
    return frame


def _forecast_metadata(
    frame: pd.DataFrame,
    product: str | None,
    model: str | None,
    mape: float | None,
    mad: float | None,
    holdout_metrics: pd.DataFrame | None,
    best_models: Any,
) -> tuple[str, float | None, float | None]:
    selected_model = model
    if selected_model is None and "modelo" in frame.columns and len(frame) > 0:
        selected_model = str(frame["modelo"].dropna().iloc[0])
    if selected_model is None and isinstance(best_models, dict) and product in best_models:
        selected_model = str(best_models[product])
    selected_mape = mape
    selected_mad = mad
    if len(frame) > 0:
        if selected_mape is None and "mape_holdout" in frame.columns:
            selected_mape = float(frame["mape_holdout"].dropna().iloc[0])
        if selected_mad is None and "mad_holdout" in frame.columns:
            selected_mad = float(frame["mad_holdout"].dropna().iloc[0])
    if holdout_metrics is not None and selected_model is not None and len(holdout_metrics) > 0:
        selected = holdout_metrics
        if product is not None and "produto" in selected.columns:
            selected = selected.loc[selected["produto"].astype(str).eq(str(product))]
        if "modelo" in selected.columns:
            selected = selected.loc[selected["modelo"].astype(str).eq(str(selected_model))]
        if len(selected) > 0:
            if selected_mape is None and "mape" in selected.columns:
                selected_mape = float(selected.iloc[0]["mape"])
            if selected_mad is None and "mad" in selected.columns:
                selected_mad = float(selected.iloc[0]["mad"])
    return str(selected_model or "modelo não informado"), selected_mape, selected_mad


def _metric_text(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/d"
    return f"{float(value):.2f}"


def _bridge(
    prev_t: np.ndarray, prev_v: np.ndarray, next_t: np.ndarray, next_v: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Prepend the previous segment's last point so two plot() calls join with no visual gap."""
    if len(prev_t) == 0 or len(next_t) == 0:
        return np.asarray(next_t), np.asarray(next_v)
    return (
        np.concatenate([[prev_t[-1]], np.asarray(next_t)]),
        np.concatenate([[prev_v[-1]], np.asarray(next_v)]),
    )


def fig_forecast_product(
    history: pd.DataFrame | pd.Series | None,
    forecast: Any = None,
    product: str | None = None,
    model: str | None = None,
    mape: float | None = None,
    mad: float | None = None,
    holdout_metrics: pd.DataFrame | None = None,
    best_models: Any = None,
) -> Figure:
    """Plot one product's historical series and future forecast distinctly."""
    history_frame = _product_frame(history, product)
    future_frame = _forecast_plot_frame(forecast)
    if product is not None and "produto" in future_frame.columns:
        future_frame = future_frame.loc[future_frame["produto"].astype(str).eq(str(product))]
    label = _product_label(history_frame, product)
    figure, axis = _new_figure()
    if len(history_frame) == 0 and len(future_frame) == 0:
        _empty_message(axis, f"Previsão — {label}")
        return figure
    selected_model, selected_mape, selected_mad = _forecast_metadata(
        future_frame, product, model, mape, mad, holdout_metrics, best_models
    )
    history_month_idx = np.array([])
    history_values = np.array([])
    if len(history_frame) > 0:
        history_month_idx = _month_index(_dates(history_frame))
        history_values = _values(history_frame)
        valid_history = np.isfinite(history_values)
        if valid_history.any():
            history_month_idx = history_month_idx[valid_history]
            history_values = history_values[valid_history]
            axis.plot(
                history_month_idx,
                history_values,
                color="#1769aa",
                marker="o",
                label="Histórico 2022–2024",
            )
    value_column = (
        "unidades_previstas" if "unidades_previstas" in future_frame.columns else "previsao"
    )
    if (
        len(future_frame) > 0
        and value_column in future_frame.columns
        and "data" in future_frame.columns
    ):
        bridged_t, bridged_vals = _bridge(
            history_month_idx,
            history_values,
            _month_index(future_frame["data"]),
            future_frame[value_column].to_numpy(dtype=float),
        )
        axis.plot(
            bridged_t,
            bridged_vals,
            color="#d95f02",
            linestyle="--",
            marker="o",
            label=f"Previsão ({selected_model})",
        )
    title = (
        f"Previsão — {label} | {selected_model} | "
        f"MAPE={_metric_text(selected_mape)}% | MAD={_metric_text(selected_mad)}"
    )
    axis.set_title(title)
    axis.set_xlabel(_MONTH_AXIS_LABEL)
    axis.set_ylabel("Unidades")
    axis.legend()
    return figure


def fig_forecast_all(
    history: pd.DataFrame | None,
    forecasts: Any = None,
    best_models: Any = None,
    holdout_metrics: pd.DataFrame | None = None,
) -> Figure:
    """Plot all products with historical solid and forecast dashed lines."""
    history_frame = _as_frame(history)
    forecast_frame = _forecast_plot_frame(forecasts)
    figure, axis = _new_figure()
    products = _product_values(history_frame)
    if len(products) == 0 and "produto" in forecast_frame.columns:
        products = [str(value) for value in forecast_frame["produto"].dropna().drop_duplicates()]
    if len(products) == 0:
        _empty_message(axis, "Previsão — todas as linhas")
        return figure
    colors = _regime_colors(products)
    for product in products:
        historical = _product_frame(history_frame, product)
        label = _product_label(historical, product)
        hist_month_idx = np.array([])
        hist_values = np.array([])
        if len(historical) > 0:
            hist_month_idx = _month_index(_dates(historical))
            hist_values = _values(historical)
            valid = np.isfinite(hist_values)
            if valid.any():
                hist_month_idx = hist_month_idx[valid]
                hist_values = hist_values[valid]
                axis.plot(
                    hist_month_idx,
                    hist_values,
                    color=colors[product],
                    marker="o",
                    markersize=4,
                    label=f"{label} histórico",
                )
        future = forecast_frame
        if "produto" in future.columns:
            future = future.loc[future["produto"].astype(str).eq(str(product))]
        selected_model, selected_mape, selected_mad = _forecast_metadata(
            future, product, None, None, None, holdout_metrics, best_models
        )
        value_column = (
            "unidades_previstas" if "unidades_previstas" in future.columns else "previsao"
        )
        if len(future) == 0 or value_column not in future.columns or "data" not in future.columns:
            continue
        legend = (
            f"{label} previsão ({selected_model}, "
            f"MAPE={_metric_text(selected_mape)}%, MAD={_metric_text(selected_mad)})"
        )
        bridged_t, bridged_vals = _bridge(
            hist_month_idx,
            hist_values,
            _month_index(future["data"]),
            future[value_column].to_numpy(dtype=float),
        )
        axis.plot(
            bridged_t,
            bridged_vals,
            color=colors[product],
            linestyle="--",
            marker="o",
            markersize=4,
            label=legend,
        )
    axis.set_title("Previsão — todas as linhas")
    axis.set_xlabel(_MONTH_AXIS_LABEL)
    axis.set_ylabel("Unidades")
    axis.legend(fontsize=8)
    return figure


def _forecast_year_2025(forecast_frame: pd.DataFrame | None) -> pd.DataFrame:
    frame = _as_frame(forecast_frame)
    if len(frame) == 0 or "ano" not in frame.columns:
        return pd.DataFrame()
    return frame.loc[frame["ano"].eq(2025)].copy()


def fig_forecast_2025_bar(
    forecast_frame: pd.DataFrame | None, product: str, best_models: Any = None
) -> Figure:
    """Bar chart of the 2025-only monthly forecast for a single product.

    Deliberately isolated from the 2022-2024 history: bars are the forecast, `fig_historical_bar`
    already owns the observed-vs-predicted comparison, and scattering point-in-time observed
    dots inside a bar chart mixes incompatible chart geometries.
    """
    apply_style()
    year_2025 = _forecast_year_2025(forecast_frame)
    subset = (
        year_2025.loc[year_2025[_PRODUCT_COLUMN].astype(str).eq(str(product))].sort_values("mes")
        if len(year_2025) > 0 and _PRODUCT_COLUMN in year_2025.columns
        else pd.DataFrame()
    )
    figure, axis = _new_figure()
    if len(subset) == 0:
        _empty_message(axis, f"Previsão 2025 — {product}")
        return figure
    value_column = "unidades_previstas" if "unidades_previstas" in subset.columns else "previsao"
    label = _product_label(subset, product)
    model_name = None
    if "modelo" in subset.columns:
        model_name = str(subset["modelo"].dropna().iloc[0])
    elif isinstance(best_models, dict):
        model_name = best_models.get(product)
    month_index = _global_month_index(subset["ano"].to_numpy(), subset["mes"].to_numpy())
    bars = axis.bar(month_index, subset[value_column], color="#1f77b4")
    axis.bar_label(bars, fmt="%.0f", padding=4, rotation=90, fontsize=8)
    axis.set_xticks(np.arange(36, 48))
    axis.set_xlabel("T (índice inteiro do mês, T=36 em janeiro de 2025)")
    axis.set_ylabel("unidades previstas")
    annual_total = float(subset[value_column].sum())
    title = f"Previsão 2025 — {label}"
    if model_name:
        title += f" ({model_name})"
    title += f" — total do ano = {annual_total:,.0f} unidades".replace(",", ".")
    axis.set_title(title)
    axis.margins(y=0.28)
    axis.grid(alpha=0.3, axis="y")
    return figure


def fig_forecast_2025_total_bar(forecast_frame: pd.DataFrame | None) -> Figure:
    """Bar chart of the 2025-only monthly forecast summed across every product.

    Deliberately isolated from history for the same reason as `fig_forecast_2025_bar`.
    """
    apply_style()
    year_2025 = _forecast_year_2025(forecast_frame)
    figure, axis = _new_figure()
    if len(year_2025) == 0:
        _empty_message(axis, "Previsão 2025 — total de todas as linhas")
        return figure
    value_column = "unidades_previstas" if "unidades_previstas" in year_2025.columns else "previsao"
    total_by_month = year_2025.groupby("mes")[value_column].sum().reindex(range(1, 13)).fillna(0.0)
    annual_total = float(total_by_month.sum())
    month_index = _global_month_index(
        np.full(len(total_by_month), 2025), total_by_month.index.to_numpy()
    )
    bars = axis.bar(month_index, total_by_month.to_numpy(), color="#7f7f7f")
    axis.bar_label(bars, fmt="%.0f", padding=4, rotation=90, fontsize=8)
    axis.set_xticks(np.arange(36, 48))
    axis.set_xlabel("T (índice inteiro do mês, T=36 em janeiro de 2025)")
    axis.set_ylabel("unidades previstas (soma das linhas)")
    axis.set_title(
        f"Previsão 2025 — total de todas as linhas (soma do ano = {annual_total:,.0f} unidades)".replace(
            ",", "."
        )
    )
    axis.margins(y=0.28)
    axis.grid(alpha=0.3, axis="y")
    return figure


def fig_forecast_2025_curves_all(
    forecast_frame: pd.DataFrame | None,
    holdout_metrics: pd.DataFrame | None = None,
    history: pd.DataFrame | None = None,
) -> Figure:
    """Line chart overlaying every product's 2025-only forecast from its overall winning model.

    One curve per product, labeled with its model and holdout MAPE (DEM-27 AC3). The x-axis is
    the continuous integer month index `T`. When ``history`` is given, each product's 2022-2024
    observed points (T=0..35) are plotted first in the same color, bridged into its 2025
    forecast, so the whole T=0..47 timeline is comparable in one figure.
    """
    apply_style()
    year_2025 = _forecast_year_2025(forecast_frame)
    figure, axis = _new_figure()
    products = _product_values(year_2025) if len(year_2025) > 0 else []
    if len(products) == 0:
        _empty_message(axis, "Previsão 2025 — curvas por linha")
        return figure
    value_column = "unidades_previstas" if "unidades_previstas" in year_2025.columns else "previsao"
    colors = _regime_colors(products)
    history_frame = _as_frame(history)
    has_history = len(history_frame) > 0
    for product in products:
        subset = year_2025.loc[
            year_2025[_PRODUCT_COLUMN].astype(str).eq(str(product))
        ].sort_values("mes")
        if len(subset) == 0:
            continue
        label = _product_label(subset, product)
        model_name = str(subset["modelo"].dropna().iloc[0]) if "modelo" in subset.columns else None
        mape_value = None
        if (
            holdout_metrics is not None
            and model_name is not None
            and {"produto", "modelo"}.issubset(holdout_metrics.columns)
        ):
            matched = holdout_metrics.loc[
                holdout_metrics["produto"].astype(str).eq(str(product))
                & holdout_metrics["modelo"].astype(str).eq(str(model_name))
            ]
            if len(matched) > 0 and "mape" in matched.columns:
                mape_value = float(matched.iloc[0]["mape"])
        month_index = _global_month_index(subset["ano"].to_numpy(), subset["mes"].to_numpy())
        legend = (
            f"{label} ({model_name}, MAPE={_metric_text(mape_value)}%)" if model_name else label
        )
        product_history = _product_frame(history_frame, product)
        history_t = np.array([])
        history_v = np.array([])
        if len(product_history) > 0:
            history_t = _month_index(_dates(product_history))
            history_v = _values(product_history)
            valid = np.isfinite(history_v)
            history_t, history_v = history_t[valid], history_v[valid]
            if len(history_t) > 0:
                axis.plot(
                    history_t,
                    history_v,
                    color=colors[product],
                    marker="o",
                    markersize=4,
                    linewidth=1.6,
                )
        bridged_t, bridged_vals = _bridge(
            history_t, history_v, month_index, subset[value_column].to_numpy(dtype=float)
        )
        axis.plot(
            bridged_t,
            bridged_vals,
            marker="o",
            linestyle="--" if len(history_t) > 0 else "-",
            color=colors[product],
            label=legend,
        )
    if has_history:
        axis.set_xlabel(_MONTH_AXIS_LABEL)
        axis.xaxis.set_major_locator(MaxNLocator(integer=True))
    else:
        axis.set_xticks(np.arange(36, 48))
        axis.set_xlabel("T (índice inteiro do mês, T=36 em janeiro de 2025)")
    axis.set_ylabel("unidades")
    axis.set_title("Previsão 2025 — curvas por linha (modelo vencedor geral por produto)")
    axis.legend(fontsize=8)
    axis.grid(alpha=0.3)
    return figure


_MONTH_NAMES_PT = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)


def fig_historical_bar(
    frame: pd.DataFrame | None,
    product: str,
    forecast_frame: pd.DataFrame | None = None,
) -> Figure:
    """Bar chart comparing observed sales against each year's model prediction, per product.

    ``forecast_frame`` may carry predictions for any subset of years (in-sample reconstruction
    for 2022-2024, genuine forecast for 2025): every year present gets its own "previsto" bar
    right next to that year's "vendido" bar, sharing the same color; a year with no observed
    data (2025) shows only the forecast bar. The x-axis uses month names.
    """
    data = _as_frame(frame)
    apply_style()
    subset = (
        data.loc[data[_PRODUCT_COLUMN].astype(str).eq(str(product))]
        if len(data) > 0 and _PRODUCT_COLUMN in data.columns
        else pd.DataFrame()
    )
    figure, axis = _new_figure()
    if len(subset) == 0 or "ano" not in subset.columns or "mes" not in subset.columns:
        _empty_message(axis, f"Vendas por mês — {product}")
        return figure
    label = _product_label(subset, product)

    observed_by_year = {
        int(year): subset.loc[subset["ano"].eq(year)].sort_values("mes")
        for year in subset["ano"].dropna().unique()
    }
    forecast_by_year: dict[int, pd.DataFrame] = {}
    forecast_data = _as_frame(forecast_frame)
    if len(forecast_data) > 0 and _PRODUCT_COLUMN in forecast_data.columns:
        forecast_subset = forecast_data.loc[
            forecast_data[_PRODUCT_COLUMN].astype(str).eq(str(product))
        ]
        value_column = (
            "unidades_previstas" if "unidades_previstas" in forecast_subset.columns else "previsao"
        )
        if len(forecast_subset) > 0 and value_column in forecast_subset.columns and "ano" in forecast_subset.columns:
            for year in forecast_subset["ano"].dropna().unique():
                forecast_by_year[int(year)] = (
                    forecast_subset.loc[forecast_subset["ano"].eq(year)]
                    .sort_values("mes")
                    .rename(columns={value_column: _VALUE_COLUMN})
                )

    year_groups: list[tuple[int, pd.DataFrame, bool]] = []
    for year in sorted(set(observed_by_year) | set(forecast_by_year)):
        if year in observed_by_year:
            year_groups.append((year, observed_by_year[year], False))
        if year in forecast_by_year:
            year_groups.append((year, forecast_by_year[year], True))

    n_groups = len(year_groups)
    bar_width = 0.8 / max(n_groups, 1)
    colors = _regime_colors([str(year) for year, _, _ in year_groups])
    for offset, (year, year_data, is_forecast) in enumerate(year_groups):
        month_positions = year_data["mes"].to_numpy(dtype=float) - 1.0
        positions = month_positions + (offset - (n_groups - 1) / 2) * bar_width
        total = float(year_data[_VALUE_COLUMN].sum())
        total_text = f"{total:,.0f}".replace(",", ".")
        suffix = "previsto" if is_forecast else "vendido"
        legend_label = f"{year} ({suffix}, total={total_text})"
        bars = axis.bar(
            positions,
            year_data[_VALUE_COLUMN],
            width=bar_width,
            label=legend_label,
            color=colors[str(year)],
            hatch="//" if is_forecast else None,
            alpha=0.85 if is_forecast else 1.0,
        )
        axis.bar_label(bars, fmt="%.0f", fontsize=5, padding=2, rotation=90)
    axis.set_xticks(range(12))
    axis.set_xticklabels(_MONTH_NAMES_PT, rotation=45, ha="right")
    axis.set_xlabel("Mês")
    axis.set_ylabel("unidades vendidas")
    axis.set_title(f"Vendas por mês — {label} — observado vs. previsto por ano")
    axis.legend(title="Ano", fontsize=8)
    axis.margins(y=0.35)
    axis.grid(alpha=0.3, axis="y")
    return figure


def fig_capacity(
    capacity: pd.DataFrame | None = None,
    demand: pd.DataFrame | None = None,
    units_per_case: int | None = None,
) -> Figure:
    """Plot documented capacity before/after expansion and optional case demand."""
    from .capacity import capacity_frame, demand_in_cases

    frame = capacity_frame() if capacity is None else capacity.copy()
    figure, axis = _new_figure()
    required = {"produto", "antes", "depois"}
    missing = sorted(required.difference(frame.columns))
    if len(frame) == 0:
        _empty_message(axis, "Capacidade fabril")
        return figure
    if len(missing) > 0:
        _empty_message(axis, f"Capacidade fabril — colunas ausentes: {missing}")
        return figure
    labels = frame["produto"].astype(str).tolist()
    positions = np.arange(len(frame), dtype=float)
    width = 0.36
    axis.bar(positions - width / 2, frame["antes"], width, label="Antes")
    axis.bar(positions + width / 2, frame["depois"], width, label="Depois")
    deltas = frame["delta"] if "delta" in frame.columns else frame["depois"] - frame["antes"]
    for position, (_, row), delta in zip(positions, frame.iterrows(), deltas, strict=True):
        axis.annotate(
            f"Δ {float(delta):,.0f}".replace(",", "."),
            (position, max(row["antes"], row["depois"])),
            ha="center",
            va="bottom",
            fontsize=8,
        )
    axis.set_xticks(positions, labels=labels)
    axis.set_ylabel("Caixas/mês")
    title = "Capacidade fabril — antes e depois da expansão"
    if units_per_case is not None:
        title = f"{title} ({units_per_case} unidades/caixa)"
    axis.set_title(title)
    axis.legend()
    if demand is None or units_per_case is None:
        return figure
    converted = demand_in_cases(demand, units_per_case)
    if converted is None or len(converted) == 0:
        return figure
    demand_by_product = converted.groupby("produto")["caixas"].max()
    total_by_month = converted.groupby(["ano", "mes"])["caixas"].sum()
    total_peak = float(total_by_month.max())
    demand_values = [
        total_peak if label == "total" else float(demand_by_product.get(label, np.nan))
        for label in labels
    ]
    demand_axis = axis.twinx()
    demand_axis.plot(
        positions,
        demand_values,
        color="#762a83",
        marker="o",
        linestyle=":",
        label="Demanda prevista (pico mensal)",
    )
    demand_axis.set_ylabel("Demanda prevista (caixas/mês)")
    demand_axis.legend(loc="upper left")
    return figure
