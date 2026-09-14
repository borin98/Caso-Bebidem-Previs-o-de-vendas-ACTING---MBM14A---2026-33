"""Model comparison, temporal validation, metrics, and recursive backtests."""

from __future__ import annotations

import logging
from collections.abc import Callable

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.model_selection import TimeSeriesSplit

from .config import MODEL_SPECS, SEED

LOGGER = logging.getLogger(__name__)


def build_estimators(seed: int = SEED) -> dict[str, BaseEstimator]:
    """Build the fixed estimator set with deterministic random states."""
    estimators = {}
    for name, factory in MODEL_SPECS.items():
        estimator = factory()
        if hasattr(estimator, "random_state"):
            estimator.set_params(random_state=seed)
        estimators[name] = estimator
    return estimators


def metrics(
    y_true: np.ndarray | pd.Series, y_pred: np.ndarray | pd.Series
) -> dict[str, float | int | str]:
    """Return error metrics, excluding zero actuals from percentage metrics."""
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    if actual.shape != predicted.shape:
        raise ValueError("y_true e y_pred devem ter o mesmo formato")
    error = actual - predicted
    nonzero = actual != 0
    zero_count = int(np.count_nonzero(~nonzero))
    percentages = error[nonzero] / actual[nonzero] * 100
    result: dict[str, float | int | str] = {
        "mad": float(np.mean(np.abs(error))),
        "mse": float(np.mean(error**2)),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "mape": float(np.mean(np.abs(percentages))) if len(percentages) else float("nan"),
        "mpe": float(np.mean(percentages)) if len(percentages) else float("nan"),
        "n_zeros": zero_count,
        "metric_note": "zeros_ignored" if zero_count else "",
    }
    if zero_count:
        denominator = np.abs(actual) + np.abs(predicted)
        valid_smape = denominator != 0
        result["smape"] = (
            float(np.mean(2 * np.abs(error[valid_smape]) / denominator[valid_smape]) * 100)
            if valid_smape.any()
            else 0.0
        )
    return result


def cross_validate_temporal(
    estimator: BaseEstimator,
    X: pd.DataFrame | np.ndarray,
    y: pd.Series | np.ndarray,
    n_splits: int = 3,
) -> pd.DataFrame:
    """Evaluate an estimator with expanding temporal folds."""
    splitter = TimeSeriesSplit(n_splits=n_splits)
    rows = []
    values_y = np.asarray(y)
    for fold, (train_index, test_index) in enumerate(splitter.split(X), start=1):
        candidate = clone(estimator)
        candidate.fit(np.asarray(X)[train_index], values_y[train_index])
        prediction = candidate.predict(np.asarray(X)[test_index])
        row = {"fold": fold, **metrics(values_y[test_index], prediction)}
        rows.append(row)
    return pd.DataFrame(rows)


def _feature_row(
    features_fn: Callable, history: pd.Series, target_date: pd.Timestamp
) -> pd.DataFrame:
    try:
        return features_fn(history, target_date)
    except TypeError as error:
        if "positional" not in str(error) and "argument" not in str(error):
            raise
        return features_fn(history)


def recursive_backtest(
    estimator: BaseEstimator,
    history: pd.Series,
    features_fn: Callable,
    horizon: int,
) -> pd.Series:
    """Predict forward recursively, appending predictions but never actual values."""
    if horizon < 1:
        raise ValueError("horizon deve ser positivo")
    values = history.astype(float).copy()
    dates = pd.to_datetime(values.index)
    if len(dates) == 0:
        raise ValueError("history não pode ser vazio")
    target_date = dates[-1] + pd.DateOffset(months=1)
    predictions = []
    for _ in range(horizon):
        row = _feature_row(features_fn, values, target_date)
        if len(row) == 0:
            raise ValueError("features_fn não produziu uma linha de features")
        prediction = float(estimator.predict(row)[0])
        predictions.append(prediction)
        values.loc[target_date] = prediction
        target_date += pd.DateOffset(months=1)
    return pd.Series(
        predictions,
        index=pd.date_range(dates[-1] + pd.DateOffset(months=1), periods=horizon, freq="MS"),
        name="previsao",
    )


def select_best(metrics_by_model: pd.DataFrame) -> str:
    """Select lowest MAPE, using MAD for ties within 0.5 percentage points."""
    required = {"modelo", "mape", "mad"}
    missing = required.difference(metrics_by_model.columns)
    if missing:
        raise ValueError(f"colunas ausentes: {sorted(missing)}")
    valid = metrics_by_model.dropna(subset=["mape"]).copy()
    if len(valid) == 0:
        raise ValueError("nenhum modelo aplicável")
    minimum = float(valid["mape"].min())
    tied = valid[valid["mape"] <= minimum + 0.5]
    winner = tied.sort_values(["mad", "mape", "modelo"], kind="stable").iloc[0]
    return str(winner["modelo"])


def select_overall_best(*metrics_tables: pd.DataFrame) -> dict[str, str]:
    """Select the best model per product across several metrics tables (e.g. ML/classical and time series)."""
    frames = [table for table in metrics_tables if table is not None and len(table) > 0]
    if not frames:
        return {}
    combined = pd.concat(frames, ignore_index=True)
    winners: dict[str, str] = {}
    for product, group in combined.groupby("produto", sort=False, dropna=False):
        applicable = group.dropna(subset=["mape"])
        if len(applicable) == 0:
            continue
        winners[str(product)] = select_best(applicable)
    return winners


def metrics_table(results: pd.DataFrame | list[dict]) -> pd.DataFrame:
    """Normalize model results and flag the winner per product."""
    table = pd.DataFrame(results).copy()
    if "produto" not in table.columns:
        table["produto"] = ""
    table["vencedor"] = False
    for _, group in table.groupby("produto", sort=False, dropna=False):
        applicable = group[group["mape"].notna()]
        if len(applicable) == 0:
            continue
        winner = select_best(applicable)
        table.loc[group.index, "vencedor"] = table.loc[group.index, "modelo"].eq(winner)
    return table
