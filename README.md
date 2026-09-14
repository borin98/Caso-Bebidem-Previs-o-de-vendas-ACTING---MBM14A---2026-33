# BebiBem — Previsão de Demanda da Loja Própria

Projeto Python (uv + `pyproject.toml`) que analisa o histórico mensal de demanda das três linhas da loja própria BebiBem (Suco Premium, Geleia de frutas, Doce de frutas — 2022 a 2024) e produz plots, interpolações, médias móveis, clusterização, comparação de modelos de machine learning e previsão dos próximos anos.

> **Status:** planejamento aprovado, implementação pendente. Especificação completa em `.specs/features/previsao-demanda-bebibem/` (`spec.md`, `context.md`, `design.md`, `tasks.md`) e decisões de projeto em `.specs/STATE.md`.

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
- [Como será executado](#como-será-executado)
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

---

## Como será executado

Comandos previstos pela especificação (disponíveis após a implementação das tasks em `.specs/features/previsao-demanda-bebibem/tasks.md`):

```bash
# ambiente
uv sync

# pipeline completo (figuras + tabelas + previsão)
uv run bebibem-forecast

# variações
uv run bebibem-forecast --horizon-years 2 --poly-degree 3 --formats png,svg
uv run bebibem-forecast --steps plots,interp --outdir /tmp/saida

# notebook
uv run jupyter lab notebooks/01_analise_demanda_bebibem.ipynb

# containers (imagens separadas)
docker build -f docker/pipeline.Dockerfile -t bebibem-pipeline .
docker run --rm -v "$PWD/data:/app/data:ro" -v "$PWD/reports:/app/reports" bebibem-pipeline

docker build -f docker/jupyter.Dockerfile -t bebibem-jupyter .
docker run --rm -p 8888:8888 -v "$PWD/notebooks:/app/notebooks" -v "$PWD/reports:/app/reports" bebibem-jupyter
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

- `reports/figures/{png,svg,pdf}/` — 28 figuras em três formatos (pontos observados, interpolações com a equação anotada, médias móveis, clusters, backtest, tabela de erros, regressões com equação, matrizes de confusão, previsão, capacidade) + `index.csv`.
- `reports/tables/` — `demand_tidy.csv`, `interpolation_fit.csv`, `moving_average.csv`, `clustering_months.csv`, `clustering_series.csv`, `cv_metrics.csv`, `error_metrics.csv`, `regression_fit.csv`, `regime_classification.csv`, `forecast_monthly.csv`, `forecast_annual.csv`, `capacity_vs_demand.csv`.
- Resposta da questão 5 do case: `reports/tables/forecast_annual.csv` (total anual previsto por linha de produto, com MAPE e MAD de holdout).

O formulário completo, com o detalhamento de cada componente, está em `.specs/features/previsao-demanda-bebibem/design.md` (seção *Formulário matemático*).
