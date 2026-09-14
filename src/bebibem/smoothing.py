"""Trailing and centered moving-average utilities."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from .io_data import InputError


def validate_windows(windows: Sequence[int], n_obs: int) -> None:
    """Validate positive windows that fit the available series length."""
    if n_obs < 1:
        raise InputError("série sem observações")
    if len(windows) == 0:
        raise InputError("ao menos uma janela deve ser informada")
    for window in windows:
        if window < 1:
            raise InputError(f"janela inválida: {window}")
        if window > n_obs:
            raise InputError(f"janela {window} maior que o tamanho da série {n_obs}")


def _centered_double_window(series: pd.Series, window: int) -> pd.Series:
    if window % 2 == 1:
        raise InputError("média móvel centrada exige janela par")
    values = series.astype(float).to_numpy()
    output = np.full(len(values), np.nan, dtype=float)
    half = window // 2
    for position in range(half, len(values) - half):
        first = values[position - half : position + half]
        second = values[position - half + 1 : position + half + 1]
        if np.isnan(first).any() or np.isnan(second).any():
            continue
        output[position] = (float(np.mean(first)) + float(np.mean(second))) / 2
    return pd.Series(output, index=series.index, name=series.name)


def moving_average(series: pd.Series, window: int, centered: bool = False) -> pd.Series:
    """Calculate trailing or even-window double-centered moving average."""
    validate_windows((window,), len(series))
    if centered:
        return _centered_double_window(series, window)
    return series.astype(float).rolling(window=window, min_periods=window).mean()


def moving_average_table(df: pd.DataFrame, windows: Sequence[int]) -> pd.DataFrame:
    """Append trailing and centered even-window moving-average columns."""
    required = {"produto", "data", "unidades"}
    missing = sorted(required.difference(df.columns))
    if len(missing) > 0:
        raise InputError(f"colunas faltantes para média móvel: {missing}")
    validate_windows(windows, int(df.groupby("produto").size().max()))
    result = df.copy()
    for window in windows:
        window = int(window)
        column = f"ma_{window}"
        result[column] = np.nan
        centered_column = f"ma_centered_{window}"
        if window % 2 == 0:
            result[centered_column] = np.nan
        for _, group in result.groupby("produto", sort=False):
            ordered = group.sort_values("data")
            values = moving_average(ordered["unidades"], window)
            result.loc[ordered.index, column] = values.to_numpy()
            if window % 2 == 0:
                centered_values = moving_average(ordered["unidades"], window, centered=True)
                result.loc[ordered.index, centered_column] = centered_values.to_numpy()
    return result.sort_values(["produto", "data"]).reset_index(drop=True)
