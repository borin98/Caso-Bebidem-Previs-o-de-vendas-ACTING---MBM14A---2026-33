# Previsão de Demanda BebiBem — Tasks

## Execution Protocol (MANDATORY — do not skip)

Implemente estas tasks com a skill `tlc-spec-driven`: **ative-a pelo nome e siga o fluxo Execute e as Critical Rules.** Não procure arquivos da skill por caminho de filesystem. A skill é a fonte de verdade do fluxo (ciclo por task, delegação a sub-agentes, Verifier, sensor de discriminação).

**Se a skill não puder ser ativada, PARE e avise o usuário — não prossiga sem ela.**

---

**Design**: `.specs/features/previsao-demanda-bebibem/design.md`
**Spec**: `.specs/features/previsao-demanda-bebibem/spec.md`
**Status**: Draft — aguardando aprovação

> **6 fases ⇒ oferta de sub-agentes obrigatória antes do Execute** (um worker por fase, sequencial) + Verifier final automático.
> **Pré-requisito operacional**: `data/raw/demanda_loja_propria.csv` fornecido pelo usuário antes da T23 (as demais tasks usam `data/example/demanda_exemplo.csv`).

---

## Test Coverage Matrix

> Gerada de spec + design. Repositório novo (sem testes existentes): **defaults fortes aplicados**. Guidelines encontradas: nenhuma (`AGENTS.md`, `CONTRIBUTING.md`, configs de teste inexistentes) — confirmar antes do Execute.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Lógica numérica (`io_data`, `interpolation`, `smoothing`, `clustering`, `features`, `models`, `regression`, `classification`, `forecast`, `capacity`, `formulas`) | unit | Todos os ramos; 1:1 com os ACs do spec; todo edge case listado tem teste | `tests/unit/test_<modulo>.py` | `uv run pytest tests/unit -q` |
| Visualização (`plotting`, `figures`) | unit | Contrato observável: arquivos gerados por formato, hash estável entre execuções, presença do artista `Text` da equação, erro para formato inválido | `tests/unit/test_plotting.py`, `tests/unit/test_figures.py` | `uv run pytest tests/unit -q` |
| Orquestração (`pipeline`, `cli`) | integration (e2e) | Caminho feliz + seleção de `--steps` + cada exit code (`0`, `2`) + resumo impresso | `tests/integration/test_pipeline_e2e.py` | `uv run pytest tests/integration -q` |
| Notebook | integration (nbmake) | Executa ponta a ponta sem exceção com o CSV de exemplo | `notebooks/*.ipynb` | `uv run pytest --nbmake notebooks/` |
| Configuração (`config.py`, `pyproject.toml`) | none | Somente gate de build/lint (constantes do case são verificadas em `test_capacity.py`) | — | gate build |
| Containers (`docker/*.Dockerfile`) | smoke | `build` conclui + `run` gera artefatos no volume + exit code correto | — | `docker build -f docker/<nome>.Dockerfile .` + `docker run` |

## Parallelism Assessment

> Gerada de design — confirmar antes do Execute.

| Test Type | Parallel-Safe? | Isolation Model | Evidence |
| --- | --- | --- | --- |
| unit (numérico) | Sim | Funções puras; fixtures em memória; sem I/O global | `tests/unit/*` usa `tmp_path` e DataFrames sintéticos |
| unit (visualização) | Sim | Toda escrita em `tmp_path`; backend `Agg` | `save_figure(..., outdir=tmp_path)` |
| integration (pipeline/cli) | Sim | `--outdir tmp_path` por teste; nenhum estado global | `PipelineConfig.outdir` é parâmetro obrigatório |
| integration (nbmake) | **Não** | Notebook grava em `reports/` do repositório | Caminho fixo no notebook; roda isolado no gate full |
| smoke (docker) | **Não** | Daemon Docker e nomes de imagem compartilhados | `docker build -t` com tag fixa |

## Gate Check Commands

> Gerada de design — confirmar antes do Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | Tasks com testes unitários | `uv run pytest tests/unit -q` |
| Full | Tasks de pipeline/CLI/notebook | `uv run pytest -q` |
| Build | Fim de fase, tasks de config/Docker | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q --cov=src/bebibem --cov-report=term-missing` (falha se cobertura < 85%) |
| Container | Tasks de Dockerfile | `docker build -f docker/pipeline.Dockerfile -t bebibem-pipeline . && docker build -f docker/jupyter.Dockerfile -t bebibem-jupyter .` |

---

## Execution Plan

### Fase 1 — Fundação (sequencial)

```
T1 → T2 → T3 → T4
```

### Fase 2 — Dados e utilidades (paralelo após T4)

```
        ┌→ T5 ──┐
T4 ──── ┼→ T6 ──┼──→ Fase 3
        ├→ T7 ──┤
        ├→ T8 ──┤
        └→ T24 ─┘
