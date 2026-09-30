export interface ModelFormula {
  equation: string;
  note: string;
}

/**
 * Fórmulas LaTeX das implementações em `src/bebibem/` usadas pelo motor do POC.
 * `ŷ` é a previsão, `y` a venda observada, `t` o período mensal e `xₜ` o vetor de variáveis.
 */
export const MODEL_FORMULAS: Record<string, ModelFormula> = {
  ridge: {
    equation: "\\hat{y}_t = \\beta_0 + \\boldsymbol{\\beta}^{\\mathsf{T}}\\mathbf{x}_t, \\qquad \\hat{\\boldsymbol{\\beta}} = (X^{\\mathsf{T}}X + \\alpha I)^{-1}X^{\\mathsf{T}}\\mathbf{y}",
    note: "xₜ usa lag 1, lag 12, tendência, indicadores de mês e clusters sazonais.",
  },
  random_forest: {
    equation: "\\hat{y}_t = \\frac{1}{B}\\sum_{b=1}^{B} T_b(\\mathbf{x}_t)",
    note: "Média das previsões B das árvores treinadas sobre o mesmo vetor xₜ.",
  },
  gradient_boosting: {
    equation: "F_M(\\mathbf{x}_t) = F_0(\\mathbf{x}_t) + \\eta\\sum_{k=1}^{M}\\gamma_k h_k(\\mathbf{x}_t)",
    note: "Árvores são somadas sequencialmente para corrigir os resíduos do conjunto anterior.",
  },
  linear_normal_equation: {
    equation: "\\hat{y}_t = \\beta_0 + \\beta_1 t, \\qquad \\hat{\\boldsymbol{\\beta}} = (X^{\\mathsf{T}}X)^{-1}X^{\\mathsf{T}}\\mathbf{y}",
    note: "Regressão linear ajustada por equação normal sobre o índice mensal t.",
  },
  exponential_loglinear: {
    equation: "\\ln(y_t) = \\beta_0 + \\beta_1 t, \\qquad \\hat{y}_t = \\exp(\\beta_0 + \\beta_1 t)",
    note: "Coeficientes de ln(y) calculados pelas fórmulas explícitas de mínimos quadrados.",
  },
  exponential_normal_equation: {
    equation: "\\ln(\\mathbf{y}) = X\\boldsymbol{\\beta}, \\qquad \\hat{\\boldsymbol{\\beta}} = (X^{\\mathsf{T}}X)^{-1}X^{\\mathsf{T}}\\ln(\\mathbf{y}), \\qquad \\hat{y}_t = \\exp(\\beta_0 + \\beta_1 t)",
    note: "Mesmo modelo exponencial, com coeficientes de ln(y) resolvidos por matriz normal.",
  },
  holt_winters_multiplicative: {
    equation: "\\hat{y}_{t+h} = (\\ell_t + h b_t)s_{t+h-12}",
    note: "Tendência aditiva, sazonalidade multiplicativa anual e parâmetros α, β e γ estimados.",
  },
  sarima: {
    equation: "\\left(1 - \\phi_1 B\\right)\\left(1 - \\Phi_1 B^{12}\\right)y_t = c + \\varepsilon_t",
    note: "SARIMA(1,0,0) × (1,0,0)₁₂ com constante c e período sazonal de 12 meses.",
  },
  fourier_harmonic: {
    equation: "\\hat{y}(t) = a_0 + bt + \\sum_{k=1}^{2}\\left[a_k\\cos\\left(\\frac{2\\pi kt}{12}\\right) + b_k\\sin\\left(\\frac{2\\pi kt}{12}\\right)\\right]",
    note: "Regressão por mínimos quadrados com tendência linear, dois harmônicos e período anual de 12 meses.",
  },
};
