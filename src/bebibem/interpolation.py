"""Linear and polynomial interpolation utilities."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.polynomial import Polynomial

from .io_data import InputError


@dataclass(frozen=True)
class DegreeSelection:
    """Candidate validation errors and selected polynomial degree."""

    degree: int
    candidates: pd.DataFrame


@dataclass(frozen=True)
class PolyFitResult:
    """Polynomial fit with canonical ascending coefficients."""

    coefs: np.ndarray
    degree: int
    degree_source: str
    r2: float
    r2_adj: float
    rmse_holdout: float
    candidates: pd.DataFrame

    @property
    def coefs_desc(self) -> np.ndarray:
        """Return coefficients in equation order, highest power first."""
        return self.coefs[::-1]

    def evaluate(self, x: Sequence[float] | np.ndarray) -> np.ndarray:
        return np.polynomial.polynomial.polyval(np.asarray(x, dtype=float), self.coefs)


def validate_degree(degree: int) -> None:
    if degree < 1 or degree > 5:
        raise InputError(f"grau inválido: {degree}; intervalo válido: 1 a 5")


def _as_numeric_x(x: Sequence[object] | np.ndarray) -> np.ndarray:
    values = np.asarray(x)
    if np.issubdtype(values.dtype, np.datetime64):
        timestamps = pd.to_datetime(values)
        return ((timestamps - timestamps[0]) / pd.Timedelta(days=30.4375)).to_numpy(dtype=float)
    if pd.api.types.is_datetime64_any_dtype(values):
        timestamps = pd.to_datetime(values)
        return ((timestamps - timestamps[0]) / pd.Timedelta(days=30.4375)).to_numpy(dtype=float)
    return values.astype(float)


def linear_interpolation(
    x: np.ndarray,
    y: np.ndarray,
    points_per_step: int = 10,
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate piecewise linear interpolation on a dense monthly grid."""
    if points_per_step < 1:
        raise InputError(f"pontos por intervalo inválidos: {points_per_step}")
    x_values = np.asarray(x, dtype=float)
    y_values = np.asarray(y, dtype=float)
    if len(x_values) < 2 or len(y_values) != len(x_values):
        raise InputError("interpolação linear exige ao menos dois pontos pareados")
    if np.isnan(y_values).any():
        valid = ~np.isnan(y_values)
        x_values = x_values[valid]
        y_values = y_values[valid]
    if len(x_values) < 2:
        raise InputError("interpolação linear exige dois valores observados")
    span = x_values[-1] - x_values[0]
    if span <= 0:
        raise InputError("interpolação linear exige x crescente")
    point_count = round(span * points_per_step) + 1
    dense_x = np.linspace(x_values[0], x_values[-1], point_count)
    return dense_x, np.interp(dense_x, x_values, y_values)


def fill_gaps_linear(series: pd.Series) -> pd.Series:
    """Fill NaN observations with ``numpy.interp`` while preserving the index."""
    values = series.astype(float).to_numpy()
    missing = np.isnan(values)
    if np.count_nonzero(missing) == 0:
        return series.astype(float).copy()
    observed = np.flatnonzero(~missing)
    if len(observed) == 0:
        raise InputError("não é possível interpolar série sem observações")
    filled = np.interp(np.arange(len(values)), observed, values[observed])
    return pd.Series(filled, index=series.index, name=series.name)


def _fit_coefficients(x: np.ndarray, y: np.ndarray, degree: int) -> np.ndarray:
    if len(x) <= degree:
        raise InputError(f"observações insuficientes para grau {degree}")
    fitted = Polynomial.fit(x, y, deg=degree)
    coefficients = fitted.convert().coef.astype(float)
    return np.pad(coefficients, (0, degree + 1 - len(coefficients)))


