"""Future-only recursive demand forecasts and answer tables."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from functools import partial
from typing import Any

import pandas as pd
from sklearn.base import BaseEstimator

from .config import HOLDOUT_YEAR
from .features import backcast_row, build_features, next_row, split_train_holdout
from .io_data import InputError
from .models import recursive_backtest

LOGGER = logging.getLogger(__name__)


def fit_final(estimator: BaseEstimator, X_full: pd.DataFrame, y_full: pd.Series) -> BaseEstimator:
    """Fit the selected estimator on the complete available feature history."""
    estimator.fit(X_full, y_full)
    return estimator


def reconstruct_winning_series(
    product: str,
    winning_model: str,
    *,
    ts_models: Mapping[str, Any],
    analysis_frame: pd.DataFrame,
    month_cluster_labels: pd.Series,
    ml_estimators: Mapping[str, BaseEstimator],
    holdout_year: int = HOLDOUT_YEAR,
) -> pd.Series:
    """Reconstruct the winning model's prediction for every observed month (train + holdout).

    Time series methods already carry this split (fitted train + holdout forecast, see
    ``bebibem.timeseries.TimeSeriesModelResult`` values in ``ts_models``). Classical ML methods
    are refit on the same pre-``holdout_year`` training window used for their holdout metrics,
    giving in-sample fit before ``holdout_year`` and an out-of-sample recursive forecast for it.
    """
    if winning_model in ts_models:
        ts_result = ts_models[winning_model]
        return pd.concat([ts_result.fitted_values, ts_result.forecast]).sort_index()
    product_frame = analysis_frame.loc[analysis_frame["produto"].eq(product)].sort_values("data")
    history = product_frame.set_index("data")["unidades"]
    product_features = build_features(product_frame, month_cluster_labels)
    target = history.reindex(product_features.index)
    train_x, train_y, _, _ = split_train_holdout(product_features, target, holdout_year)
    history_train = history.loc[history.index.year < holdout_year]
    fitted = fit_final(ml_estimators[winning_model], train_x, train_y)
    in_sample = pd.Series(fitted.predict(train_x), index=train_x.index)
    backcast = _backcast_first_year(
        fitted, history, month_cluster_labels, train_x.columns, holdout_year
    )
    in_sample = pd.concat([backcast, in_sample]).sort_index()
    holdout_pred = recursive_backtest(
        fitted, history_train, partial(next_row, month_clusters=month_cluster_labels), 12
    )
    return pd.concat([in_sample, holdout_pred]).sort_index()


def _seasonal_naive_proxy(history: pd.Series, month: int, before_year: int) -> float:
    """Average observed value for ``month`` in years strictly before ``before_year``, excluding
    the series' own first year (which has no earlier reference)."""
    first_year = int(history.index.year.min())
    same_month = history[
        (history.index.month == month)
        & (history.index.year > first_year)
        & (history.index.year < before_year)
    ]
    if same_month.empty:
        same_month = history[history.index.month == month]
    return float(same_month.mean())


def _backcast_first_year(
    fitted: BaseEstimator,
    history: pd.Series,
    month_cluster_labels: pd.Series,
    feature_columns: pd.Index,
    holdout_year: int,
) -> pd.Series:
    """Predict the calendar year ``build_features`` drops for lacking a real ``lag_12``.

    The series' first twelve months never reach ``in_sample`` fit because ``lag_1``/``lag_12``
    need a real prior observation that predates the series (no month -12 or, for January, no
    month -1 either). This backfills that year with the same fitted estimator, substituting the
    missing lag terms with a seasonal-naive proxy (same calendar month's average from the
    training years that do have one), so the "melhor modelo" figure shows one continuous
    predicted curve across the whole observed history instead of skipping the first year.
    """
    first_year = int(history.index.year.min())
    rows = []
    for date in history.index[history.index.year == first_year]:
        prior = date - pd.DateOffset(months=1)
        lag_1 = (
            float(history.loc[prior])
            if prior in history.index
            else _seasonal_naive_proxy(history, prior.month, holdout_year)
        )
        lag_12 = _seasonal_naive_proxy(history, date.month, holdout_year)
        trend = float(history.index.get_loc(date))
        rows.append(backcast_row(date, month_cluster_labels, lag_1, lag_12, trend))
    features = pd.concat(rows)[feature_columns]
    return pd.Series(fitted.predict(features), index=features.index)


def validate_horizon_years(value: int) -> None:
    if value not in {1, 2, 3}:
        raise InputError("horizon_years deve ser 1, 2 ou 3")