```

### Fase 3 — Modelagem (majoritariamente sequencial)

```
T5 → T9 → T10 → T25 → T11 → T12
T5 → T13
T9 → T26
```

### Fase 4 — Figuras (sequencial — mesmo arquivo `figures.py`)

```
T14 → T15 → T16
```

### Fase 5 — Orquestração (sequencial)

```
T17 → T18
```

### Fase 6 — Entrega (paralelo, exceto T23)

```
        ┌→ T19 ─┐
T18 ────┼→ T20 ─┼──→ T23
        ├→ T21 ─┤
        └→ T22 ─┘
```

---

## Task Breakdown

### T1: Inicializar repositório e estrutura de diretórios

**What**: `git init`, `.gitignore` e árvore de diretórios vazia do design.
**Where**: `.gitignore`, `data/{raw,example}/`, `notebooks/`, `reports/{figures,tables}/`, `src/bebibem/`, `tests/{unit,integration}/`, `docker/`
**Depends on**: None
**Requirement**: base de DEM-15/17/18

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `git init` executado e primeiro commit criado
- [ ] `.gitignore` cobre `.venv/`, `__pycache__/`, `reports/figures/`, `reports/tables/`, `*.ipynb_checkpoints`, `.pytest_cache/`, `.ruff_cache/`
- [ ] `data/raw/` e `reports/` versionados com `.gitkeep`
- [ ] `docs/` e `.specs/` preservados intactos

**Tests**: none · **Gate**: build (apenas estrutura)

---

### T2: Configurar projeto uv (`pyproject.toml` + `uv.lock`)

**What**: Manifesto do projeto com dependências, extras, script e configuração de ruff/pytest/coverage; gerar lock.
**Where**: `pyproject.toml`, `uv.lock`
**Depends on**: T1
**Requirement**: DEM-15 (entrypoint), base de DEM-17/18

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `requires-python = ">=3.11"`; deps `numpy`, `pandas`, `scikit-learn`, `matplotlib`
- [ ] Extra `notebook` (`jupyterlab`, `ipykernel`) e grupo `dev` (`pytest`, `pytest-cov`, `ruff`, `nbmake`)
- [ ] `[project.scripts] bebibem-forecast = "bebibem.cli:main"`
- [ ] `hatchling` com `packages = ["src/bebibem"]`; `[tool.coverage.report] fail_under = 85`
- [ ] `uv sync` conclui e `uv.lock` está commitado
- [ ] `uv run python -c "import numpy, pandas, sklearn, matplotlib"` retorna 0

**Tests**: none · **Gate**: build

---

### T3: Módulo de configuração e constantes do case

**What**: `config.py` com defaults do pipeline, seed, formatos, limiares e as constantes de capacidade do PDF.
**Where**: `src/bebibem/config.py`, `src/bebibem/__init__.py`
**Depends on**: T2
**Requirement**: DEM-19 (constantes), suporte a DEM-09/14/15

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] Constantes: `SEED=42`, `PNG_DPI=300`, `FIGURE_FORMATS=("png","svg","pdf")`, `MIN_OBS_FOR_ML=24`, `HOLDOUT_YEAR=2024`, `FORECAST_YEAR=2025`
- [ ] `CASE_CAPACITY` com sucos 12.000 → 15.600, geleias 3.000, doces 5.000 caixas/mês
- [ ] `MODEL_SPECS` declara os 3 estimadores com hiperparâmetros fixos do design
- [ ] Nenhum caminho absoluto hard-coded (tudo relativo à raiz do projeto)

**Tests**: none (constantes verificadas em `test_capacity.py`, T13) · **Gate**: build

---

### T4: Dataset de exemplo para testes e CI

**What**: CSV sintético com 3 produtos × 36 meses (2022–2024), com um mês ausente proposital, para testes e execução sem o CSV real.
**Where**: `data/example/demanda_exemplo.csv`
**Depends on**: T1
**Requirement**: suporte a DEM-01/15/16

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] Layout *wide* (`produto,ano,jan..dez`), 9 linhas (3 produtos × 3 anos)
- [ ] Valores com sazonalidade e tendência plausíveis (mesma ordem de grandeza do case)
- [ ] Exatamente 1 célula vazia (mês ausente) para exercitar o caminho de interpolação
- [ ] Arquivo commitado e referenciado nos testes como fixture

**Tests**: none · **Gate**: build

---

### T5: Loader e validação do CSV [P]

**What**: `io_data.py` — detecção de layout, normalização para tidy, validação com `InputError` e preenchimento de meses ausentes.
**Where**: `src/bebibem/io_data.py`, `tests/unit/test_io_data.py`
**Depends on**: T3, T4
**Requirement**: DEM-01, DEM-02, DEM-03

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `load_demand` retorna tidy (`produto, produto_label, ano, mes, data, unidades`) para layouts wide e long
- [ ] Nomes de mês PT-BR (`jan`, `janeiro`, `Jan`) aceitos no layout long
- [ ] `InputError` para: arquivo ausente, coluna faltante, duplicidade, valor não numérico/negativo/nulo — cada mensagem cita o dado ofensor
- [ ] Mês ausente vira linha `NaN` + `WARNING` (sem abortar)
- [ ] 7 ACs da história "Ingestão" com 1 teste cada (mín. 9 testes, incluindo casos de mensagem de erro)
- [ ] Gate quick passa: `uv run pytest tests/unit -q`

**Tests**: unit · **Gate**: quick

---

### T6: Exportação determinística de figuras [P]

**What**: `plotting.py` — estilo, `save_figure` multi-formato, validação de formatos, índice de figuras e `annotate_equation`.
**Where**: `src/bebibem/plotting.py`, `tests/unit/test_plotting.py`
**Depends on**: T3
**Requirement**: DEM-14, DEM-21 (mecanismo de anotação)

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `save_figure` grava `png` (300 dpi), `svg` e `pdf` em subdiretórios por formato, criando-os quando ausentes
- [ ] Metadados de data suprimidos ⇒ SHA-256 idêntico em duas chamadas com a mesma figura
- [ ] `--formats` restrito ao subconjunto pedido; formato inválido levanta `InputError`
- [ ] `write_figure_index` gera `index.csv` com `nome, titulo, formatos, caminho_relativo`
- [ ] `annotate_equation` insere `Text` com `bbox` semitransparente e devolve o artista
- [ ] 6 ACs da história "Exportação" com 1 teste cada
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T7: Interpolação linear, polinomial (grau anti-overfitting) e rótulo da equação [P]

**What**: `interpolation.py` — `numpy.interp` denso, preenchimento de lacunas, seleção de grau por RMSE de holdout, ajuste polinomial e `polynomial_equation_label`.
**Where**: `src/bebibem/interpolation.py`, `tests/unit/test_interpolation.py`
**Depends on**: T3
**Requirement**: DEM-05, DEM-06, DEM-21

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] Grade densa (10 pontos/mês) e igualdade nos instantes observados (tol. `1e-9`)
- [ ] `fill_gaps_linear` preenche o buraco do dataset de exemplo com o valor analítico esperado
- [ ] `select_degree` percorre `d ∈ {1..5}`, escolhe o menor RMSE de holdout, desempata pelo menor `d` e devolve a tabela de candidatos
- [ ] Série gerada por polinômio de grau 2 + ruído ⇒ grau escolhido ≤ 3 (teste anti-overfitting)
- [ ] `polynomial_fit` devolve coeficientes na base canônica, `r2` e `r2_adj`; `--poly-degree` fora de `[1,5]` levanta `InputError`
- [ ] `polynomial_equation_label` é determinística: reta perfeita grau 1 ⇒ `$y = 2,000 x + 1,000$` + `grau = 1 | R² = 1,0000 | R²_aj = 1,0000`
- [ ] Notação científica aplicada fora de `[1e-3, 1e4)`; quebra de linha a cada 3 termos
- [ ] 10 ACs da história "Interpolação" com 1 teste cada
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T8: Médias móveis [P]

**What**: `smoothing.py` — MA trailing, MA centrada (2×12) e tabela consolidada.
**Where**: `src/bebibem/smoothing.py`, `tests/unit/test_smoothing.py`
**Depends on**: T3
**Requirement**: DEM-07

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `moving_average` com `w=3` sobre `[1..12]` produz a sequência esperada e `w-1` `NaN` iniciais
- [ ] Janela par centrada usa média dupla e mantém alinhamento
- [ ] `moving_average_table` gera coluna por janela por produto
- [ ] Janela > n observações levanta `InputError`
- [ ] 5 ACs da história "Média móvel" com 1 teste cada
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T24: Formulário matemático (`formulas.py`) [P]

**What**: Fonte única das fórmulas em LaTeX/mathtext consumidas por figuras, notebook e README. (Fase 2 — nome fora da sequência por ter sido criada após a numeração inicial.)
**Where**: `src/bebibem/formulas.py`, `tests/unit/test_formulas.py`
**Depends on**: T3
**Requirement**: DEM-22

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `FORMULAS` contém exatamente as 28 chaves do design (17 originais + `normal_equation`, `linear_model`, `linear_sums`, `exponential_model`, `exponential_loglinear`, `logistic_sigmoid`, `logloss`, `confusion_matrix`, `accuracy`, `precision_recall`, `f1`), todas com string LaTeX não vazia
- [ ] `SYMBOLS` define `y_t`, `\hat{y}_t`, `n`, `w`, `d`, `k`
- [ ] `metric_footnote(["mad","mape"])` devolve rodapé mathtext contendo as duas fórmulas, sem quebrar o parser do matplotlib (teste renderiza em figura `Agg`)
- [ ] Fórmulas idênticas às do `design.md` (teste compara com o bloco do documento ou com fixture derivada dele)
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T9: Clusterização de meses e de séries produto-ano

**What**: `clustering.py` — matriz de índices sazonais, KMeans com seleção de `k` por silhouette, rótulos ordenados e clusterização das 9 séries.
**Where**: `src/bebibem/clustering.py`, `tests/unit/test_clustering.py`
**Depends on**: T5
**Requirement**: DEM-12, DEM-13

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `seasonal_index_matrix` gera 12 linhas × N produtos com índice = média do mês ÷ média anual
- [ ] `k` escolhido pelo maior silhouette em `{2,3,4}`; scores registrados no resultado
- [ ] Rótulos reordenados por índice decrescente (`alta`/`media`/`baixa`) — estáveis entre execuções
- [ ] `cluster_series` normaliza z-score as 9 séries e devolve rótulo por (produto, ano)
- [ ] Amostras < 3 ⇒ `skipped=True` com `reason`, sem exceção
- [ ] 6 ACs da história "Clusterização" com 1 teste cada + teste de determinismo (2 execuções, mesmos rótulos)
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T10: Matriz de features supervisionada

**What**: `features.py` — lags, dummies de mês, tendência, one-hot de cluster e montagem da linha futura.
**Where**: `src/bebibem/features.py`, `tests/unit/test_features.py`
**Depends on**: T5, T9
**Requirement**: DEM-08

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] Colunas exatas: `lag_1`, `lag_12`, `mes_2..mes_12`, `trend`, `cluster_*`
- [ ] Linhas sem `lag_12` disponível são descartadas do treino (sem `NaN` na matriz final)
- [ ] `split_train_holdout` separa 2024 sem vazamento (nenhuma linha de 2024 no treino)
- [ ] `next_row` monta features de um mês futuro a partir de histórico + previsões
- [ ] Série < 24 observações ⇒ sinaliza `insufficient_data` sem exceção
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T11: Modelos, validação temporal e tabela de erros (MAD/MSE/RMSE/MAPE/MPE)

**What**: `models.py` — estimadores de ML + adaptadores das regressões clássicas (T25), `TimeSeriesSplit`, as 5 métricas, backtest recursivo, tabela comparativa dos **6 modelos** e escolha do vencedor.
**Where**: `src/bebibem/models.py`, `tests/unit/test_models.py`
**Depends on**: T10
**Requirement**: DEM-09, DEM-10

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] 3 estimadores construídos com `random_state=42` e hiperparâmetros do design
- [ ] `metrics` devolve `mad`, `mse`, `rmse`, `mape`, `mpe` conferidos analiticamente (erro constante `+2` ⇒ `mad=2`, `mse=4`, `rmse=2`)
- [ ] `mpe` mantém o sinal (viés): superestimação ⇒ `mpe < 0`
- [ ] Com `y_t = 0` no vetor, MAPE/MPE ignoram esses instantes, `n_zeros` é preenchido e `smape` é adicionada
- [ ] `cross_validate_temporal` devolve as 5 métricas por fold (3 folds)
- [ ] `recursive_backtest` não usa valor real de 2024 como `lag_1` (teste prova ausência de vazamento)
- [ ] `metrics_table` gera uma linha por (produto, modelo) com as 5 métricas e a coluna `vencedor`
- [ ] `select_best` aplica menor MAPE e desempate por MAD dentro de 0,5 p.p.
- [ ] Determinismo: duas execuções ⇒ métricas idênticas até `1e-10`
- [ ] Série sintética linear+sazonal ⇒ MAPE do Ridge < 5%
- [ ] 9 ACs da história "Comparação de modelos" com 1 teste cada
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T25: Regressões clássicas (`regression.py`)

**What**: Regressão linear por equação normal e por somatórios; regressão exponencial linearizada e por equação normal; adaptador `fit/predict` para o comparativo. (Fase 3 — numeração fora de sequência por ter sido criada depois.)
**Where**: `src/bebibem/regression.py`, `tests/unit/test_regression.py`
**Depends on**: T10
**Requirement**: DEM-23, DEM-24

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `linear_regression_normal_equation` resolve `(XᵀX)β = Xᵀy` com `np.linalg.solve` (nunca `np.linalg.inv`)
- [ ] Reta perfeita `y = 3x + 5` ⇒ coeficientes `[5, 3]` (tol. `1e-9`) e `R² = 1`
- [ ] `linear_regression_sums` devolve os mesmos coeficientes da equação normal (tol. `1e-9`)
- [ ] `exponential_regression_loglinear` sobre `y = 2e^{0,3x}` ⇒ `a ≈ 2`, `b ≈ 0,3` (tol. `1e-6`)
- [ ] `exponential_regression_normal_equation` coincide com a versão linearizada (tol. `1e-9`)
- [ ] `y_t ≤ 0` ⇒ `applicable=False`, `note="not_applicable"`, `WARNING`, sem exceção
- [ ] `RegressionFit.equation` devolve mathtext (`$y = a e^{bx}$` / `$y = \beta_0 + \beta_1 x$`) com 4 algarismos significativos
- [ ] `as_estimator` expõe `fit`/`predict` compatível com o avaliador de `models.py`
- [ ] 8 ACs da história "Regressão linear e exponencial" com 1 teste cada
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T26: Classificação de regime (`classification.py`)

**What**: Regressão logística do regime `alta` vs `não alta` com matriz de confusão e métricas de classificação. (Fase 3 — numeração fora de sequência.)
**Where**: `src/bebibem/classification.py`, `tests/unit/test_classification.py`
**Depends on**: T9, T10
**Requirement**: DEM-25

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `build_regime_labels` marca `1` só nos meses do cluster `alta`
- [ ] `fit_regime_classifier` usa `LogisticRegression(random_state=42)` com treino 2022–2023 e avaliação em 2024
- [ ] `evaluate_classifier` devolve `accuracy`, `precision`, `recall`, `f1` e matriz `[[vn, fp], [fn, vp]]` conferidos em dados separáveis (acurácia 1,0, matriz diagonal)
- [ ] Classe única no treino ou teste ⇒ `skipped=True`, `reason="single_class"`, `WARNING`, sem exceção
- [ ] Métricas de classificação ficam em tabela própria (`regime_classification.csv`), nunca no comparativo de erro de previsão
- [ ] 6 ACs da história "Regressão logística" com 1 teste cada
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T12: Previsão dos anos futuros e tabelas de resposta

**What**: `forecast.py` — reajuste em 2022–2024, previsão recursiva de `12 × horizon_years` passos, truncamento de negativos e tabelas mensal/anual.
**Where**: `src/bebibem/forecast.py`, `tests/unit/test_forecast.py`
**Depends on**: T11
**Requirement**: DEM-11

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `12 × horizon_years` valores mensais por produto a partir de 2025-01, com o modelo vencedor reajustado em todo o histórico
- [ ] `validate_horizon_years` aceita `{1,2,3}` e levanta `InputError` fora disso
- [ ] Nenhum mês ≤ 2024-12 aparece na previsão (teste garante que histórico não é reprevisto)
- [ ] `lag_1` = previsão anterior; `lag_12` = real enquanto disponível, depois previsão, com `WARNING` a partir do 13º passo
- [ ] Previsão negativa truncada em 0 com `WARNING` citando produto e mês
- [ ] `forecast_monthly.csv` e `forecast_annual.csv` com o esquema do design (total anual inteiro por produto e ano, com `mape_holdout` e `mad_holdout`)
- [ ] 7 ACs da história "Previsão dos próximos anos" com 1 teste cada
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T13: Cenário capacidade × demanda [P]

**What**: `capacity.py` — constantes do case em quadro comparativo e conversão opcional unidades→caixas.
**Where**: `src/bebibem/capacity.py`, `tests/unit/test_capacity.py`
**Depends on**: T3, T5
**Requirement**: DEM-19

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `capacity_frame` reproduz 12.000 → 15.600 (delta 3.600), geleias 3.000, doces 5.000 e total pré-expansão 20.000 caixas/mês
- [ ] Sem `--units-per-case`, `demand_in_cases` devolve `None` (escalas não se misturam)
- [ ] Com `N=12`, converte unidades→caixas com arredondamento para cima
- [ ] `N <= 0` levanta `InputError`
- [ ] 5 ACs da história "Capacidade" com 1 teste cada
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T14: Figuras de séries (pontos, interpolação com equação, média móvel)

**What**: `figures.py` — `fig_points_product`, `fig_points_all`, `fig_interpolation` (equação + fórmula genérica no rodapé), `fig_moving_average`.
**Where**: `src/bebibem/figures.py`, `tests/unit/test_figures.py`
**Depends on**: T6, T7, T8, T24
**Requirement**: DEM-04, DEM-05, DEM-06, DEM-07, DEM-21, DEM-22

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] Uma figura de pontos por produto + 1 combinada; `NaN` não gera marcador
- [ ] Rótulos usam os nomes do documento (`Suco Premium`, `Geleia de frutas`, `Doce de frutas`)
- [ ] `fig_interpolation` contém pontos + curva linear + curva polinomial + `Text` idêntico a `polynomial_equation_label(...)`
- [ ] Rodapé declara `x = 0` em 2022-01 e traz a forma genérica do ajuste (`FORMULAS["poly_fit"]`)
- [ ] Legenda cita o grau escolhido e a origem (`auto` ou `--poly-degree`)
- [ ] `fig_moving_average` sobrepõe MA(3) e MA(12) às observações
- [ ] Testes verificam conteúdo dos artistas (número de linhas, texto da equação), não pixels
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T15: Figuras analíticas (clusters, backtest, métricas e tabela de erros)

**What**: `figures.py` — `fig_month_clusters`, `fig_series_clusters`, `fig_backtest`, `fig_metrics_bar`, `fig_error_table`, `fig_regression`, `fig_confusion_matrix`.
**Where**: `src/bebibem/figures.py`, `tests/unit/test_figures.py`
**Depends on**: T14, T9, T11, T25, T26
**Requirement**: DEM-10, DEM-12, DEM-13, DEM-22, DEM-23, DEM-24, DEM-25

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] Perfis sazonais coloridos por regime com silhouette e `k` no título
- [ ] 9 séries produto-ano coloridas por cluster
- [ ] Backtest: real 2024 × previsto por modelo, uma figura por produto
- [ ] Barras de MAPE por modelo × produto, com o vencedor destacado
- [ ] `fig_error_table` renderiza a tabela MAD/MSE/RMSE/MAPE/MPE por (produto, modelo), vencedor destacado, com `metric_footnote` no rodapé
- [ ] Valores da figura-tabela idênticos aos de `error_metrics.csv` (teste compara célula a célula)
- [ ] `fig_regression` mostra pontos + reta (equação normal) + curva exponencial, com as **duas equações e R² anotados** na imagem
- [ ] `fig_confusion_matrix` desenha a matriz 2×2 com contagens absolutas e rodapé com as fórmulas de acurácia, precisão, recall e F1
- [ ] Série com `not_applicable` (exponencial) ⇒ figura gerada só com a reta, com nota explícita
- [ ] Etapa pulada (cluster ausente) não quebra a geração das demais figuras
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T16: Figuras de previsão e capacidade

**What**: `figures.py` — `fig_forecast_product`, `fig_forecast_all`, `fig_capacity`.
**Where**: `src/bebibem/figures.py`, `tests/unit/test_figures.py`
**Depends on**: T15, T12, T13
**Requirement**: DEM-11, DEM-19

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] Histórico 2022–2024 + previsão futura em estilo distinto, por produto e combinada
- [ ] Título/legenda citam o modelo vencedor, o MAPE e o MAD de holdout
- [ ] `fig_capacity` mostra caixas/mês antes e depois com anotação do delta de 3.600
- [ ] Sem `--units-per-case`, unidades e caixas ficam em figuras separadas
- [ ] Catálogo completo (28 figuras) coberto pelas funções de T14–T16
- [ ] Gate quick passa

**Tests**: unit · **Gate**: quick

---

### T17: Orquestração do pipeline

**What**: `pipeline.py` — `PipelineConfig`, `run`, `resolve_steps` e escrita de todas as tabelas.
**Where**: `src/bebibem/pipeline.py`, `tests/integration/test_pipeline_e2e.py`
**Depends on**: T16
**Requirement**: DEM-15 (orquestração), integra DEM-01..DEM-21

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] Ordem canônica `load → interp → ma → cluster → features → ml → forecast → capacity → plots`
- [ ] `resolve_steps` inclui dependências ausentes e registra `INFO`
- [ ] Execução completa no dataset de exemplo grava 28 figuras × formatos + 13 tabelas + `index.csv`
- [ ] Reexecução sobrescreve arquivos homônimos sem apagar arquivos alheios
- [ ] `PipelineResult` expõe figuras, tabelas, previsão anual e avisos
- [ ] Gate full passa: `uv run pytest -q`

**Tests**: integration · **Gate**: full

---

### T18: CLI `bebibem-forecast`

**What**: `cli.py` — flags, logging, mapeamento de erro→exit code e resumo final.
**Where**: `src/bebibem/cli.py`, `tests/integration/test_pipeline_e2e.py`
**Depends on**: T17
**Requirement**: DEM-15

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `--help` lista as 11 flags do spec (incluindo `--horizon-years` e `--poly-degree` opcional)
- [ ] Sem flags usa `data/raw/demanda_loja_propria.csv` e `reports/`; exit `0` no caminho feliz
- [ ] `--steps plots,interp` restringe artefatos gerados
- [ ] `InputError` ⇒ exit `2`; erro inesperado ⇒ exit `1` com stack trace só em `--log-level debug`
- [ ] Resumo final imprime nº de figuras, nº de tabelas e total anual previsto por linha
- [ ] 6 ACs da história "Script CLI" com 1 teste cada
- [ ] Gate full passa

**Tests**: integration · **Gate**: full

---

### T19: Notebook narrativo [P]

**What**: `01_analise_demanda_bebibem.ipynb` — narrativa PT-BR chamando exclusivamente `bebibem.*`.
**Where**: `notebooks/01_analise_demanda_bebibem.ipynb`, `tests/integration/test_notebook.py`
**Depends on**: T18
**Requirement**: DEM-16, DEM-22

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] Seções na ordem: dados → pontos → interpolações (com equação) → média móvel → clusters → comparação de modelos (tabela das 5 métricas) → backtest 2024 → previsão dos próximos anos + tabela anual
- [ ] Cada seção precedida por célula markdown com a fórmula em LaTeX (`bebibem.formulas.FORMULAS`) e o glossário de símbolos
- [ ] Nenhuma função de cálculo definida em célula (só chamadas a `bebibem.*`)
- [ ] Commitado sem outputs (`execution_count: null`, `outputs: []`)
- [ ] `uv run pytest --nbmake notebooks/01_analise_demanda_bebibem.ipynb` passa com o CSV de exemplo
- [ ] Gate full passa

**Tests**: integration (nbmake) · **Gate**: full

---

### T20: Dockerfile do script + `.dockerignore` [P]

**What**: `docker/pipeline.Dockerfile` (build cacheável, usuário não-root, `ENTRYPOINT bebibem-forecast`) e `.dockerignore` compartilhado.
**Where**: `docker/pipeline.Dockerfile`, `.dockerignore`
**Depends on**: T18
**Requirement**: DEM-17

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `docker build -f docker/pipeline.Dockerfile -t bebibem-pipeline .` conclui
- [ ] `docker run --rm -v $PWD/data:/app/data:ro -v $PWD/reports:/app/reports bebibem-pipeline` gera artefatos no host e sai `0`
- [ ] Argumentos extras chegam ao CLI via `ENTRYPOINT`
- [ ] `docker run --rm bebibem-pipeline --input /inexistente.csv` sai `2`
- [ ] Imagem sem `jupyterlab`, `pytest`, `ruff`; processo como uid 10001; `MPLBACKEND=Agg`
- [ ] `.dockerignore` exclui `.venv/`, `reports/`, `.git/`, `__pycache__/`, `.specs/`, `notebooks/`, `docs/`
- [ ] Gate container passa

**Tests**: smoke (docker) · **Gate**: container

---

### T21: Dockerfile do Jupyter [P]

**What**: `docker/jupyter.Dockerfile` — JupyterLab 8888, extra `notebook`, não-root, token e healthcheck.
**Where**: `docker/jupyter.Dockerfile`
**Depends on**: T19
**Requirement**: DEM-18

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `docker build -f docker/jupyter.Dockerfile -t bebibem-jupyter .` conclui com extra `notebook` e sem `pytest`/`ruff`
- [ ] `docker run -p 8888:8888 …` responde em `http://localhost:8888` com o notebook listado
- [ ] `JUPYTER_TOKEN` respeitado; sem a variável, token aleatório aparece no log (nunca aberto)
- [ ] Processo como uid 10001, sem `--allow-root`
- [ ] `HEALTHCHECK` reporta `healthy` em até 30 s
- [ ] Notebook executa dentro do container e grava em `/app/reports` (visível no host)
- [ ] Gate container passa

