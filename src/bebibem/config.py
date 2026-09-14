"""Defaults and case constants shared by the forecasting pipeline."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge

DEFAULT_INPUT = Path("data/raw/demanda_loja_propria.csv")
DEFAULT_OUTDIR = Path("reports")
FIGURE_FORMATS = ("png", "svg", "pdf")
PNG_DPI = 300
SEED = 42
MIN_OBS_FOR_ML = 24
HOLDOUT_YEAR = 2024
FORECAST_YEAR = 2025
ORIGIN_YEAR = 2022
ORIGIN_MONTH = 1
MONTH_AXIS_LABEL = "T (índice inteiro do mês, T=0 em jan/2022)"


def global_month_index(years: Any, months: Any) -> np.ndarray:
    """Integer month index T = 12*(ano-ORIGIN_YEAR) + (mes-ORIGIN_MONTH); T=0 is January/2022."""
    return (np.asarray(years, dtype=float) - ORIGIN_YEAR) * 12.0 + (
        np.asarray(months, dtype=float) - ORIGIN_MONTH
    )


def month_index(dates: Any) -> np.ndarray:
    """Convert calendar dates to the integer month index T used on every timeline x-axis."""
    index = pd.DatetimeIndex(pd.to_datetime(dates))
    return global_month_index(index.year.to_numpy(), index.month.to_numpy())


@dataclass(frozen=True)
class CapacityLine:
    """Monthly capacity in cases before and after the documented expansion."""

    before: int
    after: int


CASE_CAPACITY = {
    "suco_premium": CapacityLine(before=12_000, after=15_600),
    "geleia_de_frutas": CapacityLine(before=3_000, after=3_000),
    "doce_de_frutas": CapacityLine(before=5_000, after=5_000),
}


MODEL_SPECS: dict[str, Callable[[], BaseEstimator]] = {
    "ridge": lambda: Ridge(alpha=1.0),
    "random_forest": lambda: RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=2,
        random_state=SEED,
    ),
    "gradient_boosting": lambda: GradientBoostingRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=2,
        random_state=SEED,
    ),
}
