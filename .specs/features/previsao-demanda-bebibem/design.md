# Previsão de Demanda BebiBem — Design

**Spec**: `.specs/features/previsao-demanda-bebibem/spec.md`
**Context**: `.specs/features/previsao-demanda-bebibem/context.md`
**Status**: Draft

---

## Architecture Overview

Biblioteca Python com layout `src/`, funções puras por etapa analítica, orquestradas por um pipeline com CLI. O notebook e o container consomem **as mesmas funções** — nenhuma lógica de cálculo vive em notebook ou em Dockerfile.

```mermaid
graph TD
    CSV[data/raw/demanda_loja_propria.csv] --> IO[io_data.load_demand]
    IO --> TIDY[(DataFrame tidy<br/>produto, ano, mes, data, unidades)]
    TIDY --> INTERP[interpolation<br/>linear + polinomial]
    TIDY --> SMOOTH[smoothing<br/>MA 3 / MA 12]
    TIDY --> CLUS[clustering<br/>meses + séries]
    CLUS --> FEAT[features<br/>lags, dummies, tendência, cluster]
    TIDY --> FEAT
    FEAT --> ML[models<br/>Ridge / RF / GB + TimeSeriesSplit]
    ML --> BT[backtest 2024]
    BT --> FC[forecast 2025 recursivo]
    TIDY --> PLOT[plotting.save_figure]
    INTERP --> PLOT
    SMOOTH --> PLOT
    CLUS --> PLOT
    BT --> PLOT
    FC --> PLOT
    FC --> CAP[capacity<br/>caixas/mês do case]
    CAP --> PLOT
    PLOT --> OUT[(reports/figures/{png,svg,pdf})]
    FC --> TAB[(reports/tables/*.csv)]
    PIPE[pipeline.run / CLI bebibem-forecast] -.orquestra.-> IO
    NB[notebooks/01_analise_demanda_bebibem.ipynb] -.importa.-> IO
    D1[docker/pipeline.Dockerfile] -.executa.-> PIPE
    D2[docker/jupyter.Dockerfile] -.serve.-> NB
```

### Abordagens consideradas (Large ⇒ exploração obrigatória)

| Abordagem | Prós | Contras | Veredito |
| --- | --- | --- | --- |
| **A. Biblioteca `src/` + CLI + notebook fino** | Testável por unidade; notebook e Docker reusam o mesmo código; sem duplicação | Mais arquivos que um script único | ✅ **Escolhida** |
| B. Script único `analise.py` + notebook autônomo | Menos arquivos | Lógica duplicada entre script e notebook; teste unitário difícil; viola "notebook sem lógica" | ❌ |
| C. Notebook como fonte da verdade + `nbconvert` para script | Um artefato só | Diff ilegível, teste ruim, CLI derivada frágil | ❌ |

---

## Estrutura de diretórios

```
insper-bebidem/
├── pyproject.toml              # uv, deps, scripts, ruff, pytest, coverage
├── uv.lock
├── README.md
├── .gitignore
├── .dockerignore
├── docker/
│   ├── pipeline.Dockerfile     # DEM-17 — executa o script
│   └── jupyter.Dockerfile      # DEM-18 — serve o notebook
├── data/
│   ├── raw/demanda_loja_propria.csv    # fornecido pelo usuário
│   └── example/demanda_exemplo.csv     # amostra sintética p/ testes e CI
├── docs/Case BebiBem - MBM - Acting 2026.pdf
├── notebooks/01_analise_demanda_bebibem.ipynb
├── reports/
│   ├── figures/{png,svg,pdf}/ + index.csv
│   └── tables/*.csv
├── src/bebibem/
│   ├── __init__.py
│   ├── config.py
│   ├── io_data.py
│   ├── interpolation.py
│   ├── smoothing.py
│   ├── clustering.py
│   ├── features.py
│   ├── models.py
│   ├── forecast.py
│   ├── capacity.py
│   ├── plotting.py
│   ├── figures.py
│   ├── formulas.py
│   ├── regression.py
│   ├── classification.py
│   ├── pipeline.py
│   └── cli.py
└── tests/
    ├── conftest.py
    ├── unit/test_*.py
    └── integration/test_pipeline_e2e.py, test_notebook.py
```

---

## Code Reuse Analysis

Repositório novo (só `docs/`), então o reuso é externo — nada de reimplementar o que a stack já entrega:

| Recurso | Origem | Uso |
| --- | --- | --- |
| `numpy.interp` | numpy | Interpolação linear e preenchimento de mês ausente (DEM-05) |
| `numpy.polynomial.Polynomial.fit` | numpy | Ajuste polinomial estável (domínio normalizado) + coeficientes para a equação (DEM-06/21) |
| `pandas.Series.rolling` | pandas | Média móvel trailing e centrada (DEM-07) |
| `pandas.get_dummies` | pandas | Dummies de mês e one-hot de cluster (DEM-08) |
| `sklearn.linear_model.Ridge`, `ensemble.RandomForestRegressor`, `ensemble.GradientBoostingRegressor` | scikit-learn | Modelos comparados (DEM-09) |
| `sklearn.model_selection.TimeSeriesSplit` | scikit-learn | Validação temporal (DEM-09) |
| `sklearn.metrics` (`mean_absolute_error`, `mean_squared_error`) | scikit-learn | Base de MAD/MSE/RMSE; MAPE, MPE e sMAPE implementados em `models.metrics` (controle de `y_t = 0`) |
| `numpy.linalg.solve` / `lstsq` | numpy | Equação normal das regressões clássicas sem inverter matriz (DEM-23/24) |
| `sklearn.linear_model.LogisticRegression`, `metrics.confusion_matrix`, `metrics.classification_report` | scikit-learn | Classificação do regime mensal e matriz de confusão (DEM-25) |
| `sklearn.cluster.KMeans`, `metrics.silhouette_score`, `preprocessing.StandardScaler` | scikit-learn | Clusterização e escolha de `k` (DEM-12/13) |
| `matplotlib.figure.Figure.savefig` (`metadata=`) | matplotlib | Exportação determinística PNG/SVG/PDF (DEM-14) |
| `matplotlib` mathtext | matplotlib | Renderização da equação na figura (DEM-21) |
| `argparse` | stdlib | CLI (DEM-15) |
| `logging` | stdlib | WARNING/INFO/DEBUG (edge cases) |

**Nada de scipy** — `CubicSpline`/`interp1d` seriam dependência extra fora da stack pedida; `numpy` cobre o necessário.

---

## Components

### `config.py`

- **Purpose**: Constantes do case, defaults do pipeline e caminhos.
- **Interfaces**:
  - `DEFAULT_INPUT: Path` = `data/raw/demanda_loja_propria.csv`
  - `DEFAULT_OUTDIR: Path` = `reports`
  - `FIGURE_FORMATS: tuple[str, ...]` = `("png", "svg", "pdf")`, `PNG_DPI = 300`
  - `SEED = 42`, `MIN_OBS_FOR_ML = 24`, `HOLDOUT_YEAR = 2024`, `FORECAST_YEAR = 2025`
  - `CASE_CAPACITY: dict[str, CapacityLine]` — sucos `12_000 → 15_600`, geleias `3_000`, doces `5_000` caixas/mês
  - `MODEL_SPECS: dict[str, Callable[[], BaseEstimator]]` — hiperparâmetros fixos
- **Dependencies**: stdlib
- **Requisitos**: DEM-19, base de DEM-09/14/15

### `io_data.py`

- **Purpose**: Carregar, normalizar e validar o CSV.
- **Interfaces**:
  - `load_demand(path: Path) -> pd.DataFrame` — detecta layout, normaliza, valida, retorna tidy (`produto, ano, mes, data, unidades`), ordenado por (produto, data)
  - `detect_layout(columns: Sequence[str]) -> Literal["wide", "long"]`
  - `normalize_product(name: str) -> str` — slug interno; `PRODUCT_LABELS` mantém o rótulo original para figuras
  - `validate_frame(df) -> None` — levanta `InputError` (exit 2) com mensagem acionável
  - `fill_missing_months(df) -> pd.DataFrame` — insere meses ausentes com `NaN` + `WARNING`
- **Erros**: `InputError(ValueError)` → CLI mapeia para exit code `2`
- **Requisitos**: DEM-01, DEM-02, DEM-03

### `interpolation.py`

- **Purpose**: Interpolação linear, ajuste polinomial com seleção de grau anti-overfitting e rótulo da equação.
- **Interfaces**:
  - `linear_interpolation(x: np.ndarray, y: np.ndarray, points_per_step: int = 10) -> tuple[np.ndarray, np.ndarray]`
  - `fill_gaps_linear(series: pd.Series) -> pd.Series`
  - `select_degree(x, y, candidates=(1,2,3,4,5), holdout_year=2024) -> DegreeSelection` — ajusta cada grau no treino, mede RMSE no holdout, devolve o menor RMSE (empate ⇒ menor grau) e a tabela completa dos candidatos
  - `polynomial_fit(x, y, degree: int | None = None) -> PolyFitResult` — `degree=None` ⇒ usa `select_degree`; `PolyFitResult(coefs_desc, degree, degree_source, r2, r2_adj, rmse_holdout, candidates, evaluate(x_dense))`; ajuste em domínio normalizado convertido para a base canônica antes de expor coeficientes
  - `polynomial_equation_label(coefs_desc, degree, r2, r2_adj, terms_per_line=3) -> str` — string mathtext determinística (`$y = …$` + `grau = d | R² | R²_aj`), 4 algarismos significativos, sinais explícitos, notação científica fora de `[1e-3, 1e4)`
  - `validate_degree(degree: int) -> None` — aceita `1 ≤ d ≤ 5`; fora disso `InputError`
- **Anti-overfitting**: grau limitado a 5, escolhido por erro fora da amostra (holdout), com `R²_aj` publicado ao lado do `R²` para expor o custo de complexidade.
- **Requisitos**: DEM-05, DEM-06, DEM-21, DEM-22