**Tests**: smoke (docker) · **Gate**: container

---

### T22: README [P]

**What**: Documentação de setup, comandos, contrato do CSV e catálogo de artefatos.
**Where**: `README.md`
**Depends on**: T18
**Requirement**: DEM-20, DEM-22

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] Seções: pré-requisitos, `uv sync`, execução do pipeline, notebook, Docker (duas imagens), contrato do CSV (wide igual ao documento e long), catálogo de figuras e tabelas
- [x] Fórmulas de MAD, MSE, RMSE, MAPE e MPE em LaTeX, com link para o formulário completo do `design.md` — **já entregue**: `README.md` criado com o formulário completo (notação, interpolações, médias móveis, índice sazonal, KMeans/silhouette, Ridge, previsão recursiva, 5 métricas + sMAPE). Resta apenas revisar após a implementação.
- [ ] Todos os comandos citados existem em `pyproject.toml`/`docker/`
- [ ] Resposta da questão 5 explicada (onde ler o total anual previsto e o erro de holdout associado)
- [ ] Gate build passa

**Tests**: none · **Gate**: build

---

### T23: Execução final com o CSV real e conferência dos artefatos

**What**: Rodar o pipeline com `data/raw/demanda_loja_propria.csv` (fornecido pelo usuário), conferir artefatos e registrar a resposta da questão 5.
**Where**: `reports/`, `README.md` (seção de resultados)
**Depends on**: T19, T20, T21, T22
**Requirement**: DEM-11, DEM-20 e validação de ponta a ponta

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [ ] `uv run bebibem-forecast` termina em `0` com o CSV real
- [ ] 28 figuras × 3 formatos presentes e não vazias; `index.csv` consistente
- [ ] `forecast_annual.csv` com 3 linhas (horizonte 1 ano), inteiros positivos, MAPE e MAD de holdout
- [ ] `error_metrics.csv` e a figura-tabela `17_tabela_erros` comparam os **6 modelos** (3 de ML + 3 de regressão clássica) nas 5 métricas, com o vencedor destacado
- [ ] `regression_fit.csv` traz as equações ajustadas e `regime_classification.csv` traz as métricas de classificação
- [ ] Segunda execução ⇒ hashes SVG/PDF idênticos e métricas idênticas
- [ ] `docker run` do pipeline reproduz os mesmos totais anuais
- [ ] Gate build passa (`ruff` + testes + cobertura ≥ 85%)

