import matplotlib.pyplot as plt

from bebibem.formulas import FORMULAS, SYMBOLS, metric_footnote

EXPECTED_KEYS = {
    "linear_interp",
    "poly_fit",
    "r2",
    "r2_adj",
    "ma_simple",
    "ma_centered",
    "seasonal_index",
    "kmeans",
    "silhouette",
    "ridge",
    "recursive_forecast",
    "mad",
    "mse",
    "rmse",
    "mape",
    "mpe",
    "smape",
    "normal_equation",
    "linear_model",
    "linear_sums",
    "exponential_model",
    "exponential_loglinear",
    "logistic_sigmoid",
    "logloss",
    "confusion_matrix",
    "accuracy",
    "precision_recall",
    "f1",
}


def test_formulas_contains_exactly_the_28_design_keys_and_nonempty_latex():
    assert set(FORMULAS) == EXPECTED_KEYS
    assert all(isinstance(value, str) and value.strip() for value in FORMULAS.values())


def test_symbols_defines_shared_notation():
    assert {"y_t", r"\hat{y}_t", "n", "w", "d", "k"}.issubset(SYMBOLS)


def test_core_formulas_match_design_equations():
    assert FORMULAS["linear_interp"] == (
        r"\hat{y}(t) = y_i + \frac{y_{i+1}-y_i}{t_{i+1}-t_i}\,(t-t_i), "
        r"\qquad t \in [t_i,\, t_{i+1}]"
    )
    assert FORMULAS["normal_equation"].startswith(r"X=\begin{bmatrix}")
    assert r"\Longleftrightarrow" in FORMULAS["normal_equation"]
    assert FORMULAS["accuracy"].startswith(r"\text{Acurácia}")
    assert FORMULAS["ma_simple"] == r"MA_w(t)=\frac{1}{w}\sum_{i=0}^{w-1} y_{t-i}"
    assert FORMULAS["rmse"] == r"\mathrm{RMSE}=\sqrt{\mathrm{MSE}}"


def test_metric_footnote_contains_requested_formulas_and_renders_with_agg():
    footnote = metric_footnote(["mad", "mape"])

    assert FORMULAS["mad"] in footnote
    assert FORMULAS["mape"] in footnote
    figure, axis = plt.subplots()
    axis.text(0.01, 0.01, footnote)
    figure.canvas.draw()
    plt.close(figure)