### `smoothing.py`

- **Purpose**: Médias móveis.
- **Interfaces**:
  - `moving_average(series: pd.Series, window: int, centered: bool = False) -> pd.Series` — janela par centrada usa média dupla (2×w)
  - `moving_average_table(df: pd.DataFrame, windows: Sequence[int]) -> pd.DataFrame`
  - `validate_windows(windows, n_obs) -> None`
- **Requisitos**: DEM-07

### `clustering.py`

- **Purpose**: Regimes sazonais mensais e agrupamento das séries produto-ano.
- **Interfaces**:
  - `seasonal_index_matrix(df) -> pd.DataFrame` — linhas = meses 1..12, colunas = produtos, valor = média do mês ÷ média anual
  - `cluster_months(matrix, k: int | None = None, k_grid=(2,3,4), seed=SEED) -> ClusterResult` — seleção por silhouette; rótulos reordenados por índice decrescente (`alta`/`media`/`baixa`)
  - `cluster_series(df, k=None, k_grid=(2,3,4), seed=SEED) -> ClusterResult` — z-score por série produto-ano (9 amostras × 12 features)
  - `ClusterResult(labels: pd.Series, k: int, silhouette: float, scores: dict[int, float], skipped: bool, reason: str | None)`
- **Requisitos**: DEM-12, DEM-13

### `features.py`

- **Purpose**: Matriz de features supervisionada.
- **Interfaces**:
  - `build_features(df_product: pd.DataFrame, month_clusters: pd.Series) -> pd.DataFrame` — `lag_1`, `lag_12`, `mes_2..mes_12`, `trend`, `cluster_*`
  - `split_train_holdout(X, y, holdout_year: int) -> tuple[...]`
  - `next_row(history: pd.Series, target_date, month_clusters) -> pd.DataFrame` — monta a linha de features para previsão recursiva
- **Requisitos**: DEM-08

### `models.py`

- **Purpose**: Comparação, validação temporal e métricas.
- **Interfaces**:
  - `build_estimators(seed=SEED) -> dict[str, BaseEstimator]` — `Ridge(alpha=1.0)`, `RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=seed)`, `GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=2, random_state=seed)`
  - `cross_validate_temporal(estimator, X, y, n_splits=3) -> pd.DataFrame` — MAD, MSE, RMSE, MAPE e MPE por fold
  - `recursive_backtest(estimator, history, features_fn, horizon) -> pd.Series`
  - `metrics(y_true, y_pred) -> dict[str, float]` — `mad`, `mse`, `rmse`, `mape`, `mpe`, `n_zeros`, `metric_note` e `smape` quando `n_zeros > 0`; MAPE/MPE calculados só em `t` com `y_t ≠ 0`
  - `metrics_table(results) -> pd.DataFrame` — uma linha por (produto, modelo) com as 5 métricas e a coluna `vencedor`
  - `select_best(metrics_by_model: pd.DataFrame) -> str` — menor MAPE; empate < 0,5 p.p. → menor MAD
- **Requisitos**: DEM-09, DEM-10

### `regression.py`

- **Purpose**: Regressões clássicas de tendência (linear e exponencial) em formulação explícita, comparáveis aos modelos de ML (DEM-23, DEM-24).
- **Interfaces**:
  - `linear_regression_normal_equation(X, y) -> RegressionFit` — resolve $(X^\top X)\hat{\beta}=X^\top y$ com `np.linalg.solve`; devolve `coefs`, `r2`, `equation` (mathtext), `predict(x)`
  - `linear_regression_sums(x, y) -> RegressionFit` — mesma reta pelas fórmulas de somatório ($\hat{b}_1=\frac{n\sum xy-\sum x\sum y}{n\sum x^2-(\sum x)^2}$); usada como verificação cruzada
  - `exponential_regression_loglinear(x, y) -> RegressionFit` — OLS sobre $\ln y$; devolve $a$, $b$, `r2_log`, `r2_original`, `equation` = `$y = a e^{bx}$`
  - `exponential_regression_normal_equation(x, y) -> RegressionFit` — mesmo modelo em forma matricial; **teste garante igualdade com `exponential_regression_loglinear` até `1e-9`**
  - `RegressionFit(name, coefs, r2, equation, predict, applicable, note)` — `applicable=False` + `note="not_applicable"` quando há `y_t ≤ 0` (exponencial) ou dados insuficientes
  - `as_estimator(fit) -> BaseEstimator`-like — adapta a regressão ao mesmo protocolo `fit/predict` usado por `models.py`, permitindo o comparativo único
- **Dependências**: numpy (sem scipy); `x` = índice de mês desde o início da série
- **Requisitos**: DEM-23, DEM-24, entra no comparativo de DEM-09/DEM-10

### `classification.py`

