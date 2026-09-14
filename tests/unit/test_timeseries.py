"""Unit tests for time series models and figures (Holt-Winters, SARIMA, Fourier)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bebibem.io_data import load_demand
from bebibem.timeseries import (
    backtest_timeseries_product,
    evaluate_timeseries_dataframe,
    forecast_timeseries_future,
    fourier_regression,
    generate_and_save_timeseries_artifacts,
    holt_winters_multiplicative,
    sarima_forecast,
)


@pytest.fixture
def synthetic_seasonal_series() -> pd.Series:
    """36 months of synthetic seasonal demand with trend."""
    dates = pd.date_range("2022-01-01", periods=36, freq="MS")
    t = np.arange(36, dtype=float)
    # Seasonal wave with period 12, amplitude 20, positive base of 50
    seasonality = 20.0 * np.sin(2 * np.pi * t / 12.0)
    trend = 1.5 * t
    values = 50.0 + trend + seasonality
    return pd.Series(values, index=dates, name="unidades")


def test_holt_winters_multiplicative_fits_and_forecasts(synthetic_seasonal_series: pd.Series) -> None:
    train = synthetic_seasonal_series.iloc[:24]
    result = holt_winters_multiplicative(train, horizon=12)
    assert result.applicable is True
    assert len(result.forecast) == 12
    assert len(result.fitted_values) == 24
    assert "alpha" in result.params
    assert "beta" in result.params
    assert "gamma" in result.params
    assert r"\hat{y}_{t+h}" in result.equation
    assert (result.forecast > 0).all()


def test_holt_winters_handles_insufficient_or_non_positive() -> None:
    short_series = pd.Series([10.0, 20.0, 30.0], index=pd.date_range("2022-01-01", periods=3, freq="MS"))
    res_short = holt_winters_multiplicative(short_series, horizon=12)
    assert res_short.applicable is False
    assert res_short.note == "dados_insuficientes"

    dates = pd.date_range("2022-01-01", periods=24, freq="MS")
    zero_vals = np.ones(24)
    zero_vals[5] = 0.0
    zero_series = pd.Series(zero_vals, index=dates)
    res_zero = holt_winters_multiplicative(zero_series, horizon=12)
    assert res_zero.applicable is False
    assert res_zero.note == "valores_nao_positivos"


def test_fourier_regression_recovers_cyclic_signal(synthetic_seasonal_series: pd.Series) -> None:
    train = synthetic_seasonal_series.iloc[:24]
    result = fourier_regression(train, horizon=12, period=12.0, k_harmonics=2)
    assert result.applicable is True
    assert len(result.forecast) == 12
    assert len(result.fitted_values) == 24
    assert result.params["r2"] > 0.90
    assert "cos" in result.equation
    assert "sin" in result.equation


def test_sarima_forecast(synthetic_seasonal_series: pd.Series) -> None:
    train = synthetic_seasonal_series.iloc[:24]
    result = sarima_forecast(train, horizon=12)
    assert result.applicable is True
    assert len(result.forecast) == 12
    assert "SARIMA" in result.display_name


def test_backtest_timeseries_product(synthetic_seasonal_series: pd.Series) -> None:
    models, errs = backtest_timeseries_product(synthetic_seasonal_series, holdout_year=2024, horizon=12)
    assert set(models.keys()) == {"holt_winters_multiplicative", "sarima", "fourier_harmonic"}
    assert set(errs.keys()) == {"holt_winters_multiplicative", "sarima", "fourier_harmonic"}
    hw_err = errs["holt_winters_multiplicative"]
    assert "mape" in hw_err
    assert "mad" in hw_err
    assert hw_err["mape"] < 25.0  # Synthetic data should have low error


def test_evaluate_timeseries_dataframe() -> None:
    df = load_demand(Path("data/raw/demanda_loja_propria.csv"))
    metrics_table, _ = evaluate_timeseries_dataframe(df, holdout_year=2024)
    assert len(metrics_table) == 9  # 3 products * 3 models
    assert set(metrics_table["produto"].unique()) == {"suco_premium", "geleia_de_frutas", "doce_de_frutas"}
    winners = metrics_table.loc[metrics_table["vencedor"]]
    assert len(winners) == 3
    # Holt-Winters should win for Suco Premium and Doce de frutas
    hw_winners = winners.loc[winners["modelo"].eq("holt_winters_multiplicative")]
    assert len(hw_winners) >= 2


def test_forecast_timeseries_future() -> None:
    df = load_demand(Path("data/raw/demanda_loja_propria.csv"))
    monthly, annual = forecast_timeseries_future(df, horizon_years=1, model_name="holt_winters_multiplicative")
    assert len(monthly) == 36  # 3 products * 12 months
    assert len(annual) == 3  # 3 products * 1 year
    assert (annual["demanda_anual_prevista"] > 0).all()


def test_timeseries_figures_and_artifacts(tmp_path: Path) -> None:
    df = load_demand(Path("data/raw/demanda_loja_propria.csv"))
    res = generate_and_save_timeseries_artifacts(df, outdir=tmp_path, formats=("png",), horizon_years=1)
    assert len(res["saved_files"]) > 0
    assert (tmp_path / "tables" / "timeseries_error_metrics.csv").is_file()
    assert (tmp_path / "tables" / "timeseries_forecast_annual.csv").is_file()
    assert (tmp_path / "figures" / "png" / "series_temporais" / "comparativo_suco_premium.png").is_file()
    assert (tmp_path / "figures" / "png" / "series_temporais" / "metricas_mape.png").is_file()
    assert (tmp_path / "figures" / "png" / "series_temporais" / "tabela_erros.png").is_file()
    assert (tmp_path / "figures" / "png" / "series_temporais" / "previsao_todos.png").is_file()
    assert (tmp_path / "figures" / "png" / "holt_winters_multiplicativo" / "backtest_suco_premium.png").is_file()
    assert (tmp_path / "figures" / "png" / "sarima" / "backtest_suco_premium.png").is_file()
    assert (tmp_path / "figures" / "png" / "fourier_harmonica" / "backtest_suco_premium.png").is_file()