def _holdout_indices(
    size: int,
    x: Sequence[object] | np.ndarray | None = None,
    holdout_year: int = 2024,
) -> tuple[np.ndarray, np.ndarray]:
    if x is not None:
        raw_values = np.asarray(x)
        is_dated = np.issubdtype(raw_values.dtype, np.datetime64) or raw_values.dtype.kind in "OUS"
        if is_dated:
            dates = pd.to_datetime(raw_values, errors="coerce")
            dated_values = dates.year.to_numpy()
            train_mask = dated_values < holdout_year
            test_mask = dated_values == holdout_year
            if np.count_nonzero(train_mask) > 0 and np.count_nonzero(test_mask) > 0:
                return np.flatnonzero(train_mask), np.flatnonzero(test_mask)
    split = max(1, size - 12)
    if size < 4:
        split = max(1, size // 2)
    return np.arange(split), np.arange(split, size)


def select_degree(
    x: Sequence[object] | np.ndarray,
    y: Sequence[float] | np.ndarray,
    candidates: Sequence[int] = (1, 2, 3, 4, 5),
    holdout_year: int = 2024,
) -> DegreeSelection:
    """Select the degree with lowest temporal holdout RMSE, breaking ties low."""
    raw_x = np.asarray(x)
    x_values = _as_numeric_x(raw_x)
    y_values = np.asarray(y, dtype=float)
    if len(x_values) != len(y_values):
        raise InputError("x e y devem possuir o mesmo tamanho")
    if len(x_values) < 2:
        raise InputError("seleção de grau exige ao menos duas observações")
    candidate_values = tuple(candidates)
    for degree in candidate_values:
        validate_degree(degree)
    train_idx, test_idx = _holdout_indices(len(x_values), raw_x, holdout_year)
    rows: list[dict[str, float | int]] = []
    for degree in candidate_values:
        if len(train_idx) <= degree:
            rows.append({"degree": degree, "rmse": float("inf")})
            continue
        coefficients = _fit_coefficients(x_values[train_idx], y_values[train_idx], degree)
        prediction = np.polynomial.polynomial.polyval(x_values[test_idx], coefficients)
        rmse = float(np.sqrt(np.mean((y_values[test_idx] - prediction) ** 2)))
        rows.append({"degree": degree, "rmse": rmse})
    candidate_frame = pd.DataFrame(rows)
    ordered = candidate_frame.sort_values(["rmse", "degree"], kind="mergesort")
    degree = int(ordered.iloc[0]["degree"])
    return DegreeSelection(degree=degree, candidates=candidate_frame.reset_index(drop=True))


def polynomial_fit(
    x: Sequence[object] | np.ndarray,
    y: Sequence[float] | np.ndarray,
    degree: int | None = None,
) -> PolyFitResult:
    """Fit a polynomial in normalized ``Polynomial.fit`` space, then expose canonical coefficients."""
    raw_x = np.asarray(x)
    x_values = _as_numeric_x(raw_x)
    y_values = np.asarray(y, dtype=float)
    if len(x_values) != len(y_values):
        raise InputError("x e y devem possuir o mesmo tamanho")
    selected = select_degree(raw_x, y_values) if degree is None else None
    selected_degree = selected.degree if selected is not None else degree
    validate_degree(int(selected_degree))
    coefficients = _fit_coefficients(x_values, y_values, int(selected_degree))
    fitted = np.polynomial.polynomial.polyval(x_values, coefficients)
    residual = y_values - fitted
    total = np.sum((y_values - np.mean(y_values)) ** 2)
    r2 = 1.0 if total == 0 else float(1 - np.sum(residual**2) / total)
    denominator = len(y_values) - int(selected_degree) - 1
    r2_adj = (
        float(1 - (1 - r2) * (len(y_values) - 1) / denominator) if denominator > 0 else float("nan")
    )
    train_idx, test_idx = _holdout_indices(len(x_values), raw_x)
    rmse_holdout = float("nan")
    if len(train_idx) > int(selected_degree) and len(test_idx) > 0:
        train_coefficients = _fit_coefficients(
            x_values[train_idx], y_values[train_idx], int(selected_degree)
        )
        prediction = np.polynomial.polynomial.polyval(x_values[test_idx], train_coefficients)
        rmse_holdout = float(np.sqrt(np.mean((y_values[test_idx] - prediction) ** 2)))
    candidates = (
        selected.candidates if selected is not None else select_degree(raw_x, y_values).candidates
    )
    source = "auto" if degree is None else "forced"
    return PolyFitResult(
        coefs=coefficients,
        degree=int(selected_degree),
        degree_source=source,
        r2=r2,
        r2_adj=r2_adj,
        rmse_holdout=rmse_holdout,
        candidates=candidates,
    )


def _format_number(value: float) -> str:
    absolute = abs(float(value))
    if absolute == 0:
        return "0,000"
    if absolute < 1e-3 or absolute >= 1e4:
        exponent = int(np.floor(np.log10(absolute)))
        mantissa = absolute / 10**exponent
        return f"{mantissa:.3f}".replace(".", ",") + f"\\times 10^{{{exponent}}}"
    decimals = max(0, 3 - int(np.floor(np.log10(absolute))))
    return f"{absolute:.{decimals}f}".replace(".", ",")


def _term(coefficient: float, power: int) -> str:
    number = _format_number(coefficient)
    if power == 0:
        return number
    variable = "x" if power == 1 else f"x^{{{power}}}"
    return f"{number} {variable}"


def polynomial_equation_label(
    coefs_desc: Sequence[float],
    degree: int,
    r2: float,
    r2_adj: float | None = None,
    terms_per_line: int = 3,
) -> str:
    """Render a deterministic mathtext polynomial equation and fit summary."""
    validate_degree(degree)
    if terms_per_line < 1:
        raise InputError("termos por linha deve ser positivo")
    coefficients = list(coefs_desc)[: degree + 1]
    terms: list[str] = []
    for position, coefficient in enumerate(coefficients):
        power = degree - position
        prefix = ""
        if position > 0:
            prefix = " - " if coefficient < 0 else " + "
        if position == 0 and coefficient < 0:
            prefix = "-"
        terms.append(prefix + _term(coefficient, power))
    groups = [
        terms[start : start + terms_per_line] for start in range(0, len(terms), terms_per_line)
    ]
    equation = "$y = " + "\n".join("".join(group) for group in groups) + "$"
    adjusted = r2 if r2_adj is None else r2_adj
    r2_text = f"{r2:.4f}".replace(".", ",")
    adjusted_text = f"{adjusted:.4f}".replace(".", ",")
    return f"{equation}\n grau = {degree} | R² = {r2_text} | R²_aj = {adjusted_text}"
