"""Logistic classification of high-demand seasonal regimes."""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import SEED
from .features import MONTH_FEATURES

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClassificationResult:
    metrics: dict[str, float]
    confusion: np.ndarray
    skipped: bool = False
    reason: str | None = None


def build_regime_labels(df: pd.DataFrame, month_clusters: pd.Series) -> pd.Series:
    """Mark months in the ``alta`` seasonal cluster as one."""
    if "mes" not in df.columns:
        raise ValueError("coluna ausente: mes")
    labels = df["mes"].map(month_clusters).eq("alta").astype(int)
    labels.index = df.index
    labels.name = "alta"
    return labels


CLASSIFICATION_FEATURES = [*MONTH_FEATURES, "trend", "lag_12"]


def select_classification_features(features: pd.DataFrame) -> pd.DataFrame:
    """Select only features allowed for regime classification."""
    missing = [column for column in CLASSIFICATION_FEATURES if column not in features.columns]
    if missing:
        raise ValueError(f"colunas ausentes para classificação: {missing}")
    return features.loc[:, CLASSIFICATION_FEATURES].copy()


def fit_regime_classifier(
    X_train: pd.DataFrame | np.ndarray,
    y_train: pd.Series | np.ndarray,
    seed: int = SEED,
) -> Pipeline | None:
    """Fit a scaled deterministic classifier, skipping invalid fits."""
    target = np.asarray(y_train)
    if len(np.unique(target)) < 2:
        LOGGER.warning("classificação ignorada: single_class no treino")
        return None
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(random_state=seed, max_iter=1000)),
        ]
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(X_train, target)
    convergence_warnings = [
        warning for warning in caught if issubclass(warning.category, ConvergenceWarning)
    ]
    if convergence_warnings:
        LOGGER.warning("classificação ignorada: non_converged")
        return None
    return model


def _skipped(reason: str) -> ClassificationResult:
    LOGGER.warning("classificação ignorada: %s", reason)
    return ClassificationResult(
        {
            "accuracy": float("nan"),
            "precision": float("nan"),
            "recall": float("nan"),
            "f1": float("nan"),
        },
        np.zeros((2, 2), dtype=int),
        True,
        reason,
    )


def evaluate_classifier(
    model: Pipeline | None,
    X_test: pd.DataFrame | np.ndarray,
    y_test: pd.Series | np.ndarray,
) -> ClassificationResult:
    """Evaluate with a fixed ``[[vn, fp], [fn, vp]]`` confusion layout."""
    target = np.asarray(y_test)
    if model is None:
        return _skipped("single_class")
    if len(np.unique(target)) < 2:
        return _skipped("single_class")
    predicted = model.predict(X_test)
    matrix = confusion_matrix(target, predicted, labels=[0, 1])
    metrics = {
        "accuracy": float(accuracy_score(target, predicted)),
        "precision": float(precision_score(target, predicted, zero_division=0)),
        "recall": float(recall_score(target, predicted, zero_division=0)),
        "f1": float(f1_score(target, predicted, zero_division=0)),
    }
    return ClassificationResult(metrics, matrix)
