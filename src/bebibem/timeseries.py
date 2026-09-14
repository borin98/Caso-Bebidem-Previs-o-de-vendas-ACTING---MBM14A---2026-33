"""Time series modeling and evaluation: Holt-Winters, SARIMA, and Fourier harmonic regression."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

from .config import FIGURE_FORMATS, HOLDOUT_YEAR, MONTH_AXIS_LABEL, month_index
from .models import metrics
from .plotting import annotate_equation, apply_style, save_figure

LOGGER = logging.getLogger(__name__)

P_ANNUAL = 12.0


@dataclass
class TimeSeriesModelResult:
    """Encapsulates fit, in-sample values, out-of-sample forecast, and model metadata."""

    name: str
    display_name: str
    model: Any = field(repr=False)
    fitted_values: pd.Series
    forecast: pd.Series
    params: dict[str, Any]
    equation: str
    applicable: bool = True
    note: str | None = None


def _clean_series(data: pd.Series | pd.DataFrame) -> pd.Series:
    """Normalize input into a sorted datetime-indexed float series."""
    if isinstance(data, pd.DataFrame):
        frame = data.copy()
        if "data" in frame.columns and "unidades" in frame.columns:
            frame["data"] = pd.to_datetime(frame["data"])
            series = frame.sort_values("data").set_index("data")["unidades"]
            return series.astype(float)
        raise ValueError("DataFrame deve conter colunas 'data' e 'unidades'")
    series = data.copy()
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index)
    return series.sort_index().astype(float)


def _format_num(val: float) -> str:
    """Format float for display equations."""
    if abs(val) < 1e-4 or abs(val) >= 1e4:
        return f"{val:.3e}"
    return f"{val:.4g}"


def holt_winters_multiplicative(
    train_series: pd.Series,
    horizon: int = 12,
    seasonal_periods: int = 12,
) -> TimeSeriesModelResult:
    """Fit multiplicative Holt-Winters exponential smoothing model."""
    series = _clean_series(train_series)
    if len(series) < 2 * seasonal_periods:
        return TimeSeriesModelResult(
            name="holt_winters_multiplicative",
            display_name="Holt-Winters Multiplicativo",
            model=None,
            fitted_values=pd.Series(dtype=float),
            forecast=pd.Series(dtype=float),
            params={},
            equation="Dados insuficientes (< 24 períodos)",
            applicable=False,
            note="dados_insuficientes",
        )
    if (series <= 0).any():
        return TimeSeriesModelResult(
            name="holt_winters_multiplicative",
            display_name="Holt-Winters Multiplicativo",
            model=None,
            fitted_values=pd.Series(dtype=float),
            forecast=pd.Series(dtype=float),
            params={},
            equation="Valores não-positivos presentes (incompatível com multiplicativo)",
            applicable=False,
            note="valores_nao_positivos",
        )
    model = ExponentialSmoothing(
        series,
        trend="add",
        seasonal="mul",
        seasonal_periods=seasonal_periods,
        initialization_method="estimated",
    )
    fit_result = model.fit()
    forecast_values = fit_result.forecast(horizon)
    alpha = fit_result.params.get("smoothing_level", np.nan)
    beta = fit_result.params.get("smoothing_trend", np.nan)
    gamma = fit_result.params.get("smoothing_seasonal", np.nan)
    equation = (
        r"$\hat{y}_{t+h} = (\ell_t + h b_t) s_{t+h-12}$"
        f"\n"
        rf"$\alpha={_format_num(alpha)}, \beta={_format_num(beta)}, \gamma={_format_num(gamma)}$"
    )
    return TimeSeriesModelResult(
        name="holt_winters_multiplicative",
        display_name="Holt-Winters Multiplicativo",
        model=fit_result,
        fitted_values=pd.Series(fit_result.fittedvalues, index=series.index),
        forecast=pd.Series(forecast_values),
        params={"alpha": alpha, "beta": beta, "gamma": gamma},
        equation=equation,
        applicable=True,
    )


def sarima_forecast(
    train_series: pd.Series,
    horizon: int = 12,
    order: tuple[int, int, int] = (1, 0, 0),
    seasonal_order: tuple[int, int, int, int] = (1, 0, 0, 12),
) -> TimeSeriesModelResult:
    """Fit seasonal autoregressive moving average (SARIMA) model."""
    series = _clean_series(train_series)
    if len(series) < 24:
        return TimeSeriesModelResult(
            name="sarima",
            display_name="SARIMA",
            model=None,
            fitted_values=pd.Series(dtype=float),
            forecast=pd.Series(dtype=float),
            params={},
            equation="Dados insuficientes (< 24 observações)",
            applicable=False,
            note="dados_insuficientes",
        )
    note = None
    try:
        model = SARIMAX(
            series,
            order=order,
            seasonal_order=seasonal_order,
            trend="c",
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        fit_result = model.fit(disp=False, maxiter=200)
        forecast_values = fit_result.forecast(horizon)
        # Check stability against extreme explosion
        max_train = float(series.max())
        if (forecast_values > 10 * max_train).any() or (forecast_values < -2 * max_train).any():
            note = "mle_instabilidade_divergente"
            forecast_values = np.clip(forecast_values, 0, 10 * max_train)
        fitted_values = pd.Series(fit_result.fittedvalues, index=series.index)
        ar_param = fit_result.params.get("ar.L1", np.nan)
        sar_param = fit_result.params.get("ar.S.L12", np.nan)
        intercept = fit_result.params.get("intercept", np.nan)
        equation = (
            rf"$\mathrm{{SARIMA}}({order[0]},{order[1]},{order[2]})\times({seasonal_order[0]},{seasonal_order[1]},{seasonal_order[2]})_{{12}}$"
            f"\n"
            rf"$\phi_1={_format_num(ar_param)}, \Phi_1={_format_num(sar_param)}, c={_format_num(intercept)}$"
        )
        return TimeSeriesModelResult(
            name="sarima",
            display_name=f"SARIMA({order[0]},{order[1]},{order[2]})({seasonal_order[0]},{seasonal_order[1]},{seasonal_order[2]})₁₂",
            model=fit_result,
            fitted_values=fitted_values,
            forecast=pd.Series(forecast_values),
            params={"phi_1": ar_param, "Phi_1": sar_param, "intercept": intercept},
            equation=equation,
            applicable=True,
            note=note,
        )
    except Exception as error:  # noqa: BLE001
        LOGGER.warning("Falha ao ajustar SARIMA: %s", error)
        return TimeSeriesModelResult(
            name="sarima",
            display_name="SARIMA",
            model=None,
            fitted_values=pd.Series(dtype=float),
            forecast=pd.Series(dtype=float),
            params={},
            equation=f"Erro de convergência: {error}",
            applicable=False,
            note=f"erro_ajuste: {error}",
        )


def fourier_regression(
    train_series: pd.Series,
    horizon: int = 12,
    period: float = P_ANNUAL,
    k_harmonics: int = 2,
) -> TimeSeriesModelResult:
    """Fit harmonic regression with linear trend and K trigonometric harmonics."""
    series = _clean_series(train_series)
    n = len(series)
    if n < 2 * k_harmonics + 2:
        return TimeSeriesModelResult(
            name="fourier_harmonic",
            display_name="Fourier (Regressão Harmônica)",
            model=None,
            fitted_values=pd.Series(dtype=float),
            forecast=pd.Series(dtype=float),
            params={},
            equation="Dados insuficientes para K harmônicos",
            applicable=False,
            note="dados_insuficientes",
        )
    t_train = np.arange(n, dtype=float)
    cols = [np.ones(n), t_train]
    for k in range(1, k_harmonics + 1):
        freq = 2.0 * np.pi * k / period
        cols.append(np.cos(freq * t_train))
        cols.append(np.sin(freq * t_train))
    x_train = np.column_stack(cols)
    y_train = series.to_numpy(dtype=float)
    coefs, *_ = np.linalg.lstsq(x_train, y_train, rcond=None)
    fitted = x_train @ coefs
    # In-sample R2
    total_ss = float(np.sum((y_train - y_train.mean()) ** 2))
    residual_ss = float(np.sum((y_train - fitted) ** 2))
    r2 = 1.0 - (residual_ss / total_ss) if total_ss > 0 else 1.0
    # Future forecast
    t_future = np.arange(n, n + horizon, dtype=float)
    future_cols = [np.ones(horizon), t_future]
    for k in range(1, k_harmonics + 1):
        freq = 2.0 * np.pi * k / period
        future_cols.append(np.cos(freq * t_future))
        future_cols.append(np.sin(freq * t_future))
    x_future = np.column_stack(future_cols)
    predicted_future = x_future @ coefs
    # Future dates
    start_future = series.index[-1] + pd.DateOffset(months=1)
    future_dates = pd.date_range(start_future, periods=horizon, freq="MS")
    # Equation text
    a0, b = coefs[0], coefs[1]
    b_sign = "+" if b >= 0 else "-"
    equation_lines = [
        rf"$y(t) = {_format_num(a0)} {b_sign} {_format_num(abs(b))}\,t$",
    ]
    for k in range(1, k_harmonics + 1):
        ak = coefs[2 * k]
        bk = coefs[2 * k + 1]
        ak_sign = "+" if ak >= 0 else "-"
        bk_sign = "+" if bk >= 0 else "-"
        equation_lines.append(
            rf"{ak_sign} {_format_num(abs(ak))}\cos(\frac{{{2*k}\pi t}}{{{int(period)}}}) "
            rf"{bk_sign} {_format_num(abs(bk))}\sin(\frac{{{2*k}\pi t}}{{{int(period)}}})"
        )
    equation_lines.append(rf"$R^2={r2:.4f}, K={k_harmonics}, P={int(period)}$")
    equation = "\n".join(equation_lines)
    return TimeSeriesModelResult(
        name="fourier_harmonic",
        display_name=f"Fourier (Regressão Harmônica, K={k_harmonics})",
        model={"coefs": coefs, "r2": r2, "k": k_harmonics, "period": period},
        fitted_values=pd.Series(fitted, index=series.index),
        forecast=pd.Series(predicted_future, index=future_dates),
        params={"coefs": coefs, "r2": r2, "k": k_harmonics},
        equation=equation,
        applicable=True,
    )


def backtest_timeseries_product(
    product_series: pd.Series,
    holdout_year: int = HOLDOUT_YEAR,
    horizon: int = 12,
) -> tuple[dict[str, TimeSeriesModelResult], dict[str, dict[str, Any]]]:
    """Train time series models on history prior to holdout year and evaluate on holdout."""
    series = _clean_series(product_series)
    train_mask = series.index.year < holdout_year
    holdout_mask = series.index.year == holdout_year
    train_data = series.loc[train_mask]
    holdout_data = series.loc[holdout_mask]
    actual_holdout = holdout_data.to_numpy(dtype=float)
    models: dict[str, TimeSeriesModelResult] = {
        "holt_winters_multiplicative": holt_winters_multiplicative(train_data, horizon=horizon),
        "sarima": sarima_forecast(train_data, horizon=horizon),
        "fourier_harmonic": fourier_regression(train_data, horizon=horizon, k_harmonics=2),
    }
    metrics_map: dict[str, dict[str, Any]] = {}
    for name, result in models.items():
        if not result.applicable or len(result.forecast) == 0:
            metrics_map[name] = {
                "mad": np.nan,
                "mse": np.nan,
                "rmse": np.nan,
                "mape": np.nan,
                "mpe": np.nan,
                "n_zeros": 0,
                "metric_note": result.note or "not_applicable",
            }
            continue
        pred = result.forecast.to_numpy(dtype=float)[: len(actual_holdout)]
        calculated = metrics(actual_holdout, pred)
        if result.note:
            calculated["metric_note"] = result.note
        metrics_map[name] = calculated
    return models, metrics_map


def evaluate_timeseries_dataframe(
    demand_df: pd.DataFrame,
    holdout_year: int = HOLDOUT_YEAR,
) -> tuple[pd.DataFrame, dict[str, dict[str, TimeSeriesModelResult]]]:
    """Evaluate time series methods across all products in DataFrame and build error metrics table."""
    rows: list[dict[str, Any]] = []
    models_by_product: dict[str, dict[str, TimeSeriesModelResult]] = {}
    products = demand_df["produto"].drop_duplicates().astype(str).tolist()
    for product in products:
        sub = demand_df.loc[demand_df["produto"].eq(product)].sort_values("data")
        series = sub.set_index("data")["unidades"].astype(float)
        results, errs = backtest_timeseries_product(series, holdout_year=holdout_year)
        models_by_product[product] = results
        product_rows = []
        for model_key, err in errs.items():
            entry = {
                "produto": product,
                "modelo": model_key,
                "mad": err.get("mad", np.nan),
                "mse": err.get("mse", np.nan),
                "rmse": err.get("rmse", np.nan),
                "mape": err.get("mape", np.nan),
                "mpe": err.get("mpe", np.nan),
                "n_zeros": err.get("n_zeros", 0),
                "metric_note": err.get("metric_note", ""),
                "vencedor": False,
            }
            product_rows.append(entry)
        # Choose winner by lowest MAPE among applicable
        valid_candidates = [
            row for row in product_rows if np.isfinite(row["mape"]) and row["mape"] > 0
        ]
        if valid_candidates:
            # Sort by MAPE, tie-break by MAD
            best = min(valid_candidates, key=lambda r: (round(r["mape"], 4), r["mad"]))
            best["vencedor"] = True
        rows.extend(product_rows)
    metrics_table = pd.DataFrame(rows)
    return metrics_table, models_by_product


def forecast_timeseries_future(
    demand_df: pd.DataFrame,
    horizon_years: int = 1,
    model_name: str | Mapping[str, str] = "holt_winters_multiplicative",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train the selected time series model(s) on full history and forecast future years.

    ``model_name`` is either a single model applied to every product, or a mapping of
    ``produto -> modelo`` so each product forecasts with its own winning method.
    """
    monthly_rows: list[dict[str, Any]] = []
    horizon_months = 12 * horizon_years
    products = demand_df["produto"].drop_duplicates().astype(str).tolist()
    for product in products:
        sub = demand_df.loc[demand_df["produto"].eq(product)].sort_values("data")
        series = sub.set_index("data")["unidades"].astype(float)
        selected_model = model_name.get(product, "holt_winters_multiplicative") if isinstance(
            model_name, Mapping
        ) else model_name
        if selected_model == "holt_winters_multiplicative":
            result = holt_winters_multiplicative(series, horizon=horizon_months)
        elif selected_model == "sarima":
            result = sarima_forecast(series, horizon=horizon_months)
        else:
            result = fourier_regression(series, horizon=horizon_months, k_harmonics=2)
        if not result.applicable:
            continue
        forecast_dates = pd.date_range(
            series.index[-1] + pd.DateOffset(months=1),
            periods=horizon_months,
            freq="MS",
        )
        forecast_vals = result.forecast.to_numpy(dtype=float)
        for date, val in zip(forecast_dates, forecast_vals, strict=False):
            monthly_rows.append(
                {
                    "produto": product,
                    "ano": date.year,
                    "mes": date.month,
                    "data": date.strftime("%Y-%m-%d"),
                    "unidades_previstas": float(val),
                    "modelo": selected_model,
                }
            )
    monthly_df = pd.DataFrame(monthly_rows)
    if not monthly_df.empty:
        annual_df = (
            monthly_df.groupby(["produto", "ano", "modelo"])["unidades_previstas"]
            .sum()
            .reset_index()
            .rename(columns={"unidades_previstas": "demanda_anual_prevista"})
        )
    else:
        annual_df = pd.DataFrame(
            columns=["produto", "ano", "modelo", "demanda_anual_prevista"]
        )
    return monthly_df, annual_df


