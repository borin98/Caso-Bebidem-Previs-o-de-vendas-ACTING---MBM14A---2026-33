"""Deterministic seasonal and product-year clustering."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from .config import SEED

LOGGER = logging.getLogger(__name__)

_MONTH_LABELS = {
    2: "media_alta",
    3: "media",
    4: "media_baixa",
}


@dataclass(frozen=True)
class ClusterResult:
    labels: pd.Series
    k: int
    silhouette: float
    scores: dict[int, float]
    skipped: bool = False
    reason: str | None = None


def seasonal_index_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Return monthly mean demand divided by each product's annual mean."""
    required = {"produto", "mes", "unidades"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"colunas ausentes: {sorted(missing)}")

    monthly = df.groupby(["mes", "produto"], sort=True)["unidades"].mean().unstack("produto")
    annual = df.groupby("produto", sort=True)["unidades"].mean()
    matrix = monthly.divide(annual.replace(0, np.nan), axis="columns")
    return matrix.reindex(range(1, 13))


def _valid_k_values(n_samples: int, k: int | None, k_grid: Sequence[int]) -> list[int]:
    if k is not None:
        if k < 2 or k >= n_samples:
            raise ValueError("k deve estar entre 2 e o número de amostras menos 1")
        return [k]
    values = sorted({candidate for candidate in k_grid if 2 <= candidate < n_samples})
    if len(values) == 0:
        raise ValueError("não há valores de k válidos para o número de amostras")
    return values


def _choose_k(
    values: np.ndarray, k: int | None, k_grid: Sequence[int], seed: int
) -> tuple[int, float, dict[int, float], np.ndarray]:
    valid_ks = _valid_k_values(len(values), k, k_grid)
    scores: dict[int, float] = {}
    models: dict[int, tuple[float, np.ndarray, KMeans]] = {}
    for candidate in valid_ks:
        model = KMeans(n_clusters=candidate, random_state=seed, n_init=10)
        labels = model.fit_predict(values)
        score = float(silhouette_score(values, labels))
        scores[candidate] = score
        models[candidate] = (score, labels, model)
    selected = min(valid_ks, key=lambda candidate: (-scores[candidate], candidate))
    score, labels, model = models[selected]
    return selected, score, scores, labels


def _regime_names(k: int) -> list[str]:
    names = {
        2: ["alta", "baixa"],
        3: ["alta", "media", "baixa"],
        4: ["alta", "media_alta", "media_baixa", "baixa"],
    }
    if k not in names:
        raise ValueError(f"k não suportado para rótulos: {k}")
    return names[k]


def _stable_regime_labels(values: np.ndarray, raw_labels: np.ndarray, k: int) -> dict[int, str]:
    means = {cluster: float(values[raw_labels == cluster].mean()) for cluster in range(k)}
    ordered = sorted(means, key=lambda cluster: (-means[cluster], cluster))
    return dict(zip(ordered, _regime_names(k), strict=True))


def cluster_months(
    matrix: pd.DataFrame,
    k: int | None = None,
    k_grid: Sequence[int] = (2, 3, 4),
    seed: int = SEED,
) -> ClusterResult:
    """Cluster monthly seasonal-index vectors with stable regime names."""
    values = matrix.to_numpy(dtype=float)
    if matrix.shape[1] == 0:
        LOGGER.warning("clusterização mensal ignorada: amostras insuficientes")
        return ClusterResult(
            pd.Series(dtype="object"), 0, float("nan"), {}, True, "insufficient_data"
        )
    valid_rows = np.isfinite(values).all(axis=1)
    if valid_rows.sum() < 3:
        LOGGER.warning("clusterização mensal ignorada: amostras insuficientes")
        return ClusterResult(
            pd.Series(dtype="object"), 0, float("nan"), {}, True, "insufficient_data"
        )
    valid_values = values[valid_rows]
    if len(np.unique(valid_values, axis=0)) < 2:
        LOGGER.warning("clusterização mensal ignorada: vetores sem separação")
        return ClusterResult(pd.Series(dtype="object"), 0, float("nan"), {}, True, "single_cluster")

    selected, score, scores, raw_labels = _choose_k(valid_values, k, k_grid, seed)
    regime_map = _stable_regime_labels(valid_values, raw_labels, selected)
    labels = pd.Series(
        index=matrix.index[valid_rows],
        data=[regime_map[label] for label in raw_labels],
        name="cluster",
    )
    return ClusterResult(labels, selected, score, scores)


def cluster_series(
    df: pd.DataFrame,
    k: int | None = None,
    k_grid: Sequence[int] = (2, 3, 4),
    seed: int = SEED,
) -> ClusterResult:
    """Cluster product-year seasonal profiles after row-wise z-score normalization."""
    required = {"produto", "ano", "mes", "unidades"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"colunas ausentes: {sorted(missing)}")
    profiles = df.pivot_table(
        index=["produto", "ano"], columns="mes", values="unidades", aggfunc="mean"
    )
    profiles = profiles.reindex(columns=range(1, 13)).dropna(axis=0, how="any")
    if len(profiles) < 3:
        LOGGER.warning("clusterização de séries ignorada: amostras insuficientes")
        return ClusterResult(
            pd.Series(dtype="object"), 0, float("nan"), {}, True, "insufficient_data"
        )

    values = profiles.to_numpy(dtype=float)
    means = values.mean(axis=1, keepdims=True)
    stds = values.std(axis=1, keepdims=True)
    normalized = np.divide(values - means, stds, out=np.zeros_like(values), where=stds != 0)
    if len(np.unique(normalized, axis=0)) < 2:
        LOGGER.warning("clusterização de séries ignorada: vetores sem separação")
        return ClusterResult(pd.Series(dtype="object"), 0, float("nan"), {}, True, "single_cluster")

    selected, score, scores, raw_labels = _choose_k(normalized, k, k_grid, seed)
    labels = pd.Series(raw_labels, index=profiles.index, name="cluster")
    return ClusterResult(labels, selected, score, scores)
