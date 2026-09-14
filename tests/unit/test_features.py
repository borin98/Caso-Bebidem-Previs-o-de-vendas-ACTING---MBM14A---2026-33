import numpy as np
import pandas as pd

from bebibem.features import build_features, next_row, split_train_holdout


def _frame(periods=36):
    dates = pd.date_range("2022-01-01", periods=periods, freq="MS")
    return pd.DataFrame(
        {
            "produto": "a",
            "ano": dates.year,
            "mes": dates.month,
            "data": dates,
            "unidades": np.arange(periods, dtype=float) + 100,
        }
    )


def _clusters():
    return pd.Series({month: ("alta" if month in (1, 2) else "baixa") for month in range(1, 13)})


def test_build_features_has_exact_feature_columns_and_discards_warmup_rows():
    result = build_features(_frame(), _clusters())
    expected = [
        "lag_1",
        "lag_12",
        *[f"mes_{m}" for m in range(2, 13)],
        "trend",
        "cluster_alta",
        "cluster_baixa",
    ]
    assert result.columns.tolist() == expected
    assert len(result) == 24
    assert result.isna().sum().sum() == 0
    assert result.iloc[0]["lag_1"] == 111
    assert result.iloc[0]["lag_12"] == 100


def test_split_train_holdout_excludes_2024_from_training():
    frame = _frame()
    features = build_features(frame, _clusters())
    y = frame.set_index("data").loc[features.index, "unidades"]
    train_x, train_y, holdout_x, holdout_y = split_train_holdout(features, y, 2024)
    assert train_x.index.max().year == 2023
    assert holdout_x.index.min().year == 2024
    assert train_y.index.max().year == 2023
    assert holdout_y.index.min().year == 2024


def test_next_row_uses_recursive_history_and_month_cluster():
    frame = _frame()
    history = frame.set_index("data")["unidades"]
    row = next_row(history, "2025-01-01", _clusters())
    assert row.index[0] == pd.Timestamp("2025-01-01")
    assert row.iloc[0]["lag_1"] == 135
    assert row.iloc[0]["lag_12"] == 124
    assert row.iloc[0]["mes_2"] == 0
    assert row.iloc[0]["cluster_alta"] == 1


def test_next_row_signals_insufficient_history_without_exception():
    history = _frame(12).set_index("data")["unidades"]
    row = next_row(history, "2023-01-01", _clusters())
    assert row.empty
    assert row.attrs["insufficient_data"] is True
