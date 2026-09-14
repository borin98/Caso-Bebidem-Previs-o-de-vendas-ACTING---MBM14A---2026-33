import numpy as np
import pandas as pd
import pytest

from bebibem.io_data import InputError
from bebibem.smoothing import moving_average, moving_average_table, validate_windows


def test_trailing_moving_average_w3_has_warmup_nan_and_expected_values():
    series = pd.Series(np.arange(1, 13, dtype=float))

    result = moving_average(series, 3)

    assert result.iloc[:2].isna().all()
    assert result.iloc[2:].tolist() == pytest.approx([2, 3, 4, 5, 6, 7, 8, 9, 10, 11])


def test_centered_even_moving_average_uses_double_12_alignment():
    series = pd.Series(np.ones(24, dtype=float) * 7)

    result = moving_average(series, 12, centered=True)

    assert result.iloc[:6].isna().all()
    assert result.iloc[6:18].tolist() == pytest.approx([7.0] * 12)
    assert result.iloc[18:].isna().all()


def test_moving_average_table_has_one_window_column_per_product():
    frame = pd.DataFrame(
        {
            "produto": ["a"] * 4 + ["b"] * 4,
            "data": list(pd.date_range("2022-01", periods=4, freq="MS")) * 2,
            "unidades": [1, 2, 3, 4, 10, 20, 30, 40],
        }
    )

    result = moving_average_table(frame, windows=(3,))

    assert "ma_3" in result.columns
    assert result.groupby("produto").size().to_dict() == {"a": 4, "b": 4}
    assert result.loc[result["produto"] == "a", "ma_3"].iloc[-1] == pytest.approx(3)


def test_validate_windows_rejects_window_larger_than_series():
    with pytest.raises(InputError, match=r"janela 5.*3"):
        validate_windows((5,), n_obs=3)


def test_centered_moving_average_rejects_odd_window():
    with pytest.raises(InputError, match="par"):
        moving_average(pd.Series([1.0, 2.0, 3.0]), 3, centered=True)