_FITTERS: dict[str, Any] = {
    "holt_winters_multiplicative": holt_winters_multiplicative,
    "sarima": sarima_forecast,
    "fourier_harmonic": lambda s, horizon: fourier_regression(s, horizon=horizon, k_harmonics=2),
}


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


# ---------------------------------------------------------------------------
# Visualizations
# ---------------------------------------------------------------------------

def fig_timeseries_comparison(
    history: pd.Series | pd.DataFrame,
    results: dict[str, TimeSeriesModelResult],
    product: str,
    holdout_year: int = HOLDOUT_YEAR,
    forecast_horizon: int = 12,
) -> Figure:
    """Compare the 3 time series methods over the full T=0..47 range (Jan/2022-Dec/2025).

    Shows observed points, each method's 2024 holdout backtest, and a genuine 2025 forecast
    (each method refit on the complete history, since a real forecast never trains on future data).
    """
    apply_style()
    series = _clean_series(history)
    fig, ax = plt.subplots(figsize=(10, 6))
    t_all = month_index(series.index)
    # Observed points
    ax.scatter(t_all, series.values, color="#111111", label="Observado", zorder=5, s=28)
    # Highlight holdout zone
    holdout_mask = series.index.year == holdout_year
    holdout_dates = series.index[holdout_mask]
    t_holdout = t_all[holdout_mask]
    if len(t_holdout) > 0:
        ax.axvspan(
            t_holdout[0],
            t_holdout[-1],
            color="#dddddd",
            alpha=0.35,
            label="Holdout (2024)",
            zorder=1,
        )
    future_start = series.index[-1] + pd.DateOffset(months=1)
    future_dates = pd.date_range(future_start, periods=forecast_horizon, freq="MS")
    t_future = month_index(future_dates)
    ax.axvspan(
        t_future[0],
        t_future[-1],
        color="#cfe8f3",
        alpha=0.35,
        label=f"Previsão {future_dates[0].year}",
        zorder=1,
    )
    palette = {
        "holt_winters_multiplicative": ("#1b9e77", "-", "Holt-Winters Multiplicativo"),
        "sarima": ("#7570b3", "-.", "SARIMA(1,0,0)(1,0,0)₁₂"),
        "fourier_harmonic": ("#d95f02", "--", "Fourier (Harmônica, K=2)"),
    }
    for key, result in results.items():
        if not result.applicable or len(result.forecast) == 0:
            continue
        color, linestyle, display_label = palette.get(key, ("#333333", "-", result.display_name))
        pred_dates = holdout_dates if len(holdout_dates) == len(result.forecast) else result.forecast.index
        t_pred = month_index(pred_dates)
        # Compute MAPE for legend
        actual = series.loc[series.index.year == holdout_year].to_numpy(dtype=float)
        pred_vals = result.forecast.to_numpy(dtype=float)[: len(actual)]
        nonzero = actual != 0
        mape_val = (
            np.mean(np.abs((actual[nonzero] - pred_vals[nonzero]) / actual[nonzero])) * 100
            if nonzero.any()
            else 0.0
        )
        ax.plot(
            t_pred,
            pred_vals,
            color=color,
            linestyle=linestyle,
            linewidth=2.2,
            label=f"{display_label} (MAPE={mape_val:.1f}%)",
            zorder=4,
        )
        future_result = _FITTERS[key](series, forecast_horizon)
        if not future_result.applicable or len(future_result.forecast) == 0:
            continue
        bridged_t, bridged_vals = _bridge(
            t_pred,
            pred_vals,
            month_index(future_result.forecast.index),
            future_result.forecast.to_numpy(dtype=float),
        )
        ax.plot(
            bridged_t,
            bridged_vals,
            color=color,
            linestyle=linestyle,
            linewidth=2.2,
            alpha=0.6,
            zorder=4,
        )
    ax.set_title(f"Séries Temporais — Comparativo de Métodos — {product.replace('_', ' ').title()}")
    ax.set_xlabel(MONTH_AXIS_LABEL)
    ax.set_ylabel("Unidades")
    ax.legend(loc="upper left", framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    return fig


def fig_timeseries_backtest_single(
    history: pd.Series | pd.DataFrame,
    result: TimeSeriesModelResult,
    product: str,
    holdout_year: int = HOLDOUT_YEAR,
    forecast_horizon: int = 12,
) -> Figure:
    """Plot one method's 2024 holdout backtest plus a genuine 2025 forecast (T=0..47).

    The 2025 segment refits the same method on the complete history, since a real forecast
    never trains on future data.
    """
    apply_style()
    series = _clean_series(history)
    fig, ax = plt.subplots(figsize=(10, 6))
    t_all = month_index(series.index)
    ax.scatter(t_all, series.values, color="#111111", label="Observado", zorder=5, s=28)
    holdout_mask = series.index.year == holdout_year
    t_holdout = t_all[holdout_mask]
    if len(t_holdout) > 0:
        ax.axvspan(
            t_holdout[0],
            t_holdout[-1],
            color="#dddddd",
            alpha=0.35,
            label="Holdout (2024)",
            zorder=1,
        )
    future_start = series.index[-1] + pd.DateOffset(months=1)
    future_dates = pd.date_range(future_start, periods=forecast_horizon, freq="MS")
    t_future = month_index(future_dates)
    ax.axvspan(
        t_future[0],
        t_future[-1],
        color="#cfe8f3",
        alpha=0.35,
        label=f"Previsão {future_dates[0].year}",
        zorder=1,
    )
    train_t = np.array([])
    train_vals = np.array([])
    if result.applicable and len(result.fitted_values) > 0:
        fitted_in_train = result.fitted_values.loc[result.fitted_values.index.year < holdout_year]
        train_t = month_index(fitted_in_train.index)
        train_vals = fitted_in_train.to_numpy(dtype=float)
        ax.plot(
            train_t,
            train_vals,
            color="#1769aa",
            linestyle=":",
            alpha=0.75,
            label="Ajuste no treino (2022–2023)",
            zorder=3,
        )
    holdout_vals = np.array([])
    if result.applicable and len(result.forecast) > 0:
        actual = series.loc[series.index.year == holdout_year].to_numpy(dtype=float)
        holdout_vals = result.forecast.to_numpy(dtype=float)[: len(actual)]
        nonzero = actual != 0
        mape_val = (
            np.mean(np.abs((actual[nonzero] - holdout_vals[nonzero]) / actual[nonzero])) * 100
            if nonzero.any()
            else 0.0
        )
        mad_val = np.mean(np.abs(actual - holdout_vals))
        bridged_t, bridged_vals = _bridge(train_t, train_vals, t_holdout, holdout_vals)
        ax.plot(
            bridged_t,
            bridged_vals,
            color="#d95f02",
            linestyle="--",
            marker="o",
            linewidth=2.0,
            label=f"Previsão Holdout 2024 (MAPE={mape_val:.1f}%, MAD={mad_val:.1f})",
            zorder=4,
        )
        annotate_equation(ax, result.equation)
    fitter = _FITTERS.get(result.name)
    if fitter is not None:
        future_result = fitter(series, forecast_horizon)
        if future_result.applicable and len(future_result.forecast) > 0:
            prev_t = t_holdout if len(holdout_vals) > 0 else train_t
            prev_vals = holdout_vals if len(holdout_vals) > 0 else train_vals
            bridged_t, bridged_vals = _bridge(
                prev_t,
                prev_vals,
                month_index(future_result.forecast.index),
                future_result.forecast.to_numpy(dtype=float),
            )
            ax.plot(
                bridged_t,
                bridged_vals,
                color="#2c7fb8",
                linestyle="--",
                marker="o",
                linewidth=2.0,
                label=f"Previsão {future_dates[0].year} (ajuste com histórico completo)",
                zorder=4,
            )
    ax.set_title(
        f"Backtest {result.display_name} — {product.replace('_', ' ').title()}"
    )
    ax.set_xlabel(MONTH_AXIS_LABEL)
    ax.set_ylabel("Unidades")
    ax.legend(loc="upper left", framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    return fig


def fig_timeseries_metrics_bar(error_metrics: pd.DataFrame) -> Figure:
    """Bar chart comparing holdout MAPE and MAD across time series models for each product."""
    apply_style()
    fig, (ax_mape, ax_mad) = plt.subplots(1, 2, figsize=(14, 6))
    palette = {
        "holt_winters_multiplicative": "#1b9e77",
        "sarima": "#7570b3",
        "fourier_harmonic": "#d95f02",
    }
    model_labels = {
        "holt_winters_multiplicative": "Holt-Winters",
        "sarima": "SARIMA",
        "fourier_harmonic": "Fourier",
    }
    products = sorted(error_metrics["produto"].unique())
    models = ["holt_winters_multiplicative", "sarima", "fourier_harmonic"]
    x = np.arange(len(products))
    width = 0.25
    for idx, model_name in enumerate(models):
        sub = error_metrics.loc[error_metrics["modelo"].eq(model_name)]
        sub_dict = sub.set_index("produto")["mape"].to_dict()
        mad_dict = sub.set_index("produto")["mad"].to_dict()
        mape_vals = [sub_dict.get(p, np.nan) for p in products]
        mad_vals = [mad_dict.get(p, np.nan) for p in products]
        # Cap visual bars at 100% for readability if exploding
        mape_capped = [min(v, 100.0) if np.isfinite(v) else 0.0 for v in mape_vals]
        ax_mape.bar(
            x + (idx - 1) * width,
            mape_capped,
            width,
            label=model_labels.get(model_name, model_name),
            color=palette.get(model_name, "#333333"),
        )
        ax_mad.bar(
            x + (idx - 1) * width,
            mad_vals,
            width,
            label=model_labels.get(model_name, model_name),
            color=palette.get(model_name, "#333333"),
        )
    ax_mape.set_title("Comparação de MAPE (%) no Holdout 2024")
    ax_mape.set_xlabel("Produto")
    ax_mape.set_ylabel("MAPE (%)")
    ax_mape.set_xticks(x, [p.replace("_", " ").title() for p in products])
    ax_mape.legend()
    ax_mape.grid(True, alpha=0.3, axis="y")
    ax_mad.set_title("Comparação de MAD (unidades) no Holdout 2024")
    ax_mad.set_xlabel("Produto")
    ax_mad.set_ylabel("MAD (unidades)")
    ax_mad.set_xticks(x, [p.replace("_", " ").title() for p in products])
    ax_mad.legend()
    ax_mad.grid(True, alpha=0.3, axis="y")
    fig.suptitle("Desempenho dos Métodos de Séries Temporais no Holdout 2024", fontsize=14)
    return fig


def fig_timeseries_error_table(error_metrics: pd.DataFrame) -> Figure:
    """Render a clean error comparison table as a matplotlib figure."""
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.axis("off")
    cols = ["Produto", "Método", "MAD", "MSE", "RMSE", "MAPE (%)", "MPE (%)", "Vencedor"]
    display_names = {
        "holt_winters_multiplicative": "Holt-Winters Multiplicativo",
        "sarima": "SARIMA(1,0,0)(1,0,0)₁₂",
        "fourier_harmonic": "Fourier (Harmônica K=2)",
    }
    cell_data = []
    for _, row in error_metrics.iterrows():
        p_name = str(row["produto"]).replace("_", " ").title()
        m_name = display_names.get(str(row["modelo"]), str(row["modelo"]))
        mad_str = f"{float(row['mad']):.2f}" if np.isfinite(row["mad"]) else "n/d"
        mse_str = f"{float(row['mse']):.1f}" if np.isfinite(row["mse"]) else "n/d"
        rmse_str = f"{float(row['rmse']):.2f}" if np.isfinite(row["rmse"]) else "n/d"
        mape_str = f"{float(row['mape']):.2f}%" if np.isfinite(row["mape"]) else "n/d"
        mpe_str = f"{float(row['mpe']):.2f}%" if np.isfinite(row["mpe"]) else "n/d"
        venc_str = "Sim" if row.get("vencedor") else ""
        cell_data.append([p_name, m_name, mad_str, mse_str, rmse_str, mape_str, mpe_str, venc_str])
    table = ax.table(
        cellText=cell_data,
        colLabels=cols,
        colWidths=[0.18, 0.28, 0.08, 0.08, 0.08, 0.10, 0.10, 0.10],
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.4)
    # Highlight header
    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_facecolor("#2c3e50")
            cell.set_text_props(color="white", weight="bold")
        elif cell_data[r - 1][7] == "Sim":
            cell.set_facecolor("#e8f8f5")
    ax.set_title("Tabela Comparativa de Erros — Séries Temporais (Holdout 2024)", pad=20, weight="bold")
    return fig


def fig_timeseries_forecast_all(
    history_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    model_name: str = "Holt-Winters Multiplicativo",
) -> Figure:
    """Plot historical and future forecast (2025+) for all products using chosen method."""
    apply_style()
    fig, ax = plt.subplots(figsize=(10, 6))
    palette = {
        "suco_premium": "#1b9e77",
        "geleia_de_frutas": "#d95f02",
        "doce_de_frutas": "#7570b3",
    }
    products = history_df["produto"].drop_duplicates().tolist()
    for product in products:
        color = palette.get(product, "#333333")
        label_name = product.replace("_", " ").title()
        # Historical
        sub_h = history_df.loc[history_df["produto"].eq(product)].sort_values("data")
        t_h = month_index(pd.to_datetime(sub_h["data"]))
        vals_h = sub_h["unidades"].to_numpy(dtype=float)
        ax.plot(
            t_h, vals_h, color=color, marker="o", markersize=4, label=f"{label_name} (Histórico)", linewidth=1.8
        )
        # Future forecast
        sub_f = forecast_df.loc[forecast_df["produto"].eq(product)].sort_values("data")
        if not sub_f.empty:
            t_f = month_index(pd.to_datetime(sub_f["data"]))
            vals_f = sub_f["unidades_previstas"].to_numpy(dtype=float)
            bridged_t, bridged_vals = _bridge(t_h, vals_h, t_f, vals_f)
            ax.plot(
                bridged_t,
                bridged_vals,
                color=color,
                linestyle="--",
                marker="o",
                markersize=4,
                label=f"{label_name} (Previsão {model_name})",
                linewidth=1.8,
            )
    ax.set_title(f"Previsão de Demanda Futura — Séries Temporais ({model_name})")
    ax.set_xlabel(MONTH_AXIS_LABEL)
    ax.set_ylabel("Unidades")
    ax.legend(loc="upper left", framealpha=0.9, fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    return fig


def generate_and_save_timeseries_artifacts(
    demand_df: pd.DataFrame,
    outdir: Path,
    formats: tuple[str, ...] = FIGURE_FORMATS,
    holdout_year: int = HOLDOUT_YEAR,
    horizon_years: int = 1,
) -> dict[str, Any]:
    """Execute complete time series analysis, generate plots, and persist artifacts."""
    fig_dir = outdir / "figures"
    table_dir = outdir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)
    saved_files: list[Path] = []

    # 1. Evaluation & metrics
    metrics_df, models_by_product = evaluate_timeseries_dataframe(
        demand_df, holdout_year=holdout_year
    )
    metrics_path = table_dir / "timeseries_error_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False)
    saved_files.append(metrics_path)

    # 2. Future forecast (per product's own winning time series method)
    best_ts_model = {
        str(product): str(sub.loc[sub["vencedor"], "modelo"].iloc[0])
        for product, sub in metrics_df.groupby("produto")
        if sub["vencedor"].any()
    }
    monthly_fc, annual_fc = forecast_timeseries_future(
        demand_df, horizon_years=horizon_years, model_name=best_ts_model
    )
    monthly_fc_path = table_dir / "timeseries_forecast_monthly.csv"
    annual_fc_path = table_dir / "timeseries_forecast_annual.csv"
    monthly_fc.to_csv(monthly_fc_path, index=False)
    annual_fc.to_csv(annual_fc_path, index=False)
    saved_files.extend([monthly_fc_path, annual_fc_path])

    # 3. Figures: Comparison plots per product
    for product, results in models_by_product.items():
        sub = demand_df.loc[demand_df["produto"].eq(product)].sort_values("data")
        series = sub.set_index("data")["unidades"].astype(float)
        # Multi-model comparison figure
        fig_comp = fig_timeseries_comparison(
            series, results, product, holdout_year=holdout_year, forecast_horizon=12 * horizon_years
        )
        saved_files.extend(
            save_figure(fig_comp, f"series_temporais/comparativo_{product}", fig_dir, formats)
        )
        plt.close(fig_comp)
        folder_map = {
            "holt_winters_multiplicative": "holt_winters_multiplicativo",
            "sarima": "sarima",
            "fourier_harmonic": "fourier_harmonica",
        }
        for model_key, result in results.items():
            fig_single = fig_timeseries_backtest_single(
                series, result, product, holdout_year=holdout_year, forecast_horizon=12 * horizon_years
            )
            folder_name = folder_map.get(model_key, model_key)
            saved_files.extend(
                save_figure(fig_single, f"{folder_name}/backtest_{product}", fig_dir, formats)
            )
            plt.close(fig_single)
    # 4. Error comparison bar chart & table figure
    fig_bar = fig_timeseries_metrics_bar(metrics_df)
    saved_files.extend(save_figure(fig_bar, "series_temporais/metricas_mape", fig_dir, formats))
    plt.close(fig_bar)

    fig_tbl = fig_timeseries_error_table(metrics_df)
    saved_files.extend(save_figure(fig_tbl, "series_temporais/tabela_erros", fig_dir, formats))
    plt.close(fig_tbl)

    # 5. Future forecast figure
    fig_fc = fig_timeseries_forecast_all(demand_df, monthly_fc)
    saved_files.extend(save_figure(fig_fc, "series_temporais/previsao_todos", fig_dir, formats))
    plt.close(fig_fc)

    return {
        "metrics": metrics_df,
        "models": models_by_product,
        "monthly_forecast": monthly_fc,
        "annual_forecast": annual_fc,
        "saved_files": saved_files,
    }
