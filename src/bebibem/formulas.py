"""Single source of LaTeX formulas shared by figures and reports."""

from __future__ import annotations

from collections.abc import Sequence

from .io_data import InputError

SYMBOLS = {
    "y_t": r"y_t",
    r"\hat{y}_t": r"\hat{y}_t",
    "n": "n",
    "w": "w",
    "d": "d",
    "k": "k",
    "T_0": r"T_0=\{t:y_t\ne 0\}",
    "beta": r"\beta",
    "X": "X",
}

FORMULAS = {
    "linear_interp": r"\hat{y}(t) = y_i + \frac{y_{i+1}-y_i}{t_{i+1}-t_i}\,(t-t_i), \qquad t \in [t_i,\, t_{i+1}]",
    "poly_fit": r"\hat{y}(x)=\sum_{j=0}^{d} a_j\,x^{j}, \qquad \mathbf{a}=\arg\min_{\mathbf{a}}\sum_{t=1}^{n}\left(y_t-\sum_{j=0}^{d}a_j\,x_t^{j}\right)^{2}",
    "r2": r"R^{2}=1-\frac{\sum_{t}(y_t-\hat{y}_t)^{2}}{\sum_{t}(y_t-\bar{y})^{2}}",
    "r2_adj": r"R^{2}_{aj}=1-(1-R^{2})\,\frac{n-1}{n-d-1}",
    "ma_simple": r"MA_w(t)=\frac{1}{w}\sum_{i=0}^{w-1} y_{t-i}",
    "ma_centered": r"MA^{c}_{w}(t)=\frac{1}{2}\left(\frac{1}{w}\sum_{i=-w/2}^{w/2-1} y_{t+i}+\frac{1}{w}\sum_{i=-w/2+1}^{w/2} y_{t+i}\right)",
    "seasonal_index": r"S_m=\frac{\bar{y}_m}{\bar{y}}, \qquad \bar{y}_m=\frac{1}{|A|}\sum_{a\in A} y_{a,m}",
    "kmeans": r"\min_{C_1,\dots,C_k}\ \sum_{j=1}^{k}\sum_{x\in C_j}\lVert x-\mu_j\rVert_2^{2}, \qquad \mu_j=\frac{1}{|C_j|}\sum_{x\in C_j}x",
    "silhouette": r"s(i)=\frac{b(i)-a(i)}{\max\{a(i),\,b(i)\}}",
    "ridge": r"\min_{\beta}\ \lVert y-X\beta\rVert_2^{2}+\alpha\lVert\beta\rVert_2^{2}",
    "recursive_forecast": r"\hat{y}_{t+h}=f\!\left(\hat{y}_{t+h-1},\ y_{t+h-12},\ \text{mês}_{t+h},\ \text{trend}_{t+h},\ c_{m(t+h)}\right)",
    "mad": r"\mathrm{MAD}=\frac{1}{n}\sum_{t=1}^{n}\left|y_t-\hat{y}_t\right|",
    "mse": r"\mathrm{MSE}=\frac{1}{n}\sum_{t=1}^{n}\left(y_t-\hat{y}_t\right)^{2}",
    "rmse": r"\mathrm{RMSE}=\sqrt{\mathrm{MSE}}",
    "mape": r"\mathrm{MAPE}=\frac{100}{|T_0|}\sum_{t\in T_0}\left|\frac{y_t-\hat{y}_t}{y_t}\right|",
    "mpe": r"\mathrm{MPE}=\frac{100}{|T_0|}\sum_{t\in T_0}\frac{y_t-\hat{y}_t}{y_t}",
    "smape": r"\mathrm{sMAPE}=\frac{100}{n}\sum_{t=1}^{n}\frac{\left|y_t-\hat{y}_t\right|}{\left(\left|y_t\right|+\left|\hat{y}_t\right|\right)/2} \quad \text{(usada quando } n_{zeros}>0\text{)}",
    "normal_equation": r"X=\begin{bmatrix}1 & x_1\\ \vdots & \vdots\\ 1 & x_n\end{bmatrix}, \qquad \hat{\beta}=\left(X^{\top}X\right)^{-1}X^{\top}y \quad\Longleftrightarrow\quad \left(X^{\top}X\right)\hat{\beta}=X^{\top}y",
    "linear_model": r"\hat{y}(x)=\hat{\beta}_0+\hat{\beta}_1 x",
    "linear_sums": r"\hat{\beta}_1=\frac{n\sum_{t} x_t y_t-\sum_{t} x_t \sum_{t} y_t}{n\sum_{t} x_t^{2}-\left(\sum_{t} x_t\right)^{2}}, \qquad \hat{\beta}_0=\bar{y}-\hat{\beta}_1\bar{x}",
    "exponential_model": r"y=a\,e^{b x}",
    "exponential_loglinear": r"y=a\,e^{b x} \quad\Longrightarrow\quad \ln y=\ln a+b x",
    "logistic_sigmoid": r"P(y=1\mid x)=\sigma\!\left(\beta^{\top}x\right)=\frac{1}{1+e^{-\beta^{\top}x}}",
    "logloss": r"\mathcal{L}(\beta)=-\frac{1}{n}\sum_{i=1}^{n}\Big[y_i\ln \hat{p}_i+(1-y_i)\ln\left(1-\hat{p}_i\right)\Big]",
    "confusion_matrix": r"C=\begin{bmatrix} VN & FP\\ FN & VP \end{bmatrix}",
    "accuracy": r"\text{Acurácia}=\frac{VP+VN}{VP+VN+FP+FN}",
    "precision_recall": r"\text{Precisão}=\frac{VP}{VP+FP}, \qquad \text{Recall}=\frac{VP}{VP+FN}",
    "f1": r"F_1=2\cdot\frac{\text{Precisão}\cdot\text{Recall}}{\text{Precisão}+\text{Recall}}",
}