- **Purpose**: Regressão logística do regime mensal (`alta` vs `não alta`) com matriz de confusão (DEM-25).
- **Interfaces**:
  - `build_regime_labels(df, month_clusters) -> pd.Series` — `1` quando o mês pertence ao cluster `alta`, senão `0`
  - `fit_regime_classifier(X_train, y_train, seed=SEED) -> LogisticRegression`
  - `evaluate_classifier(model, X_test, y_test) -> ClassificationResult` — `accuracy`, `precision`, `recall`, `f1`, matriz `[[vn, fp], [fn, vp]]`
  - `ClassificationResult(metrics: dict, confusion: np.ndarray, skipped: bool, reason: str | None)` — `skipped=True` com `reason="single_class"` quando falta uma classe
- **Requisitos**: DEM-25

### `forecast.py`

- **Purpose**: Previsão dos anos futuros e tabelas de resposta.
- **Interfaces**:
  - `fit_final(estimator, X_full, y_full) -> BaseEstimator`
  - `forecast_recursive(estimator, history, month_clusters, horizon_years=1, start="2025-01") -> pd.Series` — `12 × horizon_years` passos; `lag_1` = previsão anterior; `lag_12` = real enquanto existir, depois previsão (com `WARNING` de acúmulo); nunca reprevê meses históricos; trunca negativos em 0 com `WARNING`
  - `validate_horizon_years(value: int) -> None` — aceita `{1,2,3}`, senão `InputError`
  - `forecast_tables(forecasts, best_models, holdout_metrics) -> tuple[pd.DataFrame, pd.DataFrame]` — `forecast_monthly` + `forecast_annual` (total inteiro por produto e ano, com `mape_holdout` e `mad_holdout`)
- **Requisitos**: DEM-11

### `capacity.py`

- **Purpose**: Cenário capacidade (caixas/mês) × demanda prevista.
- **Interfaces**:
  - `capacity_frame() -> pd.DataFrame` — antes/depois da expansão, delta de 3.600 caixas
  - `demand_in_cases(forecast_units: pd.DataFrame, units_per_case: int | None) -> pd.DataFrame | None` — `None` quando não informado (escalas não se misturam)
  - `validate_units_per_case(value) -> None`
- **Requisitos**: DEM-19

### `plotting.py`

- **Purpose**: Estilo comum e exportação multi-formato determinística.
- **Interfaces**:
  - `apply_style() -> None` — rcParams fixos (fonte, grid, tamanho, `MPLBACKEND=Agg`)
  - `save_figure(fig, name: str, outdir: Path, formats=("png","svg","pdf"), title: str = "") -> list[Path]` — cria diretórios, `dpi=300` no PNG, `metadata={"Date": None}` (SVG) / `{"CreationDate": None}` (PDF), registra no índice
  - `validate_formats(formats) -> None`
  - `write_figure_index(records, outdir) -> Path`
  - `annotate_equation(ax, label: str) -> Text` — caixa `bbox(facecolor="white", alpha=0.75)` no canto de menor densidade de pontos
- **Requisitos**: DEM-14, DEM-21

### `figures.py`

- **Purpose**: Construção de cada figura do catálogo (uma função por figura, sem I/O de disco além de `save_figure`).
- **Interfaces**: `fig_points_product`, `fig_points_all`, `fig_interpolation`, `fig_moving_average`, `fig_month_clusters`, `fig_series_clusters`, `fig_backtest`, `fig_metrics_bar`, `fig_error_table`, `fig_regression`, `fig_confusion_matrix`, `fig_forecast_product`, `fig_forecast_all`, `fig_capacity`
- **Requisitos**: DEM-04, DEM-06, DEM-07, DEM-10, DEM-11, DEM-12, DEM-13, DEM-19, DEM-21, DEM-22

### `formulas.py`

- **Purpose**: Fonte única das fórmulas em LaTeX/mathtext usadas em figuras, notebook e README (DEM-22).
- **Interfaces**:
  - `FORMULAS: dict[str, str]` — 28 chaves: `linear_interp`, `poly_fit`, `r2`, `r2_adj`, `ma_simple`, `ma_centered`, `seasonal_index`, `kmeans`, `silhouette`, `ridge`, `recursive_forecast`, `mad`, `mse`, `rmse`, `mape`, `mpe`, `smape`, `normal_equation`, `linear_model`, `linear_sums`, `exponential_model`, `exponential_loglinear`, `logistic_sigmoid`, `logloss`, `confusion_matrix`, `accuracy`, `precision_recall`, `f1`
  - `SYMBOLS: dict[str, str]` — glossário (`y_t`, `\hat{y}_t`, `n`, `w`, `d`, `k`, `\beta`, `X`)
  - `metric_footnote(keys: Sequence[str]) -> str` — rodapé mathtext com as fórmulas pedidas, usado por `fig_error_table` e `fig_interpolation`
- **Requisitos**: DEM-22

### `pipeline.py`