**Tests**: integration · **Gate**: build

---

## Check 1 — Task Granularity

| Task | Deliverable único? | Veredito |
| --- | --- | --- |
| T1–T4 | estrutura / manifesto / config / fixture | ✅ |
| T5–T8, T24 | um módulo + seus testes cada | ✅ |
| T9–T13, T25, T26 | um módulo + seus testes cada | ✅ |
| T14–T16 | um grupo coeso de figuras no mesmo arquivo, em sequência | ✅ |
| T17–T18 | orquestração e CLI separadas | ✅ |
| T19–T23 | notebook / dockerfile / dockerfile / readme / execução final | ✅ |

## Check 2 — Diagram-Definition Cross-Check

| Task | `Depends on` | Diagrama | Match |
| --- | --- | --- | --- |
| T1 | None | raiz Fase 1 | ✅ |
| T2 | T1 | T1 → T2 | ✅ |
| T3 | T2 | T2 → T3 | ✅ |
| T4 | T1 | Fase 1 (antes da Fase 2) | ✅ |
| T5 | T3, T4 | T4 → T5 | ✅ |
| T6 | T3 | T4 → T6 | ✅ |
| T7 | T3 | T4 → T7 | ✅ |
| T8 | T3 | T4 → T8 | ✅ |
| T24 | T3 | T4 → T24 (Fase 2) | ✅ |
| T9 | T5 | T5 → T9 | ✅ |
| T10 | T5, T9 | T9 → T10 | ✅ |
| T11 | T10 | T10 → T11 | ✅ |
| T12 | T11 | T11 → T12 | ✅ |
| T13 | T3, T5 | T5 → T13 | ✅ |
| T25 | T10 | T10 → T25 → T11 | ✅ |
| T26 | T9, T10 | T9 → T26 | ✅ |
| T14 | T6, T7, T8, T24 | início Fase 4 | ✅ |
| T15 | T14, T9, T11, T25, T26 | T14 → T15 | ✅ |
| T16 | T15, T12, T13 | T15 → T16 | ✅ |
| T17 | T16 | T16 → T17 | ✅ |
| T18 | T17 | T17 → T18 | ✅ |
| T19–T22 | T18 (T21 via T19) | leque da Fase 6 | ✅ |
| T23 | T19–T22 | convergência final | ✅ |

