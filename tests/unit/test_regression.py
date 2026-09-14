import logging

import numpy as np

from bebibem.regression import (
    as_estimator,
    exponential_regression_loglinear,
    exponential_regression_normal_equation,
    linear_regression_normal_equation,
    linear_regression_sums,
)


def test_linear_normal_equation_returns_exact_line_and_r2():
    x = np.arange(6, dtype=float)
    fit = linear_regression_normal_equation(np.column_stack([np.ones(6), x]), 3 * x + 5)
    assert np.allclose(fit.coefs, [5, 3], atol=1e-9)
    assert fit.r2 == 1.0
    assert fit.equation == "$y = 5 + 3 x$"


def test_linear_sums_matches_normal_equation():
    x = np.arange(6, dtype=float)
    target = 3 * x + 5
    normal = linear_regression_normal_equation(x, target)
    sums = linear_regression_sums(x, target)
    assert np.allclose(sums.coefs, normal.coefs, atol=1e-9)


def test_exponential_formulations_match_expected_coefficients():
    x = np.arange(8, dtype=float)
    target = 2 * np.exp(0.3 * x)
    loglinear = exponential_regression_loglinear(x, target)
    normal = exponential_regression_normal_equation(x, target)
    assert loglinear.applicable is True
    assert np.allclose(loglinear.coefs, [2, 0.3], atol=1e-6)
    assert np.allclose(normal.coefs, loglinear.coefs, atol=1e-9)
    assert loglinear.r2_log == 1.0
    assert loglinear.r2_original == 1.0
    assert loglinear.equation.startswith("$y = 2 e^{+0.3x}$")


def test_as_estimator_refits_and_predicts():
    x = np.arange(5, dtype=float)
    estimator = as_estimator(linear_regression_sums(x, 3 * x + 5))
    estimator.fit(x, 3 * x + 5)
    assert np.allclose(estimator.predict([5]), [20])


def test_exponential_nonpositive_values_are_not_applicable(caplog):
    with caplog.at_level(logging.WARNING):
        fit = exponential_regression_loglinear(np.arange(3), [1, 0, 2])
    assert fit.applicable is False
    assert fit.note == "not_applicable"
    assert "not_applicable" in caplog.text
    assert np.isnan(fit.predict([1])[0])
