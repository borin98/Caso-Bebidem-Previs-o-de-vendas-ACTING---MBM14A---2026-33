import numpy as np
import pandas as pd
import pytest

from bebibem.interpolation import (
    fill_gaps_linear,
    linear_interpolation,
    polynomial_equation_label,
    polynomial_fit,
    select_degree,
    validate_degree,
)
from bebibem.io_data import InputError


def test_linear_interpolation_is_dense_and_matches_observations():
    x = np.array([0.0, 1.0, 2.0])
    y = np.array([1.0, 3.0, 5.0])

    dense_x, dense_y = linear_interpolation(x, y, points_per_step=10)

    assert len(dense_x) == 21
    assert np.max(np.abs(np.interp(x, dense_x, dense_y) - y)) <= 1e-9
    assert dense_y[10] == pytest.approx(3.0)


def test_fill_gaps_linear_uses_analytic_neighbor_value():
    series = pd.Series([10.0, np.nan, 30.0], index=pd.date_range("2022-01", periods=3, freq="MS"))

    filled = fill_gaps_linear(series)

    assert filled.iloc[1] == pytest.approx(20.0)
    assert filled.index.equals(series.index)


def test_select_degree_returns_candidate_rmse_table_and_smallest_tie_degree():
    x = np.arange(36, dtype=float)
    y = 2 * x + 1

    selection = select_degree(x, y, candidates=(1, 2, 3, 4, 5))

    assert selection.degree == 1
    assert selection.candidates["degree"].tolist() == [1, 2, 3, 4, 5]
    assert selection.candidates["rmse"].notna().all()
    assert selection.candidates.loc[selection.candidates["degree"] == 1, "rmse"].iloc[
        0
    ] == pytest.approx(0)


def test_select_degree_uses_smallest_degree_for_exact_rmse_tie(monkeypatch):
    from bebibem import interpolation as interpolation_module

    monkeypatch.setattr(
        interpolation_module,
        "_fit_coefficients",
        lambda x, y, degree: np.zeros(degree + 1),
    )
    selection = select_degree(np.arange(36, dtype=float), np.zeros(36), candidates=(1, 2, 3))

    assert selection.degree == 1
    assert selection.candidates["rmse"].tolist() == [0.0, 0.0, 0.0]


def test_select_degree_honors_calendar_holdout_year(monkeypatch):
    from bebibem import interpolation as interpolation_module

    monkeypatch.setattr(
        interpolation_module,
        "_fit_coefficients",
        lambda x, y, degree: np.zeros(degree + 1),
    )
    dates = pd.date_range("2022-01", periods=36, freq="MS")
    values = np.concatenate([np.zeros(12), np.ones(12), np.full(12, 10.0)])

    selection = select_degree(dates, values, candidates=(1,), holdout_year=2023)

    assert selection.candidates["rmse"].iloc[0] == pytest.approx(1.0)


def test_select_degree_avoids_high_degree_for_quadratic_noisy_series():
    rng = np.random.default_rng(42)
    x = np.arange(36, dtype=float)
    y = 0.02 * x**2 - 0.5 * x + 10 + rng.normal(0, 0.2, len(x))

    selection = select_degree(x, y)

    assert selection.degree <= 3
    assert set(selection.candidates["degree"]) == {1, 2, 3, 4, 5}


def test_polynomial_fit_returns_canonical_coefficients_and_r2_values():
    x = np.arange(10, dtype=float)
    y = 2 * x + 1

    result = polynomial_fit(x, y, degree=1)

    assert result.coefs[0] == pytest.approx(1.0, abs=1e-9)
    assert result.coefs[1] == pytest.approx(2.0, abs=1e-9)
    assert result.r2 == pytest.approx(1.0)
    assert result.r2_adj == pytest.approx(1.0)


@pytest.mark.parametrize("degree", [0, 6])
def test_validate_degree_rejects_values_outside_one_to_five(degree):
    with pytest.raises(InputError, match=r"1.*5"):
        validate_degree(degree)


def test_polynomial_equation_label_has_deterministic_portuguese_decimal_format():
    label = polynomial_equation_label([2.0, 1.0], 1, 1.0, 1.0)

    assert label == "$y = 2,000 x + 1,000$\n grau = 1 | R² = 1,0000 | R²_aj = 1,0000"


def test_polynomial_equation_label_uses_scientific_notation_and_line_breaks():
    label = polynomial_equation_label([1.2e4, -2.0e-4, 3.0, 4.0, -5.0], 4, 0.5, 0.4)

    assert "10^{4}" in label
    assert "e-" not in label
    assert label.count("\n") >= 2
