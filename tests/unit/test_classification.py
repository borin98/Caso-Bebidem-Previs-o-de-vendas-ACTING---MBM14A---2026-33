import logging

import numpy as np
import pandas as pd

from bebibem.classification import (
    CLASSIFICATION_FEATURES,
    build_regime_labels,
    evaluate_classifier,
    fit_regime_classifier,
    select_classification_features,
)


def test_build_regime_labels_marks_only_alta_months():
    frame = pd.DataFrame({"mes": [1, 2, 3, 4]})
    clusters = pd.Series({1: "alta", 2: "baixa", 3: "alta", 4: "media"})
    result = build_regime_labels(frame, clusters)
    assert result.tolist() == [1, 0, 1, 0]


def test_separable_classifier_has_perfect_metrics_and_confusion_matrix():
    train_x = np.array([[-3.0], [-2.0], [2.0], [3.0]])
    train_y = np.array([0, 0, 1, 1])
    test_x = np.array([[-4.0], [4.0]])
    test_y = np.array([0, 1])
    model = fit_regime_classifier(train_x, train_y)
    result = evaluate_classifier(model, test_x, test_y)
    assert result.skipped is False
    assert result.metrics == {"accuracy": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0}
    assert result.confusion.tolist() == [[1, 0], [0, 1]]


def test_classification_features_exclude_target_and_lag1():
    columns = ["lag_1", *CLASSIFICATION_FEATURES, "cluster_alta"]
    features = pd.DataFrame([[1, *range(len(CLASSIFICATION_FEATURES)), 1]], columns=columns)

    selected = select_classification_features(features)

    assert selected.columns.tolist() == CLASSIFICATION_FEATURES
    assert "cluster_alta" not in selected.columns
    assert "lag_1" not in selected.columns


def test_single_class_train_skips_without_exception(caplog):
    with caplog.at_level(logging.WARNING):
        model = fit_regime_classifier(np.array([[1], [2]]), np.array([1, 1]))
        result = evaluate_classifier(model, np.array([[3], [4]]), np.array([1, 1]))
    assert model is None
    assert result.skipped is True
    assert result.reason == "single_class"
    assert "single_class" in caplog.text


def test_single_class_test_skips_without_exception(caplog):
    model = fit_regime_classifier(np.array([[-1], [1]]), np.array([0, 1]))
    with caplog.at_level(logging.WARNING):
        result = evaluate_classifier(model, np.array([[2], [3]]), np.array([1, 1]))
    assert result.skipped is True
    assert result.reason == "single_class"
    assert "single_class" in caplog.text
