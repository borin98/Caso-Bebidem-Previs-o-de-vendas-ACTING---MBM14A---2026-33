"""Capacity scenario constants and explicit unit-to-case conversion."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CASE_CAPACITY
from .io_data import InputError


def capacity_frame() -> pd.DataFrame:
    """Return documented monthly capacity before/after expansion."""
    rows = [
        {
            "produto": product,
            "antes": line.before,
            "depois": line.after,
            "delta": line.after - line.before,
        }
        for product, line in CASE_CAPACITY.items()
    ]
    result = pd.DataFrame(rows)
    total_before = int(result["antes"].sum())
    total_after = int(result["depois"].sum())
    result.loc[len(result)] = {
        "produto": "total",
        "antes": total_before,
        "depois": total_after,
        "delta": total_after - total_before,
    }
    return result


def validate_units_per_case(value: int) -> None:
    if value <= 0:
        raise InputError("units_per_case deve ser maior que zero")


def demand_in_cases(
    forecast_units: pd.DataFrame, units_per_case: int | None
) -> pd.DataFrame | None:
    """Convert forecast units to whole cases only when an explicit factor is given."""
    if units_per_case is None:
        return None
    validate_units_per_case(units_per_case)
    value_column = "unidades_previstas"
    if value_column not in forecast_units.columns:
        value_column = "unidades"
    if value_column not in forecast_units.columns:
        raise ValueError("forecast_units precisa conter unidades_previstas ou unidades")
    result = forecast_units.copy()
    result["caixas"] = np.ceil(result[value_column].astype(float) / units_per_case).astype(int)
    return result
