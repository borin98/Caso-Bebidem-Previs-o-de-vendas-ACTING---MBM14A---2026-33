# BebiBem — Previsão de Demanda da Loja Própria

Projeto Python (uv + `pyproject.toml`) que analisa o histórico mensal de demanda das três linhas da loja própria BebiBem (Suco Premium, Geleia de frutas, Doce de frutas — 2022 a 2024) e produz plots, interpolações, médias móveis, clusterização, comparação de modelos de machine learning e previsão dos próximos anos.

> **Status:** implementação concluída para análise, previsão, CLI, notebook e imagens Docker. A especificação completa está em `.specs/features/previsao-demanda-bebibem/` (`spec.md`, `context.md`, `design.md`, `tasks.md`) e as decisões de projeto estão em `.specs/STATE.md`.

- Fonte de negócio: `docs/Case BebiBem - MBM - Acting 2026.pdf` (questão 5, p. 3–4).
- Stack: `numpy`, `pandas`, `scikit-learn`, `matplotlib`.
- Saídas: figuras em **PNG (300 dpi) + SVG + PDF** e tabelas `.csv` em `reports/`.

---

## Sumário

- [Notação](#notação)
- [Formulário matemático](#formulário-matemático)
  - [Interpolação linear](#interpolação-linear)
  - [Interpolação polinomial](#interpolação-polinomial-ajuste-por-mínimos-quadrados)
  - [Qualidade do ajuste](#qualidade-do-ajuste-r-e-r-ajustado)
  - [Médias móveis](#médias-móveis)
  - [Índice sazonal](#índice-sazonal)
  - [Clusterização](#clusterização-kmeans-e-silhouette)
  - [Modelos de previsão](#modelos-de-previsão)
  - [Regressão linear (equação normal)](#regressão-linear-equação-normal)
  - [Regressão exponencial](#regressão-exponencial)
  - [Regressão logística e matriz de confusão](#regressão-logística-e-matriz-de-confusão)
  - [Previsão recursiva](#previsão-recursiva)
  - [Métricas de erro](#métricas-de-erro)
  - [Comparativo de modelos](#comparativo-de-modelos)
  - [Modelos de séries temporais (ciclos periódicos)](#modelos-de-séries-temporais-ciclos-periódicos)
    - [Resumo de escolha](#resumo-de-escolha)
    - [Suavização exponencial Holt-Winters Multiplicativo](#suavização-exponencial-holt-winters-multiplicativo)
    - [SARIMA](#sarima-sazonal-autorregressivo-integrado-de-médias-móveis)
    - [Fourier (Regressão Harmônica)](#fourier-regressão-harmônica)
    - [Comparativo de erros das séries temporais](#comparativo-de-erros-das-séries-temporais-holdout-2024)
- [Abordagem de treinamento e seleção de modelos](#abordagem-de-treinamento-e-seleção-de-modelos)
  - [Candidatos avaliados](#candidatos-avaliados)
  - [Critério de seleção](#critério-de-seleção)
  - [Resultados e previsão 2025](#resultados-e-previsão-2025)
  - [Limitações](#limitações)
- [Como executar](#como-executar)
- [Contrato do CSV de entrada](#contrato-do-csv-de-entrada)
- [Artefatos gerados](#artefatos-gerados)

---

## Notação

| Símbolo | Significado |
| --- | --- |
| $y_t$ | demanda observada (unidades) no instante $t$ |
| $\hat{y}_t$ | demanda prevista pelo modelo no instante $t$ |
| $\bar{y}$ | média das observações |
| $n$ | número de observações avaliadas |
| $w$ | janela da média móvel (meses) |
| $d$ | grau do polinômio |
| $k$ | número de clusters |
| $x$ | índice do mês desde o início da série ($x = 0$ em 2022-01) |
| $T_0$ | $\{t : y_t \neq 0\}$ — instantes usados nas métricas percentuais |
| $m$ | período do ciclo sazonal ($m = 12$ meses) |
| $K$ | número de harmônicos da série de Fourier |
| $\alpha, \beta, \gamma$ | parâmetros de suavização do Holt-Winters (nível, tendência, sazonalidade) |
| $\ell_t, b_t, s_t$ | componentes de nível, tendência e fator sazonal no instante $t$ |
| $B$ | operador de retardo (*backshift*): $B^k y_t = y_{t-k}$ |
| $\phi_p, \Phi_P$ | polinômios autorregressivos (não-sazonal e sazonal) do SARIMA |
| $\theta_q, \Theta_Q$ | polinômios de médias móveis (não-sazonal e sazonal) do SARIMA |

---

## Formulário matemático

### Interpolação linear

Entre dois pontos consecutivos $(t_i, y_i)$ e $(t_{i+1}, y_{i+1})$:

$$\hat{y}(t) = y_i + \frac{y_{i+1} - y_i}{t_{i+1} - t_i}\,(t - t_i), \qquad t \in [t_i,\, t_{i+1}]$$

Usada também para preencher meses ausentes na série antes das demais etapas.

### Interpolação polinomial (ajuste por mínimos quadrados)

$$\hat{y}(x) = \sum_{j=0}^{d} a_j\,x^{j}, \qquad \mathbf{a} = \arg\min_{\mathbf{a}} \sum_{t=1}^{n}\left(y_t - \sum_{j=0}^{d} a_j\,x_t^{j}\right)^{2}$$

O grau $d$ é escolhido automaticamente em $d \in \{1,\dots,5\}$ pelo **menor RMSE fora da amostra** (holdout de 2024), com empate resolvido pelo menor $d$ — critério anti-overfitting. A equação ajustada é anotada dentro de cada figura de interpolação.

### Qualidade do ajuste ($R^2$ e $R^2$ ajustado)

$$R^{2} = 1 - \frac{\sum_{t}\left(y_t - \hat{y}_t\right)^{2}}{\sum_{t}\left(y_t - \bar{y}\right)^{2}}
\qquad
R^{2}_{aj} = 1 - \left(1 - R^{2}\right)\frac{n-1}{n-d-1}$$

$R^{2}$ nunca diminui ao aumentar $d$; $R^{2}_{aj}$ penaliza a complexidade e expõe o custo de graus altos.

### Médias móveis

Média móvel simples (*trailing*) de janela $w$:

$$MA_w(t) = \frac{1}{w}\sum_{i=0}^{w-1} y_{t-i}$$

Média móvel centrada $2 \times w$ (para $w$ par, como $w = 12$):

$$MA^{c}_{w}(t) = \frac{1}{2}\left(\frac{1}{w}\sum_{i=-w/2}^{w/2-1} y_{t+i} \;+\; \frac{1}{w}\sum_{i=-w/2+1}^{w/2} y_{t+i}\right)$$

### Índice sazonal

Para o mês $m$, sobre o conjunto de anos $A$:

$$S_m = \frac{\bar{y}_m}{\bar{y}}, \qquad \bar{y}_m = \frac{1}{|A|}\sum_{a \in A} y_{a,m}$$

$S_m > 1$ indica mês acima da média anual. Esses índices são a entrada da clusterização de regimes sazonais.

### Clusterização (KMeans e silhouette)

Objetivo do KMeans:

$$\min_{C_1,\dots,C_k}\ \sum_{j=1}^{k}\ \sum_{x \in C_j} \lVert x - \mu_j \rVert_2^{2},
\qquad \mu_j = \frac{1}{|C_j|}\sum_{x \in C_j} x$$

Escolha de $k$ pelo coeficiente de silhueta, com $a(i)$ = distância média intra-cluster e $b(i)$ = menor distância média a outro cluster:

$$s(i) = \frac{b(i) - a(i)}{\max\{a(i),\, b(i)\}}, \qquad s(i) \in [-1, 1]$$

Duas visões: meses agrupados em regimes sazonais (`alta`, `media`, `baixa`) e as 9 séries produto-ano normalizadas por z-score.

### Modelos de previsão

Regressão Ridge (baseline linear regularizado):

$$\min_{\beta}\ \lVert y - X\beta \rVert_2^{2} + \alpha \lVert \beta \rVert_2^{2}$$

Comparada com `RandomForestRegressor` e `GradientBoostingRegressor` (scikit-learn) e com as regressões clássicas descritas abaixo. Todos avaliados por validação temporal `TimeSeriesSplit` no treino (2022–2023) e por backtest no holdout (2024). Matriz de features dos modelos de ML:

$$X_t = \left[\,y_{t-1},\ y_{t-12},\ \mathbb{1}_{\text{mês}=2..12},\ \text{trend}_t,\ \mathbb{1}_{\text{cluster}(m_t)}\,\right]$$

### Regressão linear (equação normal)

Forma matricial, com $x$ = índice do mês:

$$X=\begin{bmatrix}1 & x_1\\\ \vdots & \vdots\\\ 1 & x_n\end{bmatrix}, \qquad \hat{\beta}=\left(X^{\top}X\right)^{-1}X^{\top}y \quad\Longleftrightarrow\quad \left(X^{\top}X\right)\hat{\beta}=X^{\top}y$$

$$\hat{y}(x)=\hat{\beta}_0+\hat{\beta}_1 x$$

Fórmulas de somatório equivalentes (usadas como verificação cruzada da equação normal):

$$\hat{\beta}_1=\frac{n\sum_{t} x_t y_t-\sum_{t} x_t \sum_{t} y_t}{n\sum_{t} x_t^{2}-\left(\sum_{t} x_t\right)^{2}}, \qquad \hat{\beta}_0=\bar{y}-\hat{\beta}_1\bar{x}$$

A implementação resolve $(X^{\top}X)\hat{\beta}=X^{\top}y$ com `numpy.linalg.solve` — nunca invertendo a matriz explicitamente.

### Regressão exponencial

Modelo multiplicativo e sua linearização logarítmica (exige $y_t > 0$):

$$y = a\,e^{b x} \quad\Longrightarrow\quad \ln y = \ln a + b x$$

$$\hat{b}=\frac{n\sum_{t} x_t \ln y_t-\sum_{t} x_t \sum_{t}\ln y_t}{n\sum_{t} x_t^{2}-\left(\sum_{t} x_t\right)^{2}}, \qquad \hat{a}=\exp\!\left(\frac{\sum_{t}\ln y_t-\hat{b}\sum_{t} x_t}{n}\right)$$

A mesma solução é obtida pela equação normal com $z=\ln y$:

$$\hat{\beta}=\left(X^{\top}X\right)^{-1}X^{\top}z, \qquad \hat{a}=e^{\hat{\beta}_0}, \quad \hat{b}=\hat{\beta}_1$$

As duas implementações (somatórios e equação normal) devem coincidir até `1e-9` — igualdade verificada por teste.

### Regressão logística e matriz de confusão

Usada para **classificar o regime do mês** (`alta` vs `não alta`, rótulo vindo do cluster sazonal), não para prever a demanda contínua:

$$P(y=1 \mid x)=\sigma\!\left(\beta^{\top}x\right)=\frac{1}{1+e^{-\beta^{\top}x}}$$

$$\mathcal{L}(\beta)=-\frac{1}{n}\sum_{i=1}^{n}\Big[y_i\ln \hat{p}_i+(1-y_i)\ln\left(1-\hat{p}_i\right)\Big]$$

Avaliação por matriz de confusão:

$$C=\begin{bmatrix} VN & FP\\\ FN & VP \end{bmatrix}$$

$$\text{Acurácia}=\frac{VP+VN}{VP+VN+FP+FN}, \qquad \text{Precisão}=\frac{VP}{VP+FP}, \qquad \text{Recall}=\frac{VP}{VP+FN}$$

$$F_1 = 2\cdot\frac{\text{Precisão}\cdot\text{Recall}}{\text{Precisão}+\text{Recall}}$$

### Previsão recursiva

Para $h$ passos à frente, a previsão realimenta as próprias saídas:

$$\hat{y}_{t+h} = f\!\left(\hat{y}_{t+h-1},\ y_{t+h-12},\ \text{mês}_{t+h},\ \text{trend}_{t+h},\ c_{m(t+h)}\right)$$

O termo $y_{t+h-12}$ usa o valor real enquanto existir; a partir do 13.º passo passa a usar previsões (com aviso de acúmulo de erro).

### Métricas de erro

Avaliadas no holdout de 2024 e publicadas em tabela comparativa por (produto, modelo):

$$\mathrm{MAD} = \frac{1}{n}\sum_{t=1}^{n}\left|y_t - \hat{y}_t\right|$$

$$\mathrm{MSE} = \frac{1}{n}\sum_{t=1}^{n}\left(y_t - \hat{y}_t\right)^{2}
\qquad
\mathrm{RMSE} = \sqrt{\mathrm{MSE}} = \sqrt{\frac{1}{n}\sum_{t=1}^{n}\left(y_t - \hat{y}_t\right)^{2}}$$

$$\mathrm{MAPE} = \frac{100}{|T_0|}\sum_{t \in T_0}\left|\frac{y_t - \hat{y}_t}{y_t}\right|
\qquad
\mathrm{MPE} = \frac{100}{|T_0|}\sum_{t \in T_0}\frac{y_t - \hat{y}_t}{y_t}$$

Quando há $y_t = 0$ no período, esses instantes são excluídos de MAPE e MPE (contados em `n_zeros`) e a linha recebe o erro percentual simétrico:

$$\mathrm{sMAPE} = \frac{100}{n}\sum_{t=1}^{n}\frac{\left|y_t - \hat{y}_t\right|}{\left(\left|y_t\right| + \left|\hat{y}_t\right|\right)/2}$$

**Leitura das métricas**

| Métrica | Unidade | O que mostra |
| --- | --- | --- |
| MAD | unidades | Erro absoluto médio; robusto a outliers |
| MSE | unidades² | Penaliza erros grandes quadraticamente |
| RMSE | unidades | Igual ao MSE, mas na escala original |
| MAPE | % | Erro relativo; comparável entre linhas de escalas diferentes |
| MPE | % | **Viés**: positivo ⇒ subestimação sistemática; negativo ⇒ superestimação |

Critério de escolha do modelo: menor MAPE de holdout; empates dentro de 0,5 p.p. são desempatados pelo menor MAD.

### Comparativo de modelos

Os **6 modelos de previsão** são avaliados sob exatamente as mesmas 5 métricas, no mesmo holdout (2024), e publicados em `reports/tables/error_metrics.csv` e na figura-tabela `17_tabela_erros`:

| Modelo | Chave | Tipo |
| --- | --- | --- |
| Ridge | `ridge` | ML (linear regularizado) |
| Random Forest | `random_forest` | ML (ensemble de árvores) |
| Gradient Boosting | `gradient_boosting` | ML (boosting) |
| Regressão linear (equação normal) | `linear_normal_equation` | Regressão clássica |
| Regressão exponencial (linearizada) | `exponential_loglinear` | Regressão clássica |
| Regressão exponencial (equação normal) | `exponential_normal_equation` | Regressão clássica |

Critério de escolha: menor MAPE de holdout; empates dentro de 0,5 p.p. desempatados pelo menor MAD. O modelo vencedor de cada linha de produto é o que gera a previsão dos próximos anos. Modelos inaplicáveis a uma série (ex.: exponencial com $y_t \le 0$) aparecem na tabela marcados como `not_applicable`.

A classificação logística tem tabela e figura próprias (`regime_classification.csv`, `21_confusao_<produto>`) — métricas de classificação nunca entram no comparativo de erro de previsão.

### Modelos de séries temporais (ciclos periódicos)

Para capturar a forte oscilação periódica anual (picos em janeiro/fevereiro e vales no meio do ano) observada nas curvas de demanda, foram incorporadas três formulações clássicas de séries temporais:

#### Resumo de escolha

| Método | Adequação a N=37 | Captura ciclo anual | Trata amplitude variável | Risco de overfitting |
|---|---|---|---|---|
| **Holt-Winters Multiplicativo** | Alta | Sim ($m=12$) | Sim | Baixo |
| **SARIMA** | Baixa | Sim | Com $\log(y)$ | Alto (perde 12 pts) |
| **Fourier (Regressão Harmônica)** | Alta | Sim ($P=12$) | Não (amplitude fixa) | Muito baixo |

#### Suavização exponencial Holt-Winters Multiplicativo

Modela o nível local $\ell_t$, a taxa de crescimento $b_t$ e as flutuações sazonais multiplicativas $s_t$, sendo ideal para séries em que a amplitude das oscilações é proporcional ao nível médio da demanda (exige $y_t > 0$):

$$\hat{y}_{t+h} = (\ell_t + h b_t)\, s_{t+h-m(k+1)}$$

onde $m = 12$ e $k = \lfloor (h-1)/m \rfloor$. As equações de transição de estado são:

$$\ell_t = \alpha\,\frac{y_t}{s_{t-m}} + (1-\alpha)(\ell_{t-1} + b_{t-1})$$

$$b_t = \beta\,(\ell_t - \ell_{t-1}) + (1-\beta)\,b_{t-1}$$

$$s_t = \gamma\,\frac{y_t}{\ell_t} + (1-\gamma)\,s_{t-m}$$

Os parâmetros de suavização $\alpha, \beta, \gamma \in [0, 1]$ são estimados por máxima verossimilhança minimizando a soma dos erros quadráticos de previsão um passo à frente (SSE).

#### SARIMA (Sazonal Autorregressivo Integrado de Médias Móveis)

Modela dependências estocásticas temporais e sazonais via operadores de retardo $B$ ($B^k y_t = y_{t-k}$):

$$\Phi_P(B^s)\,\phi_p(B)\,(1-B)^d\,(1-B^s)^D y_t = c + \Theta_Q(B^s)\,\theta_q(B)\,\varepsilon_t$$

Para séries curtas ($N=36$, 24 no treino), adota-se a especificação parsimoniosa $\mathrm{SARIMA}(1,0,0)\times(1,0,0)_{12}$:

$$(1 - \phi_1 B)(1 - \Phi_1 B^{12}) y_t = c + \varepsilon_t$$

$$\Longleftrightarrow\quad y_t = c + \phi_1 y_{t-1} + \Phi_1 y_{t-12} - \phi_1 \Phi_1 y_{t-13} + \varepsilon_t$$

> **Diagnóstico de risco amostral:** a diferenciação sazonal ($D=1$) descartaria os primeiros 12 meses da amostra, deixando apenas 12 observações para o treino. Isso causa instabilidade numérica e divergência no estimador MLE em dados sintéticos ou restritos.

#### Fourier (Regressão Harmônica)

Aproximação determinística do ciclo periódico com tendência linear e $K$ pares de harmônicos ortogonais:

$$y(t) = a_0 + b\,t + \sum_{k=1}^{K}\left[ a_k \cos\!\left(\frac{2\pi k\,t}{P}\right) + b_k \sin\!\left(\frac{2\pi k\,t}{P}\right) \right] + \varepsilon_t$$

com $P = 12$ meses e $K = 2$ harmônicos. A estimação é realizada por Mínimos Quadrados Ordinários (equação normal):

$$\mathbf{\hat{\beta}} = \left(X^{\top}X\right)^{-1} X^{\top}\mathbf{y}, \qquad X_t = \left[\,1,\ t,\ \cos\!\left(\frac{2\pi t}{12}\right),\ \sin\!\left(\frac{2\pi t}{12}\right),\ \cos\!\left(\frac{4\pi t}{12}\right),\ \sin\!\left(\frac{4\pi t}{12}\right)\,\right]$$

#### Comparativo de erros das séries temporais (Holdout 2024)

Avaliação idêntica ao backtest dos demais modelos (treino 2022–2023, avaliação nos 12 meses de 2024):

| Produto | Método | MAD | MSE | RMSE | MAPE (%) | MPE (%) | Vencedor |
|---|---|---|---|---|---|---|---|
| **Doce de frutas** | **Holt-Winters Multiplicativo** | **6,10** | **75,7** | **8,70** | **15,53%** | **-2,99%** | **Sim** |
| Doce de frutas | SARIMA $(1,0,0)(1,0,0)_{12}$ | 11,76 | 175,0 | 13,23 | 37,61% | -22,60% | Não |
| Doce de frutas | Fourier (Harmônica $K=2$) | 12,86 | 299,9 | 17,32 | 46,04% | -23,08% | Não |
| **Geleia de frutas** | **Holt-Winters Multiplicativo** | **3,56** | **24,7** | **4,97** | **27,51%** | **-24,78%** | **Sim** |
| Geleia de frutas | SARIMA $(1,0,0)(1,0,0)_{12}$ | 5,01 | 48,5 | 6,97 | 35,36% | -30,12% | Não |
| Geleia de frutas | Fourier (Harmônica $K=2$) | 5,57 | 41,8 | 6,47 | 50,84% | -39,83% | Não |
| **Suco Premium** | **Holt-Winters Multiplicativo** | **6,29** | **49,3** | **7,02** | **11,16%** | **-9,01%** | **Sim** |
| Suco Premium | SARIMA $(1,0,0)(1,0,0)_{12}$ | 8,28 | 85,9 | 9,27 | 16,90% | -16,90% | Não |
| Suco Premium | Fourier (Harmônica $K=2$) | 17,26 | 457,6 | 21,39 | 34,97% | -26,23% | Não |

**Principais conclusões do comparativo:**
1. **Holt-Winters Multiplicativo superou todos os concorrentes de séries temporais** em todas as três linhas de produto, alcançando o menor MAPE e menor MAD. Em Doce de Frutas, reduziu o MAPE para 15,53% (contra 34,55% do Ridge, melhor modelo anterior). Em Suco Premium, alcançou 11,16% de MAPE com viés baixo (-9,01%).
2. **SARIMA** obteve o segundo lugar em todas as linhas, mas foi limitado pela restrição de amostra (24 meses no treino), apresentando tendência a superestimar a demanda nos períodos de vale (MPE entre -16% e -30%).
3. **Fourier (Harmônica)** capturou a ciclicidade de forma robusta e sem risco de divergência, porém foi prejudicado pela amplitude fixa dos termos senoidais, subestimando os picos mais recentes onde a demanda cresceu (efeito multiplicativo).

#### Modificações no projeto e novos artefatos

- Módulo dedicado: `src/bebibem/timeseries.py`.
- Suporte CLI: `bebibem-forecast --timeseries` executa a modelagem e gera todos os plots.
- Figuras geradas em PNG (300 dpi), SVG e PDF:
  - `reports/figures/{png,svg,pdf}/series_temporais/comparativo_<produto>`: comparação direta das 3 abordagens contra os pontos observados no holdout 2024.
  - `reports/figures/{png,svg,pdf}/series_temporais/metricas_mape`: gráfico de barras comparando MAPE e MAD entre os métodos e produtos.
  - `reports/figures/{png,svg,pdf}/series_temporais/tabela_erros`: tabela renderizada em alta resolução com todas as 5 métricas de erro.
  - `reports/figures/{png,svg,pdf}/series_temporais/previsao_todos`: projeção futura de 2025 para as três linhas com o modelo vencedor (Holt-Winters).
  - `reports/figures/{png,svg,pdf}/{holt_winters_multiplicativo,sarima,fourier_harmonica}/backtest_<produto>`: backtests individuais por método.
- Tabelas CSV em `reports/tables/`: `timeseries_error_metrics.csv`, `timeseries_forecast_monthly.csv`, `timeseries_forecast_annual.csv`.

---

## Abordagem de treinamento e seleção de modelos

O objetivo, conforme a questão 5 do case, é prever a demanda de 2025 das três linhas da loja própria (Suco Premium, Geleia de frutas e Doce de frutas) a partir de 36 observações mensais (2022–2024). Por se tratar de uma série curta e com sazonalidade anual marcada, a validação adotou partição temporal, sem embaralhamento: treino em 2022–2023 e holdout nos 12 meses de 2024. Nos modelos de ML, a previsão do holdout é [recursiva](#previsão-recursiva) — cada mês usa a previsão do mês anterior como defasagem e nenhum valor real de 2024 entra como entrada —, reproduzindo as condições de uma previsão feita para o ano seguinte.

### Candidatos avaliados

Nove candidatos por linha, em dois grupos, todos com semente fixa (42) para reprodutibilidade:

| Grupo | Modelos | Entradas |
| --- | --- | --- |
| ML/regressão clássica | Ridge, Random Forest, Gradient Boosting | `lag_1`, `lag_12`, indicadores de mês, tendência e regime sazonal do mês (KMeans sobre o índice sazonal, $k$ escolhido por silhouette) |
| ML/regressão clássica | Linear (equação normal), exponencial linearizada, exponencial (equação normal) | somente a tendência $x$ |
| Séries temporais | Holt-Winters (tendência aditiva, sazonalidade multiplicativa, $m=12$), $\mathrm{SARIMA}(1,0,0)\times(1,0,0)_{12}$ com constante, Fourier (tendência linear, $K=2$, $P=12$) | a própria série |

### Critério de seleção

Cada candidato é avaliado no holdout de 2024 pelas cinco [métricas de erro](#métricas-de-erro). A escolha segue `bebibem.models.select_best`:

1. **menor MAPE** — erro relativo, independente de escala, lido pela gestão como "erro médio percentual";
2. candidatos até 0,5 p.p. acima do menor MAPE são considerados empatados e desempatados pelo **menor MAD** (erro médio em unidades);
3. persistindo o empate, menor MAPE e, por fim, ordem alfabética do nome do modelo.

$$C = \{\,m : \mathrm{MAPE}_m \le \min_k \mathrm{MAPE}_k + 0{,}5\,\}, \qquad m^{*} = \arg\min_{m \in C} \mathrm{MAD}_m$$

MSE, RMSE e MPE são reportados apenas como diagnóstico e não entram na decisão. A regra é aplicada uma única vez por linha sobre os nove candidatos juntos (`bebibem.models.select_overall_best`), e não dentro de cada grupo: isso impede publicar o vencedor de um grupo quando o outro tem modelo mais preciso — no Doce de frutas, o melhor modelo de ML (Ridge, MAPE 34,55%) era muito inferior ao Holt-Winters (15,53%). O comparativo completo está na figura `previsao/tabela_comparativa_modelos`, com a linha vencedora de cada produto destacada.

### Resultados e previsão 2025

| Linha | Modelo vencedor | Grupo | MAPE holdout 2024 | MAD holdout 2024 | Total previsto 2025 |
| --- | --- | --- | --- | --- | --- |
| Doce de frutas | Holt-Winters multiplicativo | Séries temporais | 15,53% | 6,10 | 523 unidades |
| Geleia de frutas | Random Forest | ML/regressão clássica | 18,70% | 2,89 | 180 unidades |
| Suco Premium | Gradient Boosting | ML/regressão clássica | 9,92% | 5,83 | 814 unidades |

Em nenhuma linha houve candidato dentro de 0,5 p.p. do líder, então o desempate por MAD não foi acionado. Em Doce e Geleia, o vencedor é o mesmo nas cinco métricas (MPE pelo valor absoluto). Após a seleção, o vencedor projeta os 12 meses de 2025 a partir do histórico completo (2022–2024).

> **Nota:** a seleção unificada é aplicada no notebook `notebooks/01_analise_demanda_bebibem.ipynb`, fonte da tabela acima. O CLI `bebibem-forecast` ainda escolhe o vencedor apenas entre os seis modelos de ML/regressão clássica (`select_best` sobre `error_metrics` em `src/bebibem/pipeline.py`); por isso o `forecast_annual.csv` gerado pelo CLI pode divergir desta tabela (ex.: Doce de frutas previsto com `ridge`).

### Limitações

- O holdout tem apenas 12 pontos por linha; diferenças pequenas de erro devem ser lidas com cautela.
- Suco Premium é sensível à métrica: pelo MAPE vence o Gradient Boosting (9,92% contra 11,16%), mas pelo RMSE vence o Holt-Winters (7,02 contra 7,38), que erra menos nos meses de maior desvio.
- Como `build_features` exige `lag_12`, os 12 meses de 2022 não viram linhas de treino dos modelos de ML, o que reduz a base efetiva de aprendizado dessas técnicas.

---

## Como executar

### Pré-requisitos

- Python 3.11 ou superior.
- [uv](https://docs.astral.sh/uv/) para criar o ambiente reprodutível.
- Docker (opcional), apenas para executar as imagens de pipeline ou JupyterLab.
- O pipeline completo lê `data/raw/demanda_loja_propria.csv`; use o CSV de exemplo para validar a instalação.

### Ambiente local

```bash
# instalar dependências de produção e o pacote
uv sync

# pipeline completo (figuras + tabelas + previsão)
uv run bebibem-forecast --input data/raw/demanda_loja_propria.csv --outdir reports

# validação rápida com o CSV de exemplo (saída isolada)
uv run bebibem-forecast --input data/example/demanda_exemplo.csv --outdir reports/example

# variações
uv run bebibem-forecast --horizon-years 2 --poly-degree 3 --formats png,svg
uv run bebibem-forecast --steps plots,interp --outdir /tmp/saida
# com modelos de séries temporais periódicos (Holt-Winters, SARIMA, Fourier)
uv run bebibem-forecast --timeseries --outdir reports

# notebook (instale também o extra opcional)
uv sync --extra notebook
uv run jupyter lab notebooks/01_analise_demanda_bebibem.ipynb
```

### Imagens Docker

O pipeline roda como um processo não-root e grava os artefatos no diretório local
montado em `/app/reports`. A imagem JupyterLab expõe a porta `8888`; defina
`JUPYTER_TOKEN` para uma sessão conhecida ou deixe-o vazio para gerar um token
aleatório no início do container.

```bash
# pipeline (imagem sem dependências de desenvolvimento)
docker build -f docker/pipeline.Dockerfile -t bebibem-pipeline .
docker run --rm \
  -v "$PWD/data:/app/data:ro" \
  -v "$PWD/reports:/app/reports" \
  bebibem-pipeline \
  --input /app/data/raw/demanda_loja_propria.csv \
  --outdir /app/reports

# JupyterLab (imagem com o extra notebook)
docker build -f docker/jupyter.Dockerfile -t bebibem-jupyter .
docker run --rm -p 8888:8888 \
  -e JUPYTER_TOKEN="${JUPYTER_TOKEN:-}" \
  -v "$PWD/data:/app/data:ro" \
  -v "$PWD/notebooks:/app/notebooks" \
  -v "$PWD/reports:/app/reports" \
  bebibem-jupyter
```

---

## Contrato do CSV de entrada

Arquivo esperado em `data/raw/demanda_loja_propria.csv`. Dois layouts são aceitos e normalizados internamente.

**Wide** (mesmo formato da tabela do documento, p. 4):

```csv
produto,ano,jan,fev,mar,abr,mai,jun,jul,ago,set,out,nov,dez
Suco Premium,2022,82,86,28,41,94,26,27,29,26,37,84,105
```

**Long**:

```csv
produto,ano,mes,unidades
Suco Premium,2022,1,82
```

Regras: `unidades` numérico e não negativo; sem duplicidade de (produto, ano, mês); meses ausentes são preenchidos por interpolação linear com aviso. Violações abortam a execução com exit code `2`.

---

## Artefatos gerados

- `reports/figures/{png,svg,pdf}/` — 32 figuras em três formatos, organizadas em subpastas por etapa (`pontos/`, `interpolacao/`, `media_movel/`, `clusters/`, `backtest_comparativo/`, `metricas/`, `regressao_classica/`, `classificacao/`, `previsao/`, `capacidade/`) + `index.csv`. `previsao/` inclui, por linha, a previsão histórico+2025 combinada, um gráfico de barras isolado só com os 12 meses de 2025 e um gráfico de barras com a soma mensal das 3 linhas.
- `reports/tables/` — `demand_tidy.csv`, `interpolation_fit.csv`, `moving_average.csv`, `clustering_months.csv`, `clustering_series.csv`, `cv_metrics.csv`, `error_metrics.csv`, `regression_fit.csv`, `regime_classification.csv`, `forecast_monthly.csv`, `forecast_annual.csv`, `capacity_vs_demand.csv`.
- Resposta da questão 5 do case: `reports/tables/forecast_annual.csv` (total anual previsto por linha de produto, com MAPE e MAD de holdout).

O formulário completo, com o detalhamento de cada componente, está em `.specs/features/previsao-demanda-bebibem/design.md` (seção *Formulário matemático*).
