"""Classical linear and exponential regressions for demand baselines."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

LOGGER = logging.getLogger(__name__)


def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    total = float(np.sum((y_true - y_true.mean()) ** 2))
    if total == 0:
        return 1.0 if np.allclose(y_true, y_pred) else 0.0
    return float(1 - np.sum((y_true - y_pred) ** 2) / total)


def _format(value: float) -> str:
    return f"{float(value):.4g}"


def _linear_equation(coefs: np.ndarray) -> str:
    intercept, slope = coefs[:2]
    sign = "+" if slope >= 0 else "-"
    return f"$y = {_format(intercept)} {sign} {_format(abs(slope))} x$"


def _exponential_equation(a: float, b: float) -> str:
    sign = "+" if b >= 0 else "-"
    return f"$y = {_format(a)} e^{{{sign}{_format(abs(b))}x}}$"


def _as_x(x: np.ndarray | list[float]) -> np.ndarray:
    return np.asarray(x, dtype=float).reshape(-1)


def _design_matrix(x: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(x)), x])


@dataclass
class RegressionFit:
    name: str
    coefs: np.ndarray
    r2: float
    equation: str
    _predictor: Callable[[np.ndarray], np.ndarray] = field(repr=False)
    applicable: bool = True
    note: str | None = None
    r2_log: float | None = None
    r2_original: float | None = None

    def predict(self, x: np.ndarray | list[float]) -> np.ndarray:
        return self._predictor(_as_x(x))


def linear_regression_normal_equation(X: np.ndarray, y: np.ndarray) -> RegressionFit:
    """Fit a straight line by solving the normal equation."""
    target = _as_x(y)
    matrix = np.asarray(X, dtype=float)
    if matrix.ndim == 1:
        matrix = _design_matrix(matrix)
    coefs = np.linalg.solve(matrix.T @ matrix, matrix.T @ target)
    predicted = matrix @ coefs
    equation = _linear_equation(coefs)
    return RegressionFit(
        "linear_normal_equation",
        coefs,
        _r2(target, predicted),
        equation,
        lambda values: _design_matrix(values) @ coefs,
    )


def linear_regression_sums(x: np.ndarray, y: np.ndarray) -> RegressionFit:
    """Fit a straight line with the explicit sum formulas."""
    values_x = _as_x(x)
    target = _as_x(y)
    n = len(values_x)
    denominator = n * np.sum(values_x**2) - np.sum(values_x) ** 2
    if denominator == 0:
        raise ValueError("x precisa conter valores distintos")
    slope = (n * np.sum(values_x * target) - np.sum(values_x) * np.sum(target)) / denominator
    intercept = (np.sum(target) - slope * np.sum(values_x)) / n
    coefs = np.array([intercept, slope], dtype=float)
    predicted = _design_matrix(values_x) @ coefs
    return RegressionFit(
        "linear_sums",
        coefs,
        _r2(target, predicted),
        _linear_equation(coefs),
        lambda values: _design_matrix(values) @ coefs,
    )


def _not_applicable(name: str, note: str) -> RegressionFit:
    LOGGER.warning("regressão %s ignorada: %s", name, note)
    return RegressionFit(
        name,
        np.array([np.nan, np.nan]),
        float("nan"),
        "",
        lambda values: np.full(len(values), np.nan),
        applicable=False,
        note=note,
    )


def _loglinear_coefficients(x: np.ndarray, log_target: np.ndarray) -> np.ndarray | None:
    n = len(x)
    denominator = n * np.sum(x**2) - np.sum(x) ** 2
    if denominator == 0:
        return None
    slope = (n * np.sum(x * log_target) - np.sum(x) * np.sum(log_target)) / denominator
    intercept = (np.sum(log_target) - slope * np.sum(x)) / n
    return np.array([intercept, slope], dtype=float)


def _normal_equation_coefficients(x: np.ndarray, log_target: np.ndarray) -> np.ndarray:
    matrix = _design_matrix(x)
    return np.linalg.solve(matrix.T @ matrix, matrix.T @ log_target)


def _fit_exponential(
    x: np.ndarray,
    y: np.ndarray,
    name: str,
    coefficients_builder: Callable[[np.ndarray, np.ndarray], np.ndarray | None],
) -> RegressionFit:
    if len(x) < 2:
        return _not_applicable(name, "insufficient_data")
    if np.any(y <= 0):
        return _not_applicable(name, "not_applicable")
    log_target = np.log(y)
    coefs_log = coefficients_builder(x, log_target)
    if coefs_log is None:
        return _not_applicable(name, "insufficient_data")
    matrix = _design_matrix(x)
    a = float(np.exp(coefs_log[0]))
    b = float(coefs_log[1])
    predicted = a * np.exp(b * x)
    return RegressionFit(
        name,
        np.array([a, b]),
        _r2(log_target, matrix @ coefs_log),
        _exponential_equation(a, b),
        lambda values: a * np.exp(b * values),
        r2_log=_r2(log_target, matrix @ coefs_log),
        r2_original=_r2(y, predicted),
    )


def exponential_regression_loglinear(x: np.ndarray, y: np.ndarray) -> RegressionFit:
    """Fit ``y = a exp(bx)`` by least squares on log(y)."""
    return _fit_exponential(_as_x(x), _as_x(y), "exponential_loglinear", _loglinear_coefficients)


def exponential_regression_normal_equation(x: np.ndarray, y: np.ndarray) -> RegressionFit:
    """Fit ``y = a exp(bx)`` through a matrix normal equation on log(y)."""
    return _fit_exponential(
        _as_x(x),
        _as_x(y),
        "exponential_normal_equation",
        _normal_equation_coefficients,
    )


class _RegressionEstimator:
    def __init__(self, fit: RegressionFit):
        self.fit_result = fit

    def fit(self, X: np.ndarray, y: np.ndarray) -> _RegressionEstimator:
        x = _as_x(X)
        builders = {
            "linear_normal_equation": lambda: linear_regression_normal_equation(x, y),
            "linear_sums": lambda: linear_regression_sums(x, y),
            "exponential_loglinear": lambda: exponential_regression_loglinear(x, y),
            "exponential_normal_equation": lambda: exponential_regression_normal_equation(x, y),
        }
        builder = builders.get(self.fit_result.name)
        if builder is not None:
            self.fit_result = builder()
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.fit_result.predict(_as_x(X))


def as_estimator(fit: RegressionFit) -> _RegressionEstimator:
    """Adapt a classical fit to the estimator ``fit``/``predict`` protocol."""
    return _RegressionEstimator(fit)