def forecast_recursive(
    estimator: BaseEstimator,
    history: pd.Series,
    month_clusters: pd.Series,
    horizon_years: int = 1,
    start: str = "2025-01",
) -> pd.Series:
    """Forecast only future months, recursively updating lagged history."""
    validate_horizon_years(horizon_years)
    values = history.astype(float).copy()
    values.index = pd.to_datetime(values.index)
    values = values.sort_index()
    first = pd.Timestamp(start).replace(day=1)
    horizon = horizon_years * 12
    dates = pd.date_range(first, periods=horizon, freq="MS")
    product = str(history.name or "produto_desconhecido")
    predictions: list[float] = []
    for step, target_date in enumerate(dates):
        if step == 12:
            LOGGER.warning(
                "lag_12 passa a acumular previsões a partir de %s para %s",
                target_date.strftime("%Y-%m"),
                product,
            )
        row = next_row(values, target_date, month_clusters)
        if row.empty:
            raise ValueError("histórico insuficiente para montar features futuras")
        predicted = float(estimator.predict(row)[0])
        if predicted < 0:
            LOGGER.warning(
                "previsão negativa truncada para %s em %s", product, target_date.strftime("%Y-%m")
            )
            predicted = 0.0
        predictions.append(predicted)
        values.loc[target_date] = predicted
    return pd.Series(predictions, index=dates, name=history.name)


def _forecast_frame(forecasts: Mapping[str, pd.Series] | pd.DataFrame) -> pd.DataFrame:
    if isinstance(forecasts, pd.DataFrame):
        table = forecasts.copy()
        if "data" in table.columns:
            table["data"] = pd.to_datetime(table["data"])
            return table
        if isinstance(table.index, pd.DatetimeIndex):
            table = table.reset_index(names="data")
            return table
        raise ValueError("forecasts DataFrame precisa de coluna data")
    rows = []
    for product, values in forecasts.items():
        series = values.copy()
        series.index = pd.to_datetime(series.index)
        for date, prediction in series.items():
            rows.append({"produto": product, "data": date, "unidades_previstas": prediction})
    return pd.DataFrame(rows)


def _metric_lookup(holdout_metrics: pd.DataFrame, product: str, model: str, field: str) -> float:
    if holdout_metrics is None or len(holdout_metrics) == 0:
        return float("nan")
    mask = pd.Series(True, index=holdout_metrics.index)
    if "produto" in holdout_metrics.columns:
        mask &= holdout_metrics["produto"].eq(product)
    if "modelo" in holdout_metrics.columns:
        mask &= holdout_metrics["modelo"].eq(model)
    selected = holdout_metrics.loc[mask]
    if len(selected) == 0 or field not in selected.columns:
        return float("nan")
    return float(selected.iloc[0][field])


def forecast_tables(
    forecasts: Mapping[str, pd.Series] | pd.DataFrame,
    best_models: Mapping[str, str] | pd.Series,
    holdout_metrics: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return monthly and integer annual forecast tables with holdout metrics."""
    table = _forecast_frame(forecasts)
    if len(table) == 0:
        columns = ["produto", "ano", "mes", "unidades_previstas", "modelo", "mape_holdout"]
        return pd.DataFrame(columns=columns), pd.DataFrame(
            columns=[
                "produto",
                "ano",
                "unidades_previstas_total",
                "modelo",
                "mape_holdout",
                "mad_holdout",
            ]
        )
    if "produto" not in table.columns:
        raise ValueError("forecasts precisa identificar produto")
    if "unidades_previstas" not in table.columns:
        raise ValueError("forecasts precisa conter unidades_previstas")
    table["ano"] = table["data"].dt.year.astype(int)
    table["mes"] = table["data"].dt.month.astype(int)
    table["modelo"] = table["produto"].map(best_models)
    table["mape_holdout"] = [
        _metric_lookup(holdout_metrics, product, model, "mape")
        for product, model in zip(table["produto"], table["modelo"], strict=True)
    ]
    monthly = table[
        ["produto", "ano", "mes", "unidades_previstas", "modelo", "mape_holdout"]
    ].copy()
    annual = (
        monthly.groupby(["produto", "ano", "modelo", "mape_holdout"], as_index=False, dropna=False)[
            "unidades_previstas"
        ]
        .sum()
        .rename(columns={"unidades_previstas": "unidades_previstas_total"})
    )
    annual["unidades_previstas_total"] = annual["unidades_previstas_total"].round().astype(int)
    annual["mad_holdout"] = [
        _metric_lookup(holdout_metrics, product, model, "mad")
        for product, model in zip(annual["produto"], annual["modelo"], strict=True)
    ]
    annual = annual[
        ["produto", "ano", "unidades_previstas_total", "modelo", "mape_holdout", "mad_holdout"]
    ]
    return monthly, annual
