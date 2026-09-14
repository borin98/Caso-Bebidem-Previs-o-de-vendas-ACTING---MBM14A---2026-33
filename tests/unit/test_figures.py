import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bebibem.figures import (
    fig_interpolation,
    fig_moving_average,
    fig_points_all,
    fig_points_product,
)
from bebibem.formulas import FORMULAS
from bebibem.interpolation import polynomial_equation_label, polynomial_fit


def demand_frame() -> pd.DataFrame:
    dates = pd.date_range("2022-01-01", periods=24, freq="MS")
    rows = []
    for product, offset in (("suco_premium", 0), ("geleia_de_frutas", 10)):
        for index, date in enumerate(dates):
            rows.append(
                {
                    "produto": product,
                    "produto_label": "Suco Premium"
                    if product == "suco_premium"
                    else "Geleia de frutas",
                    "data": date,
                    "unidades": float(index + offset) if index != 5 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def texts(figure):
    return [artist.get_text() for axis in figure.axes for artist in axis.texts] + [
        artist.get_text() for artist in figure.texts
    ]


def test_points_product_uses_label_and_omits_nan_marker():
    figure = fig_points_product(demand_frame(), "suco_premium")
    axis = figure.axes[0]

    assert axis.get_title() == "Pontos observados — Suco Premium"
    collection = axis.collections[0]
    assert len(collection.get_offsets()) == 23
    plt.close(figure)


def test_points_all_has_one_observed_artist_per_product():
    figure = fig_points_all(demand_frame())
    axis = figure.axes[0]

    assert len(axis.collections) == 2
    assert [line.get_label() for line in axis.lines] == []
    assert {text.get_text() for text in axis.legend().get_texts()} == {
        "Suco Premium",
        "Geleia de frutas",
    }
    plt.close(figure)


def test_interpolation_has_observations_curves_exact_equation_and_footer():
    frame = demand_frame().query("produto == 'suco_premium'")
    figure = fig_interpolation(frame, degree=1)
    axis = figure.axes[0]
    values = frame["unidades"].to_numpy()
    filled = pd.Series(values).interpolate().bfill().ffill().to_numpy()
    fit = polynomial_fit(np.arange(len(values)), filled, degree=1)
    equation = polynomial_equation_label(fit.coefs_desc, fit.degree, fit.r2, fit.r2_adj)

    assert len(axis.collections) == 1
    assert len(axis.lines) == 2
    assert equation in texts(figure)
    assert any("x = 0 em 2022-01" in text for text in texts(figure))
    assert any(FORMULAS["poly_fit"] in text for text in texts(figure))
    assert any(
        "grau 1" in text and "--poly-degree" in text
        for text in [line.get_label() for line in axis.lines]
    )
    plt.close(figure)


def test_moving_average_overlays_ma3_and_ma12():
    frame = demand_frame().query("produto == 'suco_premium'")
    figure = fig_moving_average(frame)
    axis = figure.axes[0]

    assert len(axis.collections) == 1
    assert any(line.get_ydata()[11] == 10 for line in axis.lines if line.get_label() == "MA(3)")
    plt.close(figure)


from bebibem.classification import ClassificationResult
from bebibem.clustering import ClusterResult
from bebibem.figures import (
    fig_backtest,
    fig_combined_error_table,
    fig_confusion_matrix,
    fig_error_table,
    fig_forecast_2025_bar,
    fig_forecast_2025_curves_all,
    fig_forecast_2025_summary_table,
    fig_forecast_2025_total_bar,
    fig_metrics_bar,
    fig_regression,
    fig_series_clusters,
)
from bebibem.regression import exponential_regression_loglinear, linear_regression_normal_equation


def test_cluster_figures_show_regime_metadata_and_series_count():
    matrix = pd.DataFrame(
        {"suco_premium": [0.8, 1.2, 1.0], "geleia": [0.9, 1.1, 1.0]},
        index=[1, 2, 3],
    )
    month_result = ClusterResult(
        pd.Series(["baixa", "alta", "media"], index=[1, 2, 3]), 3, 0.8123, {3: 0.8123}
    )
    month_figure = __import__(
        "bebibem.figures", fromlist=["fig_month_clusters"]
    ).fig_month_clusters(matrix, month_result)
    assert "k=3" in month_figure.axes[0].get_title()
    assert "0.812" in month_figure.axes[0].get_title()
    plt.close(month_figure)

    frame = pd.DataFrame(
        [
            {"produto": product, "ano": year, "mes": month, "unidades": month + year - 2022}
            for product in ("suco_premium", "geleia_de_frutas", "doce_de_frutas")
            for year in (2022, 2023, 2024)
            for month in range(1, 4)
        ]
    )
    labels = pd.Series(
        ["a", "b", "a", "b", "a", "b", "a", "b", "a"],
        index=pd.MultiIndex.from_product(
            [("suco_premium", "geleia_de_frutas", "doce_de_frutas"), (2022, 2023, 2024)],
            names=["produto", "ano"],
        ),
    )
    series_figure = fig_series_clusters(frame, ClusterResult(labels, 2, 0.7, {2: 0.7}))
    assert len(series_figure.axes[0].lines) == 9
    assert "silhouette=0.700" in series_figure.axes[0].get_title()
    plt.close(series_figure)


def test_backtest_shows_full_2022_2024_history_not_only_holdout_year():
    actual = pd.DataFrame(
        {
            "produto": ["suco_premium"] * 36,
            "produto_label": ["Suco Premium"] * 36,
            "data": pd.date_range("2022-01-01", periods=36, freq="MS"),
            "unidades": np.arange(70, 106),
        }
    )
    predictions = pd.DataFrame(
        {
            "produto": ["suco_premium"] * 24,
            "data": list(pd.date_range("2024-01-01", periods=12, freq="MS")) * 2,
            "modelo": ["ridge"] * 12 + ["random_forest"] * 12,
            "unidades_previstas": list(np.arange(101, 113)) + list(np.arange(99, 111)),
        }
    )
    backtest = fig_backtest(actual, predictions, "suco_premium")
    assert len(backtest.axes[0].lines) == 2
    assert {line.get_label() for line in backtest.axes[0].lines} == {"ridge", "random_forest"}
    observed = next(
        collection
        for collection in backtest.axes[0].collections
        if collection.get_label() == "Observado"
    )
    assert len(observed.get_offsets()) == 36
    plt.close(backtest)

    metrics = pd.DataFrame(
        [
            {
                "produto": "suco_premium",
                "modelo": "ridge",
                "mape": 4.5,
                "mad": 2.0,
                "vencedor": True,
            },
            {
                "produto": "suco_premium",
                "modelo": "random_forest",
                "mape": 6.5,
                "mad": 3.0,
                "vencedor": False,
            },
        ]
    )
    bars = fig_metrics_bar(metrics)
    assert [bars.axes[0].patches[0].get_height() for _ in [0]] == [4.5]
    plt.close(bars)


def test_error_table_values_and_formula_footer_are_rendered():
    models = [
        "ridge",
        "random_forest",
        "gradient_boosting",
        "linear_normal_equation",
        "exponential_loglinear",
        "exponential_normal_equation",
    ]
    rows = [
        {
            "produto": product,
            "modelo": model,
            "mad": float(index + 1),
            "mse": float(index + 2),
            "rmse": float(index + 1),
            "mape": float(index + 3),
            "mpe": -float(index + 1),
            "vencedor": model == "ridge",
        }
        for product in ("suco_premium", "geleia_de_frutas", "doce_de_frutas")
        for index, model in enumerate(models)
    ]
    figure = fig_error_table(pd.DataFrame(rows))
    table = next(
        artist for artist in figure.axes[0].get_children() if artist.__class__.__name__ == "Table"
    )
    assert table[(1, 2)].get_text().get_text() == "1.0000"
    assert table[(1, 0)].get_facecolor()[:3] != table[(0, 0)].get_facecolor()[:3]
    labels = [table[(row, 1)].get_text().get_text() for row in range(1, 19)]
    assert set(labels) == set(models)
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    for row in range(1, 19):
        cell = table[(row, 1)]
        text_box = cell.get_text().get_window_extent(renderer)
        cell_box = cell.get_window_extent(renderer)
        assert text_box.x0 >= cell_box.x0 - 1
        assert text_box.x1 <= cell_box.x1 + 1
    assert any("MAD" in text.get_text() for text in figure.texts)
    plt.close(figure)


def test_combined_error_table_highlights_cross_group_winner_not_per_group_winner():
    rows = [
        {
            "produto": "doce_de_frutas",
            "modelo": "ridge",
            "grupo": "ML/regressão clássica",
            "mad": 14.39,
            "mse": 396.70,
            "rmse": 19.92,
            "mape": 34.55,
            "mpe": 30.61,
            "vencedor_geral": False,
        },
        {
            "produto": "doce_de_frutas",
            "modelo": "holt_winters_multiplicative",
            "grupo": "séries temporais",
            "mad": 6.10,
            "mse": 75.67,
            "rmse": 8.70,
            "mape": 15.53,
            "mpe": -2.99,
            "vencedor_geral": True,
        },
    ]
    figure = fig_combined_error_table(pd.DataFrame(rows))
    table = next(
        artist for artist in figure.axes[0].get_children() if artist.__class__.__name__ == "Table"
    )
    grupo_labels = [table[(row, 2)].get_text().get_text() for row in range(1, 3)]
    assert grupo_labels == ["ML/regressão clássica", "séries temporais"]
    ridge_row_color = table[(1, 0)].get_facecolor()[:3]
    hw_row_color = table[(2, 0)].get_facecolor()[:3]
    assert ridge_row_color != hw_row_color
    assert any("MAD" in text.get_text() for text in figure.texts)
    plt.close(figure)


def test_regression_annotations_and_non_applicable_note():
    values = np.arange(1, 13, dtype=float)
    x_values = np.arange(len(values), dtype=float)
    fits = {
        "linear_normal_equation": linear_regression_normal_equation(x_values, values),
        "exponential_loglinear": exponential_regression_loglinear(x_values, values * 0),
    }
    figure = fig_regression(
        pd.DataFrame(
            {
                "produto": "suco_premium",
                "data": pd.date_range("2022-01-01", periods=12, freq="MS"),
                "unidades": values,
            }
        ),
        fits,
    )
    texts_in_axes = [text.get_text() for text in figure.axes[0].texts]
    assert any("y =" in text and "R²" in text for text in texts_in_axes)
    assert any("not_applicable" in text for text in texts_in_axes)
    plt.close(figure)


def test_confusion_matrix_has_absolute_cell_annotations_and_formulas():
    result = ClassificationResult(
        {"accuracy": 0.75, "precision": 0.8, "recall": 0.5, "f1": 0.615},
        np.array([[3, 1], [2, 4]]),
    )
    figure = fig_confusion_matrix(result)
    assert [text.get_text() for text in figure.axes[0].texts] == ["3", "1", "2", "4"]
    assert any("Acurácia" in text.get_text() for text in figure.texts)
    plt.close(figure)


from bebibem.figures import fig_capacity, fig_forecast_all, fig_forecast_product


def test_forecast_figures_distinguish_history_and_future_and_show_metrics():
    history = pd.DataFrame(
        {
            "produto": ["suco_premium"] * 4,
            "produto_label": ["Suco Premium"] * 4,
            "data": pd.date_range("2024-09-01", periods=4, freq="MS"),
            "unidades": [10, 11, 12, 13],
        }
    )
    future = pd.DataFrame(
        {
            "produto": ["suco_premium"] * 2,
            "ano": [2025, 2025],
            "mes": [1, 2],
            "unidades_previstas": [14, 15],
            "modelo": ["ridge", "ridge"],
            "mape_holdout": [4.2, 4.2],
            "mad_holdout": [1.1, 1.1],
        }
    )
    figure = fig_forecast_product(history, future)
    axis = figure.axes[0]
    assert len(axis.lines) == 2
    assert axis.lines[0].get_linestyle() == "-"
    assert axis.lines[1].get_linestyle() == "--"
    assert "ridge" in axis.get_title()
    assert "MAPE=4.20%" in axis.get_title()
    assert "MAD=1.10" in axis.get_title()
    plt.close(figure)

    combined = fig_forecast_all(history, future)
    assert len(combined.axes[0].lines) == 2
    assert any("previsão" in line.get_label() for line in combined.axes[0].lines)
    plt.close(combined)


def test_forecast_2025_bar_charts_stay_isolated_from_history():
    forecast = pd.DataFrame(
        {
            "produto": ["suco_premium"] * 2,
            "ano": [2025, 2025],
            "mes": [1, 2],
            "unidades_previstas": [80.0, 82.0],
            "modelo": ["gradient_boosting"] * 2,
        }
    )
    bar = fig_forecast_2025_bar(forecast, "suco_premium")
    assert len(bar.axes[0].collections) == 0
    plt.close(bar)

    total_bar = fig_forecast_2025_total_bar(forecast)
    assert len(total_bar.axes[0].collections) == 0
    plt.close(total_bar)


def test_forecast_2025_curves_overlay_observed_history_when_given():
    history = pd.DataFrame(
        {
            "produto": ["suco_premium"] * 24 + ["geleia_de_frutas"] * 24,
            "data": list(pd.date_range("2022-01-01", periods=24, freq="MS")) * 2,
            "unidades": list(np.arange(50, 74)) + list(np.arange(20, 44)),
        }
    )
    forecast = pd.DataFrame(
        {
            "produto": ["suco_premium"] * 2 + ["geleia_de_frutas"] * 2,
            "ano": [2025, 2025, 2025, 2025],
            "mes": [1, 2, 1, 2],
            "unidades_previstas": [80.0, 82.0, 45.0, 46.0],
            "modelo": ["gradient_boosting"] * 2 + ["random_forest"] * 2,
        }
    )

    curves_with_history = fig_forecast_2025_curves_all(forecast, history=history)
    assert len(curves_with_history.axes[0].lines) == 4
    plt.close(curves_with_history)

    curves_no_history = fig_forecast_2025_curves_all(forecast)
    assert len(curves_no_history.axes[0].lines) == 2
    plt.close(curves_no_history)


def test_capacity_figure_uses_boxes_scale_and_documents_expansion_delta():
    figure = fig_capacity()
    axis = figure.axes[0]

    assert axis.get_ylabel() == "Caixas/mês"
    assert any("3.600" in text.get_text() for text in axis.texts)
    assert len(axis.patches) == 8
    assert len(figure.axes) == 1
    plt.close(figure)


def test_forecast_2025_summary_table_highlights_grand_total_row():
    summary = pd.DataFrame(
        {
            "produto_label": ["Doce de frutas", "Geleia de frutas", "Suco Premium", "Total (3 linhas)"],
            "modelo": ["holt_winters_multiplicative", "random_forest", "gradient_boosting", "—"],
            "unidades_previstas_total": [523, 180, 814, 1517],
        }
    )

    figure = fig_forecast_2025_summary_table(summary)
    axis = figure.axes[0]
    table = axis.tables[0]
    cell_texts = [cell.get_text().get_text() for cell in table.get_celld().values()]
    total_row = [
        table[(row, column)]
        for (row, column) in table.get_celld()
        if table[(row, column)].get_text().get_text() == "Total (3 linhas)"
    ]

    assert "1517" in cell_texts
    assert "Total (3 linhas)" in cell_texts
    assert total_row[0].get_facecolor() != (1.0, 1.0, 1.0, 1.0)
    plt.close(figure)

    empty_figure = fig_forecast_2025_summary_table(None)
    assert "Sem dados disponíveis" in empty_figure.axes[0].texts[0].get_text()
    plt.close(empty_figure)