- **Purpose**: Orquestração das etapas e escrita dos artefatos.
- **Interfaces**:
  - `PipelineConfig` (dataclass): `input`, `outdir`, `formats`, `poly_degree` (`None` ⇒ automático), `ma_windows`, `horizon_years`, `k_months`, `units_per_case`, `steps`, `seed`, `log_level`
  - `run(config) -> PipelineResult` — `PipelineResult(figures: list[Path], tables: list[Path], annual_forecast: pd.DataFrame, warnings: list[str])`
  - `resolve_steps(requested) -> list[str]` — ordem canônica `load → interp → ma → cluster → features → ml → forecast → capacity → plots`, resolvendo dependências com `INFO`
- **Requisitos**: DEM-15 e integração de todos

### `cli.py`

- **Purpose**: `argparse`, logging, mapeamento de exceção → exit code, resumo final.
- **Interfaces**: `main(argv=None) -> int`; entrypoint `bebibem-forecast`
- **Exit codes**: `0` sucesso; `2` `InputError` (entrada/flag/permissão); `1` inesperado (stack trace só em `--log-level debug`)
- **Requisitos**: DEM-15

---

## Data Models

### DataFrame tidy (contrato interno)

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `produto` | `string` (slug) | `suco_premium`, `geleia_de_frutas`, `doce_de_frutas`, … |
| `produto_label` | `string` | Rótulo original para eixos/legendas |
| `ano` | `int16` | ≥ 1900 |
| `mes` | `int8` | 1–12 |
| `data` | `datetime64[ns]` | Primeiro dia do mês |
| `unidades` | `float64` | ≥ 0 ou `NaN` (mês ausente antes da interpolação) |

### Tabelas de saída (`reports/tables/`)

| Arquivo | Colunas | Requisito |
| --- | --- | --- |
| `demand_tidy.csv` | contrato tidy | DEM-01 |
| `interpolation_fit.csv` | `produto, grau, r2, coef_0..coef_d, equacao` | DEM-06/21 |
| `moving_average.csv` | `produto, data, unidades, ma_3, ma_12` | DEM-07 |
| `clustering_months.csv` | `mes, cluster, rotulo, indice_sazonal_*, k, silhouette` | DEM-12 |
| `clustering_series.csv` | `produto, ano, cluster, k, silhouette` | DEM-13 |
| `cv_metrics.csv` | `produto, modelo, fold, mad, mse, rmse, mape, mpe` (6 modelos) | DEM-09 |
| `error_metrics.csv` | `produto, modelo, mad, mse, rmse, mape, mpe, smape, n_zeros, metric_note, vencedor` (6 modelos) | DEM-10 |
| `forecast_monthly.csv` | `produto, ano, mes, unidades_previstas, modelo, mape_holdout` | DEM-11 |
| `forecast_annual.csv` | `produto, ano, unidades_previstas_total, modelo, mape_holdout, mad_holdout` | DEM-11 |
| `regression_fit.csv` | `produto, modelo, coeficientes, r2, equacao, metric_note` | DEM-23, DEM-24 |
| `regime_classification.csv` | `produto, acuracia, precisao, recall, f1, vp, vn, fp, fn, nota` | DEM-25 |
| `capacity_vs_demand.csv` | `linha, capacidade_antes, capacidade_depois, delta, demanda_caixas` | DEM-19 |

### Catálogo de figuras (nome → conteúdo)

| # | Nome do arquivo | Conteúdo | Requisito |
| --- | --- | --- | --- |
| 01–03 | `01_pontos_<produto>` | Dispersão dos pontos observados por linha | DEM-04 |
| 04 | `04_pontos_todos` | 3 séries sobrepostas | DEM-04 |
| 05–07 | `05_interpolacao_<produto>` | Pontos + linear + polinomial **com equação anotada** | DEM-05/06/21 |
| 08–10 | `08_media_movel_<produto>` | Pontos + MA(3) + MA(12) | DEM-07 |
| 11 | `11_clusters_meses` | Perfis sazonais coloridos por regime + silhouette | DEM-12 |
| 12 | `12_clusters_series` | 9 séries produto-ano coloridas por cluster | DEM-13 |
| 13–15 | `13_backtest_<produto>` | Real 2024 × previsto por modelo | DEM-10 |
| 16 | `16_metricas_mape` | Barras de MAPE por modelo × produto (6 modelos) | DEM-10 |
| 17 | `17_tabela_erros` | Figura-tabela com MAD, MSE, RMSE, MAPE e MPE por (produto, modelo), vencedor destacado, fórmulas no rodapé | DEM-10, DEM-22 |
| 18–20 | `18_regressao_<produto>` | Pontos + reta (equação normal) + curva exponencial, com as duas equações e R² anotados | DEM-23, DEM-24, DEM-21 |
| 21–23 | `21_confusao_<produto>` | Matriz de confusão 2×2 do regime `alta`, com acurácia/precisão/recall/F1 e fórmulas no rodapé | DEM-25 |
| 24–26 | `24_previsao_<produto>` | Histórico 2022–2024 + previsão futura | DEM-11 |
| 27 | `27_previsao_todos` | Previsão das 3 linhas | DEM-11 |
| 28 | `28_capacidade_case` | Capacidade caixas/mês antes/depois | DEM-19 |

