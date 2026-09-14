"""Feature construction for lagged monthly demand models."""

from __future__ import annotations

import numpy as np
import pandas as pd

MONTH_FEATURES = [f"mes_{month}" for month in range(2, 13)]


def _cluster_values(month_clusters: pd.Series) -> list[str]:
    values = month_clusters.dropna().astype(str).unique().tolist()
    return sorted(values)


def _cluster_columns(month_clusters: pd.Series) -> list[str]:
    return [f"cluster_{value}" for value in _cluster_values(month_clusters)]


def _month_cluster(month_clusters: pd.Series, month: int) -> str | None:
    if month not in month_clusters.index:
        return None
    return str(month_clusters.loc[month])


def _empty_feature_frame(month_clusters: pd.Series, insufficient_data: bool) -> pd.DataFrame:
    columns = ["lag_1", "lag_12", *MONTH_FEATURES, "trend", *_cluster_columns(month_clusters)]
    result = pd.DataFrame(columns=columns, dtype=float)
    result.attrs["insufficient_data"] = insufficient_data
    return result


def _month_dummies(month: int) -> dict[str, float]:
    return {
        feature: float(month == int(feature.removeprefix("mes_"))) for feature in MONTH_FEATURES
    }


def _cluster_dummies(label: str | None, month_clusters: pd.Series) -> dict[str, float]:
    return {
        column: float(label == column.removeprefix("cluster_"))
        for column in _cluster_columns(month_clusters)
    }


def build_features(df_product: pd.DataFrame, month_clusters: pd.Series) -> pd.DataFrame:
    """Build lag, month, trend, and seasonal-cluster features without missing rows."""
    required = {"mes", "data", "unidades"}
    missing = required.difference(df_product.columns)
    if missing:
        raise ValueError(f"colunas ausentes: {sorted(missing)}")
    ordered = df_product.sort_values("data").copy()
    ordered["data"] = pd.to_datetime(ordered["data"])
    ordered = ordered.set_index("data")
    ordered["lag_1"] = ordered["unidades"].shift(1)
    ordered["lag_12"] = ordered["unidades"].shift(12)
    ordered["trend"] = np.arange(len(ordered), dtype=float)
    month_data = pd.DataFrame(index=ordered.index)
    for feature in _month_dummies(1):
        month_data[feature] = [
            float(month == int(feature.removeprefix("mes_"))) for month in ordered["mes"]
        ]
    cluster_data = pd.DataFrame(index=ordered.index)
    labels = ordered["mes"].map(lambda month: _month_cluster(month_clusters, int(month)))
    for column in _cluster_columns(month_clusters):
        cluster_data[column] = (labels == column.removeprefix("cluster_")).astype(float)
    columns = ["lag_1", "lag_12", *MONTH_FEATURES, "trend", *_cluster_columns(month_clusters)]
    features = pd.concat([ordered[["lag_1", "lag_12", "trend"]], month_data, cluster_data], axis=1)
    features = features[columns].join(ordered[["unidades"]])
    features = features.dropna(subset=["lag_1", "lag_12", "unidades"])
    features = features.drop(columns=["unidades"])
    features.attrs["insufficient_data"] = len(ordered) < 24
    return features


def _year_mask(index: pd.Index, year: int) -> np.ndarray:
    dates = pd.to_datetime(index)
    return dates.year == year


def split_train_holdout(
    X: pd.DataFrame,
    y: pd.Series,
    holdout_year: int = 2024,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """Split by calendar year, keeping the holdout year out of training."""
    if len(X) != len(y):
        raise ValueError("X e y devem ter o mesmo tamanho")
    holdout_mask = _year_mask(X.index, holdout_year)
    train_mask = ~holdout_mask
    return X.loc[train_mask], y.loc[train_mask], X.loc[holdout_mask], y.loc[holdout_mask]


def backcast_row(
    target_date: pd.Timestamp | str,
    month_clusters: pd.Series,
    lag_1: float,
    lag_12: float,
    trend: float,
) -> pd.DataFrame:
    """Construct one feature row from explicit lag values, no lookup into observed history.

    Used for months whose true ``lag_1``/``lag_12`` predate the series (the first observed
    year), where the caller supplies a proxy instead of a real prior observation.
    """
    target = pd.Timestamp(target_date)
    month = target.month
    row = {"lag_1": float(lag_1), "lag_12": float(lag_12), "trend": float(trend)}
    row.update(_month_dummies(month))
    row.update(_cluster_dummies(_month_cluster(month_clusters, month), month_clusters))
    columns = ["lag_1", "lag_12", *MONTH_FEATURES, "trend", *_cluster_columns(month_clusters)]
    result = pd.DataFrame([row], index=[target], columns=columns)
    result.attrs["insufficient_data"] = False
    return result


def next_row(
    history: pd.Series,
    target_date: pd.Timestamp | str,
    month_clusters: pd.Series,
) -> pd.DataFrame:
    """Construct one recursive future feature row from observed/predicted history."""
    dates = pd.to_datetime(history.index)
    values = pd.Series(history.to_numpy(dtype=float), index=dates).sort_index()
    target = pd.Timestamp(target_date)
    if len(values) < 13:
        return _empty_feature_frame(month_clusters, insufficient_data=True)
    lag_12_date = target - pd.DateOffset(months=12)
    if lag_12_date not in values.index:
        return _empty_feature_frame(month_clusters, insufficient_data=True)
    return backcast_row(
        target,
        month_clusters,
        lag_1=float(values.iloc[-1]),
        lag_12=float(values.loc[lag_12_date]),
        trend=float(len(values)),
    )