TIMESERIES_FORMULAS = {
    "holt_winters_forecast": r"\hat{y}_{t+h} = (\ell_t + h b_t)\, s_{t+h-m(k+1)}",
    "holt_winters_level": r"\ell_t = \alpha\,\frac{y_t}{s_{t-m}} + (1-\alpha)(\ell_{t-1} + b_{t-1})",
    "holt_winters_trend": r"b_t = \beta\,(\ell_t - \ell_{t-1}) + (1-\beta)\,b_{t-1}",
    "holt_winters_seasonal": r"s_t = \gamma\,\frac{y_t}{\ell_t} + (1-\gamma)\,s_{t-m}",
    "sarima_model": r"\Phi_P(B^s)\phi_p(B)(1-B)^d(1-B^s)^D y_t = c + \Theta_Q(B^s)\theta_q(B)\,\varepsilon_t",
    "fourier_harmonic": r"y(t) = a_0 + b\,t + \sum_{k=1}^{K}\left[a_k\cos\!\left(\frac{2\pi k t}{P}\right) + b_k\sin\!\left(\frac{2\pi k t}{P}\right)\right] + \varepsilon_t",
}


def timeseries_footnote(keys: Sequence[str]) -> str:
    """Return selected time series formulas as mathtext lines for figure footnotes."""
    unknown = [key for key in keys if key not in TIMESERIES_FORMULAS]
    if unknown:
        raise InputError(f"fórmula(s) de séries temporais desconhecida(s): {unknown}")
    return "\n".join(f"${TIMESERIES_FORMULAS[key]}$" for key in keys)


def metric_footnote(keys: Sequence[str]) -> str:
    """Return selected formulas as separate mathtext lines for figure footnotes."""
    unknown = [key for key in keys if key not in FORMULAS]
    if unknown:
        raise InputError(f"fórmula(s) desconhecida(s): {unknown}")
    return "\n".join(f"${FORMULAS[key]}$" for key in keys)