Total: 28 figuras × 3 formatos = 84 arquivos + `index.csv`.

---

## Formulário matemático (fonte única — DEM-22)

Símbolos: $y_t$ = demanda observada no instante $t$; $\hat{y}_t$ = previsão; $n$ = nº de observações; $w$ = janela da média móvel; $d$ = grau do polinômio; $k$ = nº de clusters; $T_0=\{t: y_t \neq 0\}$.

**Interpolação linear** entre $(t_i, y_i)$ e $(t_{i+1}, y_{i+1})$:

$$\hat{y}(t) = y_i + \frac{y_{i+1}-y_i}{t_{i+1}-t_i}\,(t-t_i), \qquad t \in [t_i,\, t_{i+1}]$$

**Ajuste polinomial de grau $d$** (mínimos quadrados):

$$\hat{y}(x)=\sum_{j=0}^{d} a_j\,x^{j}, \qquad \mathbf{a}=\arg\min_{\mathbf{a}}\sum_{t=1}^{n}\left(y_t-\sum_{j=0}^{d}a_j\,x_t^{j}\right)^{2}$$

**Qualidade do ajuste** (o $R^2_{aj}$ é o freio de overfitting):

$$R^{2}=1-\frac{\sum_{t}(y_t-\hat{y}_t)^{2}}{\sum_{t}(y_t-\bar{y})^{2}}, \qquad R^{2}_{aj}=1-(1-R^{2})\,\frac{n-1}{n-d-1}$$

**Média móvel simples (trailing) de janela $w$:**

$$MA_w(t)=\frac{1}{w}\sum_{i=0}^{w-1} y_{t-i}$$

**Média móvel centrada $2\times w$ ($w$ par):**

$$MA^{c}_{w}(t)=\frac{1}{2}\left(\frac{1}{w}\sum_{i=-w/2}^{w/2-1} y_{t+i}+\frac{1}{w}\sum_{i=-w/2+1}^{w/2} y_{t+i}\right)$$

**Índice sazonal do mês $m$** (base da clusterização de regimes):

$$S_m=\frac{\bar{y}_m}{\bar{y}}, \qquad \bar{y}_m=\frac{1}{|A|}\sum_{a\in A} y_{a,m}$$

**KMeans** (objetivo) e **silhouette** (escolha de $k$):

$$\min_{C_1,\dots,C_k}\ \sum_{j=1}^{k}\sum_{x\in C_j}\lVert x-\mu_j\rVert_2^{2}, \qquad \mu_j=\frac{1}{|C_j|}\sum_{x\in C_j}x$$

$$s(i)=\frac{b(i)-a(i)}{\max\{a(i),\,b(i)\}}$$

**Ridge** (regressão linear regularizada):

$$\min_{\beta}\ \lVert y-X\beta\rVert_2^{2}+\alpha\lVert\beta\rVert_2^{2}$$

**Previsão recursiva** ($h$ passos à frente):

$$\hat{y}_{t+h}=f\!\left(\hat{y}_{t+h-1},\ y_{t+h-12},\ \text{mês}_{t+h},\ \text{trend}_{t+h},\ c_{m(t+h)}\right)$$

**Métricas de erro** (avaliadas no holdout de 2024):

$$\mathrm{MAD}=\frac{1}{n}\sum_{t=1}^{n}\left|y_t-\hat{y}_t\right| \qquad \mathrm{MSE}=\frac{1}{n}\sum_{t=1}^{n}\left(y_t-\hat{y}_t\right)^{2} \qquad \mathrm{RMSE}=\sqrt{\mathrm{MSE}}$$

$$\mathrm{MAPE}=\frac{100}{|T_0|}\sum_{t\in T_0}\left|\frac{y_t-\hat{y}_t}{y_t}\right| \qquad \mathrm{MPE}=\frac{100}{|T_0|}\sum_{t\in T_0}\frac{y_t-\hat{y}_t}{y_t}$$

$$\mathrm{sMAPE}=\frac{100}{n}\sum_{t=1}^{n}\frac{\left|y_t-\hat{y}_t\right|}{\left(\left|y_t\right|+\left|\hat{y}_t\right|\right)/2} \quad \text{(usada quando } n_{zeros}>0\text{)}$$

Leitura: MAD, MSE e RMSE em unidades (RMSE pune erro grande); MAPE em % (comparável entre linhas de escalas diferentes); MPE em % é **viés** — positivo indica subestimação sistemática, negativo indica superestimação.

**Regressão linear — forma matricial (equação normal):**

$$X=\begin{bmatrix}1 & x_1\\ \vdots & \vdots\\ 1 & x_n\end{bmatrix}, \qquad \hat{\beta}=\left(X^{\top}X\right)^{-1}X^{\top}y \quad\Longleftrightarrow\quad \left(X^{\top}X\right)\hat{\beta}=X^{\top}y$$

$$\hat{y}(x)=\hat{\beta}_0+\hat{\beta}_1 x$$

