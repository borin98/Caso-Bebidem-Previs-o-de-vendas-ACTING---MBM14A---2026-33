import numpy as np
import pandas as pd

from bebibem.models import (
    build_estimators,
    cross_validate_temporal,
    metrics,
    metrics_table,
    recursive_backtest,
    select_best,
    select_overall_best,
)


def test_build_estimators_has_fixed_specs_and_seed():
    estimators = build_estimators()
    assert set(estimators) == {"ridge", "random_forest", "gradient_boosting"}
    assert estimators["ridge"].alpha == 1.0
    assert estimators["random_forest"].n_estimators == 300
    assert estimators["random_forest"].min_samples_leaf == 2
    assert estimators["random_forest"].random_state == 42
    assert estimators["gradient_boosting"].random_state == 42


def test_metrics_constant_overprediction_has_expected_errors_and_bias():
    result = metrics(np.array([10, 10, 10], dtype=float), np.array([12, 12, 12], dtype=float))
    assert result["mad"] == 2
    assert result["mse"] == 4
    assert result["rmse"] == 2
    assert result["mpe"] < 0


def test_metrics_ignores_zero_actuals_and_reports_smape():
    result = metrics(np.array([0, 10], dtype=float), np.array([3, 12], dtype=float))
    assert result["n_zeros"] == 1
    assert result["mape"] == 20
    assert result["mpe"] == -20
    assert "smape" in result
    assert result["metric_note"] == "zeros_ignored"


def test_cross_validate_temporal_returns_three_folds_and_five_metrics():
    X = pd.DataFrame({"x": np.arange(12, dtype=float)})
    y = 2 * X["x"] + 1
    result = cross_validate_temporal(build_estimators()["ridge"], X, y)
    assert len(result) == 3
    assert {"mad", "mse", "rmse", "mape", "mpe"}.issubset(result.columns)
    assert result["fold"].tolist() == [1, 2, 3]


def test_recursive_backtest_appends_predictions_without_real_future_values():
    class LastValueEstimator:
        def predict(self, rows):
            return np.array([rows.iloc[0]["lag_1"] + 1])

    history = pd.Series(
        np.arange(24, dtype=float), index=pd.date_range("2022-01", periods=24, freq="MS")
    )

    def row_fn(values, target):
        return pd.DataFrame({"lag_1": [values.iloc[-1]]})

    result = recursive_backtest(LastValueEstimator(), history, row_fn, 3)
    assert result.tolist() == [24, 25, 26]
    assert result.index[0] == pd.Timestamp("2024-01-01")


def test_metrics_table_marks_one_winner_per_product_with_mape_tie_rule():
    rows = [
        {"produto": "a", "modelo": "ridge", "mape": 2.0, "mad": 3.0},
        {"produto": "a", "modelo": "random_forest", "mape": 2.4, "mad": 2.0},
        {"produto": "a", "modelo": "gradient_boosting", "mape": 4.0, "mad": 1.0},
        {"produto": "b", "modelo": "ridge", "mape": 1.0, "mad": 2.0},
    ]
    result = metrics_table(rows)
    assert result.loc[result["produto"] == "a", "vencedor"].tolist() == [False, True, False]
    assert result.loc[result["produto"] == "b", "vencedor"].tolist() == [True]
    assert select_best(result[result["produto"] == "a"]) == "random_forest"


def test_select_overall_best_picks_cross_group_winner_by_lowest_mape():
    ml_metrics = pd.DataFrame(
        [
            {"produto": "doce", "modelo": "ridge", "mape": 34.5, "mad": 14.0},
            {"produto": "geleia", "modelo": "random_forest", "mape": 18.7, "mad": 2.9},
        ]
    )
    ts_metrics = pd.DataFrame(
        [
            {"produto": "doce", "modelo": "holt_winters_multiplicative", "mape": 15.5, "mad": 6.1},
            {"produto": "geleia", "modelo": "sarima", "mape": 35.4, "mad": 5.0},
        ]
    )
    winners = select_overall_best(ml_metrics, ts_metrics)
    assert winners == {"doce": "holt_winters_multiplicative", "geleia": "random_forest"}


def test_select_overall_best_ignores_products_with_no_applicable_model():
    ml_metrics = pd.DataFrame([{"produto": "a", "modelo": "ridge", "mape": np.nan, "mad": np.nan}])
    ts_metrics = pd.DataFrame(columns=["produto", "modelo", "mape", "mad"])
    assert select_overall_best(ml_metrics, ts_metrics) == {}
    assert select_overall_best() == {}
