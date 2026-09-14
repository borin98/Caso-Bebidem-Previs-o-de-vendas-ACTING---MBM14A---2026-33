import logging
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge

from bebibem.forecast import (
    fit_final,
    forecast_recursive,
    forecast_tables,
    reconstruct_winning_series,
    validate_horizon_years,
)
from bebibem.io_data import InputError
from bebibem.pipeline import _forecast_classical
from bebibem.regression import linear_regression_normal_equation


def _history():
    dates = pd.date_range("2022-01", periods=36, freq="MS")
    return pd.Series(np.arange(100, 136, dtype=float), index=dates, name="suco_premium")


def _clusters():
    return pd.Series({month: ("alta" if month in (1, 2) else "baixa") for month in range(1, 13)})


def test_validate_horizon_years_accepts_one_to_three_and_rejects_other_values():
    for value in (1, 2, 3):
        validate_horizon_years(value)
    with pytest.raises(InputError, match="1, 2 ou 3"):
        validate_horizon_years(4)


def test_forecast_recursive_returns_future_only_months_and_recursive_lag():
    class PreviousValueEstimator:
        def predict(self, rows):
            return np.array([rows.iloc[0]["lag_1"] + 1])

    result = forecast_recursive(PreviousValueEstimator(), _history(), _clusters(), horizon_years=1)
    assert len(result) == 12
    assert result.index[0] == pd.Timestamp("2025-01-01")
    assert result.index[-1] == pd.Timestamp("2025-12-01")
    assert result.iloc[0] == 136
    assert result.iloc[-1] == 147
    assert result.index.min().year > 2024


def test_forecast_warns_when_lag12_switches_to_forecasts(caplog):
    class ConstantEstimator:
        def predict(self, rows):
            return np.array([10.0])

    with caplog.at_level(logging.WARNING):
        result = forecast_recursive(ConstantEstimator(), _history(), _clusters(), horizon_years=2)
    assert len(result) == 24
    assert "lag_12 passa a acumular previsões" in caplog.text


def test_negative_forecast_is_truncated_with_product_and_month_warning(caplog):
    class NegativeEstimator:
        def predict(self, rows):
            return np.array([-2.0])

    with caplog.at_level(logging.WARNING):
        result = forecast_recursive(NegativeEstimator(), _history(), _clusters())
    assert result.iloc[0] == 0
    assert "suco_premium" in caplog.text
    assert "2025-01" in caplog.text


def test_classical_forecast_truncates_negative_values_with_warnings(caplog):
    history = pd.Series(
        np.arange(35, -1, -1, dtype=float),
        index=pd.date_range("2022-01", periods=36, freq="MS"),
        name="suco_premium",
    )
    fit = linear_regression_normal_equation(np.arange(36, dtype=float), history.to_numpy())
    warnings: list[str] = []

    with caplog.at_level(logging.WARNING):
        result = _forecast_classical(fit, history, 1, warnings)

    assert (result.to_numpy() >= 0).all()
    assert len(warnings) == 12
    assert "suco_premium" in caplog.text
    assert "2025-01" in caplog.text


def test_fit_final_and_forecast_tables_have_monthly_and_integer_annual_outputs():
    dates = pd.date_range("2022-01", periods=24, freq="MS")
    X = pd.DataFrame({"x": np.arange(24)}, index=dates)
    y = pd.Series(np.arange(24, dtype=float), index=dates)
    fitted = fit_final(Ridge(), X, y)
    assert fitted.predict(X.iloc[:1]).shape == (1,)
    forecasts = {
        "suco_premium": pd.Series([1.2, 2.6], index=pd.date_range("2025-01", periods=2, freq="MS"))
    }
    holdout = pd.DataFrame(
        [{"produto": "suco_premium", "modelo": "ridge", "mape": 5.0, "mad": 2.0}]
    )
    monthly, annual = forecast_tables(forecasts, {"suco_premium": "ridge"}, holdout)
    assert monthly.columns.tolist() == [
        "produto",
        "ano",
        "mes",
        "unidades_previstas",
        "modelo",
        "mape_holdout",
    ]
    assert monthly["ano"].tolist() == [2025, 2025]
    assert annual["unidades_previstas_total"].tolist() == [4]
    assert annual["mad_holdout"].tolist() == [2.0]


def test_reconstruct_winning_series_uses_fitted_forecast_for_timeseries_winner():
    fitted_values = pd.Series([10.0, 11.0], index=pd.date_range("2022-01", periods=2, freq="MS"))
    forecast = pd.Series([12.0], index=pd.date_range("2022-02", periods=1, freq="MS"))
    ts_result = SimpleNamespace(fitted_values=fitted_values, forecast=forecast)
    series = reconstruct_winning_series(
        "suco_premium",
        "holt_winters_multiplicative",
        ts_models={"holt_winters_multiplicative": ts_result},
        analysis_frame=pd.DataFrame(),
        month_cluster_labels=_clusters(),
        ml_estimators={},
    )
    assert series.index.min() == fitted_values.index.min()
    assert series.iloc[-1] == 12.0


def test_reconstruct_winning_series_refits_ml_model_for_full_observed_span():
    dates = pd.date_range("2022-01", periods=36, freq="MS")
    frame = pd.DataFrame(
        {
            "produto": "suco_premium",
            "data": dates,
            "ano": dates.year,
            "mes": dates.month,
            "unidades": np.arange(100, 136, dtype=float),
        }
    )
    series = reconstruct_winning_series(
        "suco_premium",
        "ridge",
        ts_models={},
        analysis_frame=frame,
        month_cluster_labels=_clusters(),
        ml_estimators={"ridge": Ridge()},
    )
    assert series.index.min() == dates[0]
    assert series.index.max() == dates[-1]
    assert len(series) == 36
    assert series.notna().all()


def test_reconstruct_winning_series_backcasts_first_year_with_seasonal_shape():
    dates = pd.date_range("2022-01", periods=36, freq="MS")
    seasonal = 100 + 50 * np.cos(2 * np.pi * (dates.month - 1) / 12)
    frame = pd.DataFrame(
        {
            "produto": "suco_premium",
            "data": dates,
            "ano": dates.year,
            "mes": dates.month,
            "unidades": seasonal,
        }
    )
    series = reconstruct_winning_series(
        "suco_premium",
        "ridge",
        ts_models={},
        analysis_frame=frame,
        month_cluster_labels=_clusters(),
        ml_estimators={"ridge": Ridge(alpha=0.01)},
    )
    first_year = series.loc[series.index.year == 2022]
    assert len(first_year) == 12
    assert first_year.notna().all()
    peak_month = first_year.loc["2022-01-01"]
    trough_month = first_year.loc["2022-07-01"]
    assert peak_month > trough_month