**Regressão linear — fórmulas de somatório (equivalentes):**

$$\hat{\beta}_1=\frac{n\sum_{t} x_t y_t-\sum_{t} x_t \sum_{t} y_t}{n\sum_{t} x_t^{2}-\left(\sum_{t} x_t\right)^{2}}, \qquad \hat{\beta}_0=\bar{y}-\hat{\beta}_1\bar{x}$$

**Regressão exponencial** (modelo e linearização logarítmica, exige $y_t>0$):

$$y=a\,e^{b x} \quad\Longrightarrow\quad \ln y=\ln a+b x$$

$$\hat{b}=\frac{n\sum_{t} x_t \ln y_t-\sum_{t} x_t \sum_{t}\ln y_t}{n\sum_{t} x_t^{2}-\left(\sum_{t} x_t\right)^{2}}, \qquad \hat{a}=\exp\!\left(\frac{\sum_{t}\ln y_t-\hat{b}\sum_{t} x_t}{n}\right)$$

A mesma solução é obtida pela equação normal com $z=\ln y$: $\hat{\beta}=(X^{\top}X)^{-1}X^{\top}z$ — as duas implementações devem coincidir até `1e-9`.

**Regressão logística** (classificação do regime `alta`):

$$P(y=1\mid x)=\sigma\!\left(\beta^{\top}x\right)=\frac{1}{1+e^{-\beta^{\top}x}}$$

$$\mathcal{L}(\beta)=-\frac{1}{n}\sum_{i=1}^{n}\Big[y_i\ln \hat{p}_i+(1-y_i)\ln\left(1-\hat{p}_i\right)\Big]$$

**Matriz de confusão e métricas de classificação:**

$$C=\begin{bmatrix} VN & FP\\ FN & VP \end{bmatrix}$$

$$\text{Acurácia}=\frac{VP+VN}{VP+VN+FP+FN}, \qquad \text{Precisão}=\frac{VP}{VP+FP}, \qquad \text{Recall}=\frac{VP}{VP+FN}$$

$$F_1=2\cdot\frac{\text{Precisão}\cdot\text{Recall}}{\text{Precisão}+\text{Recall}}$$


---

## Empacotamento

### `pyproject.toml` (esboço)

```toml
[project]
name = "bebibem-demanda"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["numpy>=2.0", "pandas>=2.2", "scikit-learn>=1.5", "matplotlib>=3.9"]

[project.optional-dependencies]
notebook = ["jupyterlab>=4.2", "ipykernel>=6.29"]

[project.scripts]
bebibem-forecast = "bebibem.cli:main"

[dependency-groups]
dev = ["pytest>=8.3", "pytest-cov>=5.0", "ruff>=0.6", "nbmake>=1.5"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/bebibem"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.coverage.report]
fail_under = 85
```

### `docker/pipeline.Dockerfile` (DEM-17 — esboço)

```dockerfile
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project     # camada de deps cacheável
COPY src/ ./src/
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
ENV PATH="/app/.venv/bin:$PATH" MPLBACKEND=Agg PYTHONUNBUFFERED=1
RUN useradd -u 10001 -m app
WORKDIR /app
COPY --from=build --chown=app:app /app/.venv /app/.venv
USER app
ENTRYPOINT ["bebibem-forecast"]
CMD []
```