## Check 3 — Test Co-location Validation

| Task | Layer | Matriz exige | Task inclui | Match |
| --- | --- | --- | --- | --- |
| T1, T2, T3, T4 | estrutura/config/fixture | none (gate build) | gate build | ✅ |
| T5, T7, T8, T9, T10, T11, T12, T13, T24, T25, T26 | lógica numérica | unit 1:1 com ACs | testes unit no mesmo task | ✅ |
| T6, T14, T15, T16 | visualização | unit (arquivos, hash, artistas) | testes unit no mesmo task | ✅ |
| T17, T18 | orquestração | integration e2e | `tests/integration/test_pipeline_e2e.py` | ✅ |
| T19 | notebook | integration nbmake | `pytest --nbmake` | ✅ |
| T20, T21 | container | smoke docker | build + run no `Done when` | ✅ |
| T22 | documentação | none | gate build | ✅ |
| T23 | ponta a ponta | integration | execução real + gate build | ✅ |

---

## Rastreabilidade requisito → task

| Requisito | Tasks |
| --- | --- |
| DEM-01, DEM-02, DEM-03 | T5 |
| DEM-04 | T14 |
| DEM-05, DEM-06, DEM-21 | T7, T14 |
| DEM-07 | T8, T14 |
| DEM-08 | T10 |
| DEM-09, DEM-10 | T11, T15 |
| DEM-11 | T12, T16, T23 |
| DEM-12, DEM-13 | T9, T15 |
| DEM-14 | T6 |
| DEM-15 | T2, T17, T18 |
| DEM-16 | T19 |
| DEM-17 | T20 |
| DEM-18 | T21 |
| DEM-19 | T3, T13, T16 |
| DEM-20 | T22 |
| DEM-22 | T24, T14, T15, T19, T22 |
| DEM-23, DEM-24 | T25, T11, T15 |
| DEM-25 | T26, T15 |

**Cobertura:** 25/25 requisitos mapeados; 0 órfãos.

---

## Pendências antes do Execute

1. Confirmar Test Coverage Matrix / Parallelism / Gate commands (repositório novo — defaults fortes aplicados).
2. Confirmar MCPs e skills por task (proposta atual: nenhum MCP; sem skills auxiliares).
3. Entregar `data/raw/demanda_loja_propria.csv` (bloqueia apenas T23).
4. Aceitar (ou recusar) a oferta de sub-agentes: 6 fases ⇒ 1 worker por fase + Verifier final automático.
