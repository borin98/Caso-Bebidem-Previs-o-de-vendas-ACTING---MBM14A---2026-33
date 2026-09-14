import logging

import numpy as np
import pandas as pd

from bebibem.clustering import cluster_months, cluster_series, seasonal_index_matrix


def _monthly_frame(years=(2022, 2023, 2024)):
    rows = []
    for product, scale in [("a", 100), ("b", 200), ("c", 300)]:
        for year in years:
            for month in range(1, 13):
                seasonal = 2.0 if month <= 6 else 0.5
                rows.append(
                    {"produto": product, "ano": year, "mes": month, "unidades": scale * seasonal}
                )
    return pd.DataFrame(rows)


def test_seasonal_index_matrix_has_month_rows_and_product_columns():
    matrix = seasonal_index_matrix(_monthly_frame())
    assert matrix.shape == (12, 3)
    assert matrix.index.tolist() == list(range(1, 13))
    assert np.isclose(matrix.loc[1, "a"], 2.0 / 1.25)
    assert np.isclose(matrix.loc[7, "c"], 0.5 / 1.25)


def test_cluster_months_selects_k_and_labels_high_regime_stably():
    matrix = seasonal_index_matrix(_monthly_frame())
    first = cluster_months(matrix, k=2)
    second = cluster_months(matrix, k=2)
    assert first.k == 2
    assert set(first.labels) == {"alta", "baixa"}
    assert first.labels.loc[1] == "alta"
    assert first.labels.equals(second.labels)
    assert first.scores.keys() == {2}


def test_cluster_months_selects_best_silhouette_from_grid():
    matrix = seasonal_index_matrix(_monthly_frame())
    result = cluster_months(matrix, k_grid=(2, 3, 4))
    assert set(result.scores) == {2, 3, 4}
    assert result.k == max(result.scores, key=result.scores.get)


def test_cluster_series_row_zscore_and_multiindex_labels():
    frame = _monthly_frame().copy()
    frame.loc[(frame["ano"] == 2023) & (frame["mes"].isin([1, 2, 3])), "unidades"] *= 1.3
    result = cluster_series(frame)
    assert result.skipped is False
    assert len(result.labels) == 9
    assert isinstance(result.labels.index, pd.MultiIndex)
    assert set(result.labels.index.names) == {"produto", "ano"}


def test_cluster_series_skips_fewer_than_three_samples(caplog):
    frame = _monthly_frame(years=(2022,)).query("produto == 'a'")
    with caplog.at_level(logging.WARNING):
        result = cluster_series(frame)
    assert result.skipped is True
    assert result.reason == "insufficient_data"
    assert "amostras insuficientes" in caplog.text