### `docker/jupyter.Dockerfile` (DEM-18 — esboço)

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv
ENV UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH" MPLBACKEND=Agg PYTHONUNBUFFERED=1
RUN useradd -u 10001 -m app && apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --extra notebook --no-install-project
COPY src/ ./src/
COPY notebooks/ ./notebooks/
RUN uv sync --frozen --no-dev --extra notebook && chown -R app:app /app
USER app
EXPOSE 8888
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s \
  CMD curl -sf http://localhost:8888/api/status || exit 1
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--ServerApp.root_dir=/app"]
```

Token: sem `JUPYTER_TOKEN` definido, o JupyterLab gera token aleatório e o imprime no log (nunca sobe aberto). `--allow-root` é proibido — o processo roda como `app`.

---

## Error Handling Strategy

| Cenário | Tratamento | Impacto ao usuário |
| --- | --- | --- |
| Arquivo de entrada ausente | `InputError` no loader | Exit `2` + caminho procurado |
| Coluna faltante / layout irreconhecível | `InputError` listando esperado × encontrado | Exit `2` |
| Duplicidade (produto, ano, mês) | `InputError` listando os pares | Exit `2` |
| Valor não numérico / negativo / nulo | `InputError` com produto/ano/mês | Exit `2` |
| Mês ausente | Linha `NaN` + `WARNING` → preenchida por interpolação linear | Roda com aviso |
| Flag inválida (`--poly-degree`, `--formats`, `--ma-windows`, `--units-per-case`) | Validação antes de qualquer I/O | Exit `2` com intervalo/valores válidos |
| Série < 24 observações | Pula ML e clusters, marca `insufficient_data` | Demais linhas seguem |
| Silhouette indefinido (< 3 amostras) | Pula clusterização com `WARNING`; features sem one-hot de cluster | Roda com aviso |
| Previsão negativa | Trunca em 0 + `WARNING` (produto, mês) | Roda com aviso |
| Diretório de saída não gravável | `InputError` | Exit `2` |
| Exceção inesperada | Log `ERROR`; stack trace só em `--log-level debug` | Exit `1` |

---

## Risks & Concerns

| Concern | Onde | Impacto | Mitigação |
| --- | --- | --- | --- |
| 36 pontos por série — RF/GB podem overfitar | `models.py` | Métrica de treino ótima e holdout ruim | Holdout 2024 obrigatório; hiperparâmetros rasos (`max_depth=2`, `min_samples_leaf=2`); Ridge como baseline sempre presente |
| Previsão recursiva acumula erro no horizonte | `forecast.py` | Anos 2 e 3 pouco confiáveis | `lag_12` real enquanto disponível; MAPE/MAD de holdout publicados junto da previsão; `--horizon-years` limitado a 3 com `WARNING` a partir do 13º passo |
| CSV do usuário ainda não existe | `data/raw/` | Fase 2 bloqueada sem o arquivo | Loader aceita wide e long; `data/example/demanda_exemplo.csv` sintético destrava testes e CI |
| Determinismo de SVG/PDF (metadados de data) | `plotting.py` | Diff/hash instável quebra o critério de reprodutibilidade | `metadata={"Date": None}`/`{"CreationDate": None}`; teste de hash duplo |
| Sobreposição da caixa da equação sobre os pontos | `plotting.annotate_equation` | Figura ilegível | Escolha do canto por menor densidade de pontos + `alpha=0,75` + quebra a cada 3 termos |
| KMeans com 9 amostras (séries produto-ano) | `clustering.py` | Cluster instável / silhouette baixo | `n_init=10`, `random_state=42`, silhouette publicado na figura e na tabela; etapa pulável sem quebrar o pipeline |
| Unidades (loja própria) × caixas (capacidade) | `capacity.py` | Número agregado falso | Sem conversão por padrão; só com `--units-per-case` explícito, com o fator anotado na figura |
| Notebook duplicar lógica com o tempo | `notebooks/` | Divergência script × notebook | Regra: notebook só chama `bebibem.*`; teste `--nbmake` no CI |
| Imagem Docker inchada | `docker/*.Dockerfile` | Build lento | `--no-dev`; deps antes do código para cache; `.dockerignore` cobrindo `.venv/`, `reports/`, `.git/`, `docs/` |

---

## Tech Decisions

| Decisão | Escolha | Racional |
| --- | --- | --- |
| Layout do pacote | `src/bebibem` + `hatchling` | Evita import acidental do diretório de trabalho; padrão uv |
| Interpolação polinomial | `numpy.polynomial.Polynomial.fit` (domínio normalizado) | Estável numericamente; expõe coeficientes para a equação da figura |
| Sem scipy | numpy + pandas cobrem interp/rolling | Mantém a stack pedida pelo usuário |
| Conjunto de métricas | MAD, MAPE, MSE, RMSE e MPE em tabela comparativa (CSV + figura-tabela); vencedor por MAPE, desempate por MAD | Pedido do usuário; MPE expõe viés que as métricas absolutas escondem |
| Grau do polinômio | Selecionado em `d ∈ {1..5}` por RMSE de holdout, com `R²_aj` reportado | Pedido do usuário: evitar overfitting |
| Horizonte | Somente anos futuros; `--horizon-years ∈ {1,2,3}`, default 1 | Pedido do usuário |
| Regressões clássicas | `linear_normal_equation`, `exponential_loglinear` e `exponential_normal_equation` implementadas em numpy e adaptadas ao protocolo `fit/predict` | Pedido do usuário; entram no mesmo comparativo de 5 métricas sem duplicar código de avaliação |
| Equação normal | Resolver $(X^\top X)\hat\beta = X^\top y$ com `np.linalg.solve`, nunca `np.linalg.inv` | Mesma solução, melhor condicionamento numérico |
| Regressão logística | Usada como classificador do regime `alta` (não como previsor de demanda), avaliada por matriz de confusão | Demanda é contínua; misturar classificação no comparativo de erro seria incorreto |
| Fórmulas | `formulas.py` como fonte única em LaTeX, consumida por figuras, notebook e README | Evita divergência entre documento e código |
| Validação temporal | `TimeSeriesSplit(3)` no treino + holdout 2024 | Evita vazamento temporal com poucos dados |
| Determinismo | `random_state=42` + metadados de data suprimidos | Torna reprodutibilidade testável |
| CLI | `argparse` (stdlib) | Zero dependência extra para 11 flags |
| Dois Dockerfiles | `pipeline` e `jupyter` separados | Pedido do usuário; imagem do script fica sem jupyterlab |

> **Project-level**: registradas em `.specs/STATE.md` como `AD-001` … `AD-007`.
