# Previsão de Demanda BebiBem — Especificação

**Fonte de negócio:** `docs/Case BebiBem - MBM - Acting 2026.pdf` (questão 5 — previsão de demanda da loja própria; questões 1–3 — contexto de capacidade e canais)
**Escopo:** Large
**Status:** Aguardando confirmação do usuário

---

## Problem Statement

O case BebiBem exige uma previsão de demanda para 2025 das três linhas da loja própria (Suco Premium, Geleia de frutas, Doce de frutas) a partir de 36 observações mensais (2022–2024) e, ao mesmo tempo, evidência visual e quantitativa que sustente a resposta. Hoje não existe nenhum artefato executável: os dados estão em tabela dentro de um PDF e qualquer análise seria manual, não reproduzível e sem rastro de método. Precisamos de um projeto Python reproduzível (uv + `pyproject.toml`) que gere, com um comando, os gráficos, as interpolações, a média móvel, a comparação de modelos de ML, a clusterização e a previsão anual por linha — em formatos entregáveis (PNG e vetorial) e executável em container.

## Goals

- [ ] Um comando (`bebibem-forecast`) produz 100% dos artefatos (figuras, tabelas, previsão) a partir do CSV de entrada, sem passo manual.
- [ ] Previsão mensal dos próximos anos (a partir de 2025) e total anual por linha, com tabela comparativa de erro (MAD, MAPE, MSE, RMSE, MPE) sobre o holdout de 2024.
- [ ] Toda figura salva simultaneamente em PNG (300 dpi), SVG e PDF, com bytes estáveis entre execuções (mesma entrada ⇒ mesmo arquivo).
- [ ] Notebook Jupyter narrativo que reproduz a mesma análise chamando as funções da biblioteca (sem lógica duplicada).
- [ ] Duas imagens Docker independentes: `docker/pipeline.Dockerfile` executa o script; `docker/jupyter.Dockerfile` sobe o JupyterLab na 8888.
- [ ] Cobertura de testes ≥ 85% em `src/bebibem`, com teste 1:1 para cada critério de aceite de lógica numérica.

## Out of Scope

| Item | Motivo |
| --- | --- |
| Respostas dissertativas das questões 1, 2, 3 e 4c do case | Entregável textual de consultoria, não software |
| Modelos fora do scikit-learn (SARIMA, Prophet, LSTM) | Stack fixada pelo usuário: numpy, pandas, scikit-learn, matplotlib |
| Dashboard web / API / banco de dados | Entrega é script + notebook + figuras em disco |
| Extração automática da tabela do PDF | Usuário fornecerá o CSV no repositório (decisão do usuário) |
| Previsão por SKU (14 SKUs do portfólio) | Histórico disponível é por linha de produto, não por SKU |
| Otimização de hiperparâmetros (GridSearchCV) | 36 observações por série; risco de overfit maior que o ganho |
| Cálculo de ponto de equilíbrio da linha de soja (questão 4a/4b) | Excluído pelo usuário na definição de escopo |

---

## Assumptions & Open Questions

| Premissa / decisão | Default escolhido | Racional | Confirmado? |
| --- | --- | --- | --- |
| Formato do CSV fornecido pelo usuário | **Mesmo layout do documento**: *wide* (`produto,ano,jan..dez`), transcrição direta da tabela da p. 4; o loader também aceita *long* e normaliza ambos para tidy | Confirmado pelo usuário ("o mesmo para documento") | y |
| Nomes das linhas de produto | `Suco Premium`, `Geleia de frutas`, `Doce de frutas` exatamente como no documento, usados como **rótulos das figuras**; slug ASCII interno | Confirmado pelo usuário | y |
| Grau da interpolação polinomial | Grau escolhido automaticamente em `d ∈ {1,…,5}` pelo menor RMSE em validação temporal (empate ⇒ menor `d`), com R² ajustado reportado; `--poly-degree` força um grau específico | Confirmado pelo usuário: evitar overfitting. Grau alto passa pelos pontos e explode fora deles | y |
| Unidade da loja própria vs. capacidade fabril | **Não** converter: loja própria em *unidades*, capacidade em *caixas/mês*; conversão só com `--units-per-case` | Confirmado pelo usuário | y |
| Horizonte da previsão | **Somente anos futuros**: começa em 2025-01; `--horizon-years` ∈ {1,2,3}, default 1 (12 meses). Nenhum mês histórico é reprevisto fora do backtest de avaliação | Confirmado pelo usuário ("apenas para os próximos anos") | y |
| Partição de avaliação | Treino 2022–2023, holdout 2024 (12 meses); seleção por `TimeSeriesSplit(n_splits=3)` dentro do treino | Confirmado pelo usuário | y |
| Conjunto de métricas de erro | Reportar **MAD, MAPE, MSE, RMSE e MPE** em tabela comparativa por (produto, modelo), em CSV e em figura-tabela; vencedor por menor MAPE, desempate < 0,5 p.p. por menor MAD | Confirmado pelo usuário | y |
| Determinismo | `random_state=42` em todo estimador estocástico; metadados de data suprimidos no `savefig` | Reprodutibilidade testável | y |
| Idioma dos artefatos | PT-BR em títulos, rótulos, README e notebook; código e identificadores em inglês | Confirmado pelo usuário | y |
| Série com < 24 observações | Executa plot, interpolação e média móvel; **pula** ML e clusterização, registra `WARNING` e marca `insufficient_data` | Lag-12 e holdout anual exigem 2 ciclos anuais | y |
| Fórmulas formais | Toda técnica (interpolação, média móvel, índice sazonal, KMeans, silhouette, Ridge, 5 métricas) documentada em LaTeX no `design.md`, replicada no notebook e no README, com símbolos consistentes | Pedido explícito do usuário | y |
| Anotação da equação polinomial | Toda figura de interpolação polinomial exibe a equação ajustada em mathtext (`y = a_d x^d + … + a_0`) com grau e R², gerada por `polynomial_equation_label()` | Pedido explícito do usuário; string determinística permite asserção em teste unitário | y |
| Empacotamento Docker | **Dois Dockerfiles separados** (`docker/pipeline.Dockerfile`, `docker/jupyter.Dockerfile`), mesmo contexto de build e mesmo `.dockerignore` | Pedido explícito do usuário; substitui a proposta inicial de imagem multi-stage única | y |
| Modelos de regressão clássica | Incluir **regressão linear (equação normal)**, **regressão exponencial linearizada** e **regressão exponencial por equação normal** no mesmo comparativo dos modelos de ML, implementados com numpy | Pedido do usuário (arquivos de referência `Regressao_linear.py`, `Regressao_Exponencial.py`, `Regressao_Exponencial Equacao Normal.py`) | y |
| Arquivos de referência do usuário | Não estão neste repositório; as implementações seguem a formulação matemática documentada no `design.md`, não o código-fonte original | Só a lista de nomes foi fornecida; nenhuma leitura do código foi possível | y |
| Regressão logística | Aplicada como **classificador do regime mensal** (`alta` vs `não alta`, rótulo vindo do cluster sazonal), avaliada por **matriz de confusão** + acurácia/precisão/recall/F1 | Previsão de demanda é contínua; logística só faz sentido como classificação de regime (equivalente ao `regrassao log confusion.py` de referência) | y |

**Open questions:** nenhuma — todas resolvidas ou registradas acima. Pendência operacional (não de spec): o CSV real em `data/raw/demanda_loja_propria.csv` será fornecido pelo usuário; até lá o desenvolvimento e os testes usam `data/example/demanda_exemplo.csv` (bloqueia apenas a execução final, T23).

---

## User Stories

### P1: Ingestão e validação do histórico ⭐ MVP

**User Story**: Como analista, quero carregar o histórico de demanda de um CSV e receber erro explícito quando ele estiver malformado, para não gerar previsão sobre dado errado.

**Why P1**: Todo o restante do pipeline depende do dataframe tidy.

**Acceptance Criteria**:

1. WHEN o CSV está no formato *wide* (`produto,ano,jan,fev,...,dez`) THEN o loader SHALL retornar um DataFrame tidy com colunas `produto, ano, mes, data, unidades` e 12 linhas por par (produto, ano).
2. WHEN o CSV está no formato *long* (`produto,ano,mes,unidades`) THEN o loader SHALL retornar o mesmo esquema tidy, com `mes` inteiro 1–12 aceitando também nomes de mês em PT-BR (`jan`, `janeiro`, `Jan`).
3. WHEN falta qualquer coluna obrigatória THEN o pipeline SHALL abortar com exit code `2` e mensagem listando as colunas esperadas e as encontradas.
4. WHEN existe par (`produto`,`ano`,`mes`) duplicado THEN o pipeline SHALL abortar com exit code `2` citando os pares duplicados.
5. WHEN há valor não numérico, negativo ou nulo em `unidades` THEN o pipeline SHALL abortar com exit code `2` identificando produto/ano/mês da ocorrência.
6. WHEN faltam meses no meio da série THEN o loader SHALL inserir a linha ausente com `unidades = NaN` e registrar `WARNING`, deixando o preenchimento para a interpolação linear (DEM-05).
7. WHEN o arquivo de entrada não existe THEN o pipeline SHALL abortar com exit code `2` e mensagem indicando o caminho procurado.

**Independent Test**: `uv run pytest tests/unit/test_io_data.py` cobre os 7 casos com CSVs sintéticos em `tmp_path`.

---

### P1: Gráfico de pontos de cada demanda ⭐ MVP

**User Story**: Como analista, quero ver os pontos observados de cada linha de produto no tempo, para inspecionar sazonalidade e outliers antes de modelar.

**Why P1**: É o entregável visual mínimo pedido ("plot dos pontos de cada demanda").

**Acceptance Criteria**:

1. WHEN o pipeline roda THEN o sistema SHALL gerar uma figura de dispersão por linha de produto (3 figuras) com eixo x temporal mensal 2022-01..2024-12 e marcador em cada observação.
2. WHEN o pipeline roda THEN o sistema SHALL gerar 1 figura combinada com as 3 séries sobrepostas e legenda por produto.
3. WHEN uma observação é `NaN` (mês ausente) THEN a figura SHALL omitir o marcador e não interromper a linha guia com valor interpolado silencioso.
4. WHEN a figura é salva THEN o sistema SHALL produzir os 3 arquivos `reports/figures/png/<nome>.png`, `.../svg/<nome>.svg`, `.../pdf/<nome>.pdf`.

**Independent Test**: executar o pipeline em `--outdir tmp` e verificar existência, extensão e não-vazio dos 16 arquivos (4 figuras × 3 formatos + tabela índice).

---

### P1: Interpolação linear e polinomial ⭐ MVP

**User Story**: Como analista, quero as curvas de interpolação linear e polinomial sobre os pontos, para comparar leitura de tendência local versus tendência suave.

**Why P1**: Requisito explícito do usuário.

**Acceptance Criteria**:

1. WHEN há mês ausente (`NaN`) THEN a interpolação linear SHALL preencher o valor por `numpy.interp` entre vizinhos observados e a série preenchida SHALL ser usada pelas etapas seguintes.
2. WHEN a interpolação linear é avaliada THEN o sistema SHALL produzir a curva em grade densa de 10 pontos por mês e, nos instantes observados, o valor interpolado SHALL ser igual ao observado (tolerância `1e-9`).
3. WHEN `--poly-degree` NÃO é informado THEN o sistema SHALL selecionar o grau `d ∈ {1,…,5}` pelo menor RMSE em validação temporal (holdout 2024), com empate resolvido pelo menor `d`, registrando o grau escolhido e o RMSE de cada candidato em `reports/tables/interpolation_fit.csv`.
4. WHEN o ajuste polinomial roda THEN o sistema SHALL usar `numpy.polynomial.Polynomial.fit` sobre o índice temporal normalizado e reportar coeficientes, R² e **R² ajustado** (`1 − (1−R²)(n−1)/(n−d−1)`) na mesma tabela, evidenciando o custo de graus altos.
5. WHEN `--poly-degree` recebe valor `< 1` ou `> 5` THEN o pipeline SHALL abortar com exit code `2` e mensagem com o intervalo válido; graus acima de 5 são recusados por risco de overfitting.
6. WHEN `polynomial_equation_label(coefs, degree, r2)` é chamada THEN ela SHALL retornar string mathtext determinística no formato `$y = a_d x^{d} + … + a_0$` com coeficientes em 4 algarismos significativos, sinais explícitos (`+`/`−`), notação científica quando `|a| < 1e-3` ou `|a| ≥ 1e4`, seguida de `\n grau = d | R² = 0,xxxx | R²_aj = 0,xxxx`.
7. WHEN a figura de interpolação polinomial é gerada THEN ela SHALL conter um artista `Text` cujo conteúdo é exatamente a string de (6), posicionado dentro dos eixos em caixa com fundo branco semitransparente (`alpha=0,75`) que não sobrepõe pontos observados.
8. WHEN a equação tem mais de 4 termos THEN a anotação SHALL quebrar em linhas a cada 3 termos, mantendo a fórmula legível dentro dos limites dos eixos.
9. WHEN as curvas são plotadas THEN o sistema SHALL gerar, por produto, 1 figura contendo pontos observados + curva linear + curva polinomial + anotação da equação + legenda identificando o grau escolhido e como ele foi escolhido (`auto` ou `--poly-degree`).
10. WHEN a variável da fórmula é interpretada THEN `x` SHALL ser o índice de mês desde o início da série (`x = 0` em 2022-01), declarado no rodapé da figura, junto da forma genérica do modelo ajustado.

**Independent Test**: `tests/unit/test_interpolation.py` — série com buraco conhecido, ponto médio esperado analiticamente; polinômio de grau 1 sobre reta perfeita ⇒ R² = 1 e rótulo `$y = 2,000 x + 1,000$`; figura contém `Text` com o rótulo.

---

### P1: Média móvel ⭐ MVP

**User Story**: Como analista, quero médias móveis de 3 e 12 meses, para separar sazonalidade de tendência.

**Why P1**: Requisito explícito e insumo de leitura de tendência para a previsão.

**Acceptance Criteria**:

1. WHEN a média móvel *trailing* de janela `w` é calculada THEN os primeiros `w-1` pontos SHALL ser `NaN` e o ponto `t` SHALL ser a média das observações `t-w+1..t`.
2. WHEN a média móvel *centrada* de janela par (12) é calculada THEN o sistema SHALL aplicar a média móvel dupla (2×12) para manter alinhamento ao centro do mês.
3. WHEN `--ma-windows` recebe `3,12` (default) THEN o sistema SHALL produzir uma coluna por janela por produto na tabela `reports/tables/moving_average.csv`.
4. WHEN a média móvel é plotada THEN o sistema SHALL gerar, por produto, 1 figura com observações + MA(3) + MA(12).
5. WHEN uma janela é maior que o número de observações THEN o pipeline SHALL abortar com exit code `2` citando janela e tamanho da série.

**Independent Test**: `tests/unit/test_smoothing.py` — série constante ⇒ MA igual à constante após o warm-up; série `[1..12]` com `w=3` ⇒ valores conhecidos.

---

### P1: Comparação de modelos (ML + regressão clássica) e backtest ⭐ MVP

**User Story**: Como analista, quero comparar em uma única tabela os modelos de ML (Ridge, RandomForest, GradientBoosting) e os de regressão clássica (linear por equação normal, exponencial linearizada, exponencial por equação normal), para escolher o de menor erro por linha de produto.

**Why P1**: É a "aplicação de machine learning" pedida e a base numérica da previsão.

**Acceptance Criteria**:

1. WHEN a matriz de features é construída THEN ela SHALL conter: `lag_1`, `lag_12`, dummies de mês (11 colunas, `drop_first`), índice de tendência linear e o rótulo one-hot do cluster sazonal (DEM-12).
2. WHEN há menos de 24 observações na série THEN o sistema SHALL pular ML para essa linha, registrar `WARNING` e marcar `insufficient_data` na tabela de métricas, sem abortar as demais linhas.
3. WHEN a seleção de modelo roda THEN o sistema SHALL avaliar **os 6 modelos** com `TimeSeriesSplit(n_splits=3)` no treino (2022–2023) e registrar **MAD, MSE, RMSE, MAPE e MPE** de cada fold em `reports/tables/cv_metrics.csv`.
4. WHEN o backtest roda THEN o sistema SHALL prever os 12 meses de 2024 sem reutilizar valores reais de 2024 como `lag_1` (previsão recursiva) e gravar `reports/tables/error_metrics.csv` com uma linha por (produto, modelo) e colunas `mad, mse, rmse, mape, mpe, n_zeros, metric_note, vencedor`.
5. WHEN há `y_t = 0` no período avaliado THEN MAPE e MPE SHALL ignorar esses instantes, registrar a contagem em `n_zeros` e o sistema SHALL acrescentar a coluna `smape` para essa linha.
6. WHEN o modelo vencedor é escolhido THEN o critério SHALL ser o menor MAPE de holdout; empates dentro de 0,5 p.p. SHALL ser desempatados pelo menor MAD.
7. WHEN o pipeline é executado duas vezes com a mesma entrada e `--seed 42` THEN as métricas gravadas SHALL ser idênticas até `1e-10`.
8. WHEN o backtest termina THEN o sistema SHALL gerar 1 figura por produto (real 2024 × previsto por modelo), 1 figura de barras de MAPE por modelo × produto e 1 **figura-tabela** com as 5 métricas por (produto, modelo), destacando o vencedor.
9. WHEN a figura-tabela de erros é gerada THEN seu rodapé SHALL exibir, em notação matemática, as fórmulas de MAD, MSE, RMSE, MAPE e MPE usadas no cálculo.
10. WHEN o comparativo é montado THEN `error_metrics.csv` e a figura-tabela SHALL conter uma linha para cada um dos 6 modelos por produto: `ridge`, `random_forest`, `gradient_boosting`, `linear_normal_equation`, `exponential_loglinear`, `exponential_normal_equation`.
11. WHEN um modelo de regressão clássica não pode ser ajustado (ex.: exponencial com `y_t ≤ 0`) THEN o sistema SHALL registrar `WARNING`, marcar `not_applicable` na linha correspondente da tabela e seguir com os demais modelos.
12. WHEN o vencedor é um modelo de regressão clássica THEN a previsão futura (DEM-11) SHALL usar esse modelo, com a mesma regra de truncamento de negativos.

**Independent Test**: `tests/unit/test_models.py` — série sintética linear + sazonal conhecida ⇒ MAPE do Ridge < 5%; vetor com erro constante `+2` ⇒ `MAD = 2`, `MSE = 4`, `RMSE = 2`, `MPE` negativo (viés de superestimação); duas execuções ⇒ métricas idênticas.

---

### P1: Regressão linear e exponencial (formulação clássica) ⭐ MVP

**User Story**: Como analista, quero as regressões linear e exponencial ajustadas explicitamente (somatórios e equação normal), para comparar métodos clássicos de tendência com os modelos de ML sob as mesmas métricas.

**Why P1**: Pedido explícito do usuário; são baselines interpretáveis cuja equação pode ser lida na figura.

**Acceptance Criteria**:

1. WHEN `linear_regression_normal_equation(X, y)` é chamada THEN ela SHALL resolver $\hat{\beta}=(X^\top X)^{-1}X^\top y$ por `numpy.linalg.solve` sobre $X^\top X$ (sem inverter a matriz explicitamente) e devolver coeficientes, $R^2$ e a equação em mathtext.
2. WHEN a série é exatamente linear (`y = 3x + 5`) THEN os coeficientes retornados SHALL ser `[5, 3]` com tolerância `1e-9` e `R² = 1`.
3. WHEN `exponential_regression_loglinear(x, y)` é chamada com `y > 0` THEN ela SHALL ajustar $\ln y = \ln a + b x$ pelas fórmulas de somatório e devolver $a$, $b$, $R^2$ (no espaço log e no espaço original) e a equação `y = a e^{bx}` em mathtext.
4. WHEN `exponential_regression_normal_equation(x, y)` é chamada THEN ela SHALL ajustar o mesmo modelo pela equação normal em forma matricial e os coeficientes SHALL coincidir com os de (3) dentro de `1e-9` — a igualdade das duas formulações é verificada por teste.
5. WHEN algum `y_t ≤ 0` THEN as regressões exponenciais SHALL ser puladas para essa série com `WARNING` e marcadas `not_applicable`, sem abortar o pipeline.
6. WHEN as regressões são plotadas THEN o sistema SHALL gerar, por produto, 1 figura com os pontos observados + reta ajustada + curva exponencial, **com as duas equações anotadas na imagem** (mesmo padrão de DEM-21) e $R^2$ de cada uma.
7. WHEN os coeficientes são gravados THEN `reports/tables/regression_fit.csv` SHALL conter `produto, modelo, coeficientes, r2, equacao, metric_note`.
8. WHEN esses modelos entram no backtest THEN eles SHALL ser avaliados nas mesmas 5 métricas e aparecer no comparativo (DEM-09/DEM-10).

**Independent Test**: `tests/unit/test_regression.py` — reta perfeita ⇒ coeficientes exatos; série `y = 2e^{0,3x}` ⇒ `a ≈ 2`, `b ≈ 0,3` (tol. `1e-6`) pelas duas formulações, que devem coincidir entre si; série com zero ⇒ `not_applicable`.

---

### P2: Regressão logística do regime de demanda + matriz de confusão

**User Story**: Como analista, quero classificar cada mês como regime de demanda `alta` ou `não alta` e ver a matriz de confusão do classificador, para avaliar se o padrão sazonal é separável.

**Why P2**: Complementa a clusterização com uma leitura supervisionada; não bloqueia a resposta da questão 5.

**Acceptance Criteria**:

1. WHEN o rótulo é construído THEN `alta = 1` SHALL corresponder aos meses cujo cluster sazonal é `alta` (DEM-12); os demais meses SHALL receber `0`.
2. WHEN o classificador roda THEN o sistema SHALL usar `LogisticRegression(random_state=42)` sobre features de mês (dummies), tendência e `lag_12`, treinando em 2022–2023 e avaliando em 2024.
3. WHEN a avaliação termina THEN o sistema SHALL gravar `reports/tables/regime_classification.csv` com `produto, acuracia, precisao, recall, f1, vp, vn, fp, fn`.
4. WHEN a matriz de confusão é plotada THEN o sistema SHALL gerar 1 figura por produto com a matriz 2×2 anotada (contagens absolutas) e o rodapé trazendo as fórmulas de acurácia, precisão, recall e F1.
5. WHEN uma classe está ausente no treino ou no teste THEN o sistema SHALL pular a classificação dessa série com `WARNING` e marcar `single_class` na tabela, sem abortar o pipeline.
6. WHEN o classificador é avaliado THEN as métricas de classificação SHALL ficar em tabela e figura **separadas** das métricas de regressão — nunca misturadas no comparativo de erro de previsão.

**Independent Test**: `tests/unit/test_classification.py` — dados linearmente separáveis ⇒ acurácia 1,0 e matriz de confusão diagonal; dataset com classe única ⇒ `single_class` sem exceção.

---

### P1: Previsão dos próximos anos por linha de produto ⭐ MVP

**User Story**: Como gestor da loja própria, quero as unidades previstas para os próximos anos (a partir de 2025), mensal e total anual por linha, para responder à questão 5 do case.

**Why P1**: É a resposta de negócio.

**Acceptance Criteria**:

1. WHEN a previsão roda THEN o sistema SHALL gerar `12 × horizon_years` valores mensais por linha, começando em 2025-01, com o modelo vencedor de cada linha reajustado em todo o histórico (2022–2024).
2. WHEN `--horizon-years` NÃO é informado THEN o default SHALL ser `1` (somente 2025); valores aceitos `{1,2,3}`; fora desse conjunto ⇒ exit code `2`.
3. WHEN a previsão avança THEN o sistema SHALL prever **apenas meses futuros ao histórico** — nenhum mês de 2022–2024 é reprevisto fora do backtest de avaliação.
4. WHEN a previsão recursiva avança THEN `lag_1` SHALL usar a previsão do mês anterior e `lag_12` SHALL usar o valor real de 2024 enquanto existir; a partir do 13º passo `lag_12` SHALL usar previsões e o sistema SHALL registrar `WARNING` de acúmulo de erro.
5. WHEN a previsão termina THEN o sistema SHALL gravar `reports/tables/forecast_monthly.csv` (`produto, ano, mes, unidades_previstas, modelo, mape_holdout`) e `reports/tables/forecast_annual.csv` (`produto, ano, unidades_previstas_total, modelo, mape_holdout, mad_holdout`), com totais anuais inteiros.
6. WHEN qualquer previsão mensal resulta negativa THEN o sistema SHALL truncar em 0 e registrar `WARNING` identificando produto e mês.
7. WHEN a previsão é plotada THEN o sistema SHALL gerar 1 figura por produto com histórico 2022–2024 + previsão futura em estilo distinto e 1 figura combinada com as 3 linhas.

**Independent Test**: rodar o pipeline nos dados do case e conferir que `forecast_annual.csv` tem 3 linhas (1 ano) ou 6/9 (2/3 anos), inteiros positivos, ordem de grandeza coerente com 2024 (±40%) e nenhuma linha com ano ≤ 2024.

---

### P1: Fórmulas formais documentadas ⭐ MVP

**User Story**: Como avaliador do case, quero cada técnica escrita formalmente em notação matemática, para auditar o método sem ler o código.

**Why P1**: Pedido explícito do usuário; é o que torna o entregável defensável academicamente.

**Acceptance Criteria**:

1. WHEN `design.md` é lido THEN a seção **Formulário matemático** SHALL conter, em LaTeX: interpolação linear, ajuste polinomial e R² ajustado, média móvel simples e centrada, índice sazonal, objetivo do KMeans, silhouette, objetivo do Ridge e as 5 métricas (MAD, MSE, RMSE, MAPE, MPE).
2. WHEN o notebook é lido THEN cada etapa SHALL ser precedida por célula markdown com a fórmula correspondente em LaTeX e a definição de cada símbolo.
3. WHEN o README é lido THEN ele SHALL trazer as 5 fórmulas de erro em LaTeX e o link para o formulário completo no `design.md`.
4. WHEN uma fórmula é escrita em qualquer artefato THEN os símbolos SHALL ser consistentes: `y_t` observado, `\hat{y}_t` previsto, `n` observações, `w` janela, `d` grau, `k` clusters.
5. WHEN a figura de interpolação polinomial é gerada THEN além da equação ajustada (DEM-21) o rodapé SHALL trazer a forma genérica do modelo ajustado.
6. WHEN a figura-tabela de erros é gerada THEN o rodapé SHALL trazer as fórmulas das métricas exibidas.

**Independent Test**: `tests/unit/test_formulas.py` — `bebibem.formulas.FORMULAS` contém exatamente as 28 chaves do design (interpolações, R²/R²_aj, médias móveis, índice sazonal, KMeans, silhouette, Ridge, previsão recursiva, 5 métricas + sMAPE, equação normal, modelos linear/exponencial, logística, log-loss, matriz de confusão, acurácia/precisão/recall/F1), todas com string LaTeX não vazia; `test_notebook.py` verifica que cada fórmula usada na análise aparece no notebook.

---

### P1: Clusterização (regimes sazonais e séries) ⭐ MVP

**User Story**: Como analista, quero agrupar meses por regime sazonal e séries produto-ano por comportamento, para explicar a sazonalidade e alimentar o modelo com essa informação.

**Why P1**: Requisito explícito ("clusterização para previsão da demanda") e feature do modelo.

**Acceptance Criteria**:

1. WHEN a clusterização de meses roda THEN o sistema SHALL construir, para cada mês (1–12), o vetor de índices sazonais (média do mês ÷ média anual) das 3 linhas e aplicar `KMeans(random_state=42, n_init=10)`.
2. WHEN `k` não é fixado por `--k-months` THEN o sistema SHALL escolher `k ∈ {2,3,4}` pelo maior *silhouette score* e gravar os scores avaliados em `reports/tables/clustering_months.csv`.
3. WHEN os clusters de meses são rotulados THEN os rótulos SHALL ser reordenados por média decrescente do índice sazonal e nomeados `alta`, `media`, `baixa` (para k=3; `alta`/`baixa` para k=2; `alta`/`media_alta`/`media_baixa`/`baixa` para k=4), garantindo rótulo estável entre execuções.
4. WHEN a clusterização de séries roda THEN o sistema SHALL normalizar (z-score) as 9 séries produto-ano de 12 pontos, aplicar `KMeans` com seleção de `k` por silhouette e gravar `reports/tables/clustering_series.csv` com `produto, ano, cluster`.
5. WHEN há menos de 3 amostras para clusterizar THEN o sistema SHALL pular a etapa com `WARNING`, sem abortar o pipeline.
6. WHEN a clusterização termina THEN o sistema SHALL gerar 1 figura de perfis sazonais coloridos por cluster e 1 figura das séries produto-ano coloridas por cluster (com silhouette anotado no título).

**Independent Test**: `tests/unit/test_clustering.py` — dados sintéticos com 2 grupos separados ⇒ `k=2` escolhido, rótulo `alta` atribuído ao grupo de maior índice.

---

### P1: Exportação de figuras em PNG e vetorial ⭐ MVP

**User Story**: Como autor do relatório, quero cada figura em PNG e em formato vetorial, para usar em slide e em documento impresso sem perda.

**Why P1**: Requisito explícito do usuário.

**Acceptance Criteria**:

1. WHEN `save_figure(fig, "01_pontos_suco")` é chamada THEN o sistema SHALL gravar `png/01_pontos_suco.png` (dpi 300), `svg/01_pontos_suco.svg` e `pdf/01_pontos_suco.pdf` sob o diretório de saída configurado.
2. WHEN `--formats png,svg` é passado THEN o sistema SHALL gravar apenas os formatos listados e nenhum outro.
3. WHEN `--formats` recebe formato não suportado THEN o pipeline SHALL abortar com exit code `2` listando os formatos válidos (`png`, `svg`, `pdf`).
4. WHEN a mesma figura é gerada duas vezes com a mesma entrada THEN os arquivos SVG e PDF SHALL ter hash SHA-256 idêntico (metadados de data suprimidos).
5. WHEN o diretório de saída não existe THEN o sistema SHALL criá-lo recursivamente antes de salvar.
6. WHEN o pipeline termina THEN o sistema SHALL gravar `reports/figures/index.csv` com `nome, titulo, formatos, caminho_relativo` de cada figura gerada.

**Independent Test**: `tests/unit/test_plotting.py` — chamar `save_figure` duas vezes em `tmp_path` e comparar hashes; verificar erro para formato inválido.

---

### P1: Script CLI reproduzível ⭐ MVP

**User Story**: Como usuário do repositório, quero rodar `uv run bebibem-forecast` e obter todos os artefatos, para reproduzir a análise sem abrir o notebook.

**Why P1**: É o "script" pedido e o que o Docker executa.

**Acceptance Criteria**:

1. WHEN `uv run bebibem-forecast --help` é executado THEN a saída SHALL listar as flags `--input`, `--outdir`, `--formats`, `--poly-degree`, `--ma-windows`, `--horizon-years`, `--k-months`, `--units-per-case`, `--steps`, `--seed`, `--log-level`.
2. WHEN o comando roda sem flags THEN o sistema SHALL usar `data/raw/demanda_loja_propria.csv` e `reports/` como defaults e terminar com exit code `0`.
3. WHEN `--steps plots,interp` é passado THEN o sistema SHALL executar apenas as etapas listadas, na ordem canônica do pipeline, e nenhum artefato das demais etapas SHALL ser gravado.
4. WHEN uma etapa depende de outra não selecionada (ex.: `ml` sem `features`) THEN o sistema SHALL resolver a dependência automaticamente e registrar `INFO` sobre a inclusão.
5. WHEN o pipeline termina com sucesso THEN a saída SHALL imprimir um resumo com número de figuras, tabelas e o total anual previsto por linha.
6. WHEN ocorre erro de validação de entrada THEN o exit code SHALL ser `2`; erro inesperado SHALL retornar `1` com stack trace apenas em `--log-level debug`.

**Independent Test**: `tests/integration/test_pipeline_e2e.py` — roda o pipeline completo em `tmp_path` com CSV sintético e valida exit code, contagem de arquivos e conteúdo do resumo.

---

### P1: Notebook Jupyter narrativo ⭐ MVP

**User Story**: Como avaliador do case, quero um notebook que conte a análise passo a passo com os gráficos inline, para entender o raciocínio sem ler o código-fonte.

**Why P1**: Requisito explícito do usuário.

**Acceptance Criteria**:

1. WHEN o notebook `notebooks/01_analise_demanda_bebibem.ipynb` é executado do topo ao fim THEN todas as células SHALL executar sem exceção.
2. WHEN o notebook executa THEN ele SHALL importar funções de `bebibem.*` e NÃO SHALL redefinir lógica de cálculo (nenhuma função de modelagem declarada em célula).
3. WHEN o notebook executa THEN ele SHALL exibir, em ordem: pontos observados, interpolações, média móvel, clusters, comparação de modelos, backtest 2024 e previsão 2025 com a tabela de totais anuais.
4. WHEN o notebook é versionado THEN ele SHALL ser commitado sem outputs (`execution_count: null`, `outputs: []`) para manter diff legível.
5. WHEN o teste de notebook roda (`pytest --nbmake`) THEN ele SHALL passar usando o CSV de exemplo do repositório.

**Independent Test**: `uv run pytest --nbmake notebooks/01_analise_demanda_bebibem.ipynb`.

---

### P2: Dockerfile do script (pipeline)

**User Story**: Como usuário sem Python local, quero uma imagem que rode apenas o pipeline via CLI, para gerar todos os artefatos em qualquer máquina com Docker.

**Why P2**: Portabilidade — não bloqueia a resposta do case, mas é entregável pedido.

**Acceptance Criteria**:

1. WHEN `docker build -f docker/pipeline.Dockerfile -t bebibem-pipeline .` é executado THEN o build SHALL concluir com sucesso instalando dependências via `uv sync --frozen --no-dev` e SHALL NOT instalar `jupyterlab`, `pytest` ou `ruff`.
2. WHEN `docker run --rm -v $PWD/data:/app/data:ro -v $PWD/reports:/app/reports bebibem-pipeline` é executado THEN o container SHALL executar `bebibem-forecast`, gravar figuras e tabelas no volume montado e sair com código `0`.
3. WHEN argumentos extras são passados (`docker run ... bebibem-pipeline --steps plots --formats png`) THEN eles SHALL ser repassados ao CLI pelo `ENTRYPOINT`, sem necessidade de sobrescrever o comando.
4. WHEN o container roda THEN o processo SHALL executar como usuário não-root (`app`, uid 10001) com `MPLBACKEND=Agg` e `PYTHONUNBUFFERED=1`.
5. WHEN o `uv.lock` não muda entre builds THEN a camada de dependências SHALL ser reaproveitada do cache (dependências instaladas antes de copiar `src/`).
6. WHEN o `.dockerignore` está aplicado THEN o contexto de build SHALL excluir `.venv/`, `reports/`, `.git/`, `__pycache__/`, `.specs/`, `notebooks/` e `docs/`.
7. WHEN a entrada obrigatória não está montada THEN o container SHALL sair com código `2` e a mensagem de validação do loader (mesmo comportamento do host).

**Independent Test**: `docker build -f docker/pipeline.Dockerfile` + `docker run` com CSV de exemplo; conferir arquivos gerados no host e exit code.

---

### P2: Dockerfile do Jupyter Notebook

**User Story**: Como avaliador do case, quero uma imagem que suba o JupyterLab já com o projeto instalado, para abrir o notebook e reexecutar a análise sem configurar ambiente.

**Why P2**: Entregável pedido, independente da imagem do pipeline.

**Acceptance Criteria**:

1. WHEN `docker build -f docker/jupyter.Dockerfile -t bebibem-jupyter .` é executado THEN o build SHALL instalar o extra `notebook` (`uv sync --frozen --extra notebook`) e SHALL NOT instalar `pytest` nem `ruff`.
2. WHEN `docker run -p 8888:8888 -v $PWD/notebooks:/app/notebooks -v $PWD/data:/app/data:ro -v $PWD/reports:/app/reports bebibem-jupyter` é executado THEN o JupyterLab SHALL responder em `http://localhost:8888` com `notebooks/01_analise_demanda_bebibem.ipynb` listado.
3. WHEN o notebook é executado dentro do container THEN todas as células SHALL rodar sem erro e as figuras SHALL ser gravadas em `/app/reports`, visíveis no host pelo volume.
4. WHEN a variável `JUPYTER_TOKEN` está definida THEN o JupyterLab SHALL exigir esse token; WHEN não está definida THEN SHALL gerar token aleatório e imprimi-lo no log (nunca abrir sem autenticação).
5. WHEN o container roda THEN o processo SHALL executar como usuário não-root (`app`, uid 10001), sem `--allow-root`, com `EXPOSE 8888`.
6. WHEN o `HEALTHCHECK` é avaliado THEN ele SHALL consultar `http://localhost:8888/api/status` e reportar `healthy` em até 30 s após a subida.
7. WHEN a imagem é inspecionada THEN o pacote `bebibem` SHALL estar instalado e importável (`python -c "import bebibem"` retorna `0`).

**Independent Test**: `docker build -f docker/jupyter.Dockerfile` + `docker run`; `curl -sf localhost:8888/api/status` retorna 200 e execução do notebook via `jupyter nbconvert --execute` dentro do container conclui sem erro.

---

### P2: Cenário capacidade × demanda (contexto do case)

**User Story**: Como gestor de operações, quero visualizar a capacidade mensal declarada no case (sucos 12.000 → 15.600 caixas, geleias 3.000, doces 5.000) frente ao crescimento da demanda, para contextualizar a previsão da loja própria.

**Why P2**: Enriquece a resposta, mas usa unidades diferentes da série da loja própria.

**Acceptance Criteria**:

1. WHEN o módulo de capacidade roda THEN ele SHALL usar as constantes do case (sucos 12.000 e 15.600 caixas/mês, geleias 3.000, doces 5.000, total pré-expansão 20.000 caixas/mês) declaradas em um único módulo de configuração.
2. WHEN a figura de capacidade é gerada THEN ela SHALL exibir capacidade por linha antes e depois da expansão de 30% dos sucos, em caixas/mês, com anotação do delta de 3.600 caixas.
3. WHEN `--units-per-case` NÃO é informado THEN o sistema SHALL manter unidades e caixas em figuras separadas e NÃO SHALL somar as escalas.
4. WHEN `--units-per-case N` é informado (N > 0) THEN o sistema SHALL converter a previsão da loja própria para caixas equivalentes, gravar `reports/tables/capacity_vs_demand.csv` e anotar o fator usado no título da figura.
5. WHEN `--units-per-case` recebe valor ≤ 0 THEN o pipeline SHALL abortar com exit code `2`.

**Independent Test**: `tests/unit/test_capacity.py` — constantes conferem com o PDF; conversão com `N=12` produz caixas = unidades/12 arredondado para cima.

---

### P3: README e índice de artefatos

**User Story**: Como quem clona o repositório, quero um README com setup, comandos e descrição dos artefatos, para rodar em menos de 5 minutos.

**Why P3**: Documentação — não bloqueia execução.

**Acceptance Criteria**:

1. WHEN o README é lido THEN ele SHALL conter: pré-requisitos, `uv sync`, comando do pipeline, comando do notebook, comandos Docker (runtime e jupyter) e o contrato do CSV de entrada.
2. WHEN o pipeline termina THEN `reports/figures/index.csv` e `reports/tables/` SHALL estar descritos no README com uma linha por artefato.

**Independent Test**: leitura manual + verificação de que cada comando citado existe no `pyproject.toml`/`Dockerfile`.

---

## Edge Cases

- WHEN o CSV tem apenas 1 ano de histórico THEN interpolação, média móvel (janela ≤ n) e plots SHALL rodar; ML e clusterização de meses SHALL ser puladas com `WARNING` e marcadas na tabela de métricas.
- WHEN uma linha de produto tem valor 0 em algum mês THEN MAPE e MPE SHALL ignorar esses instantes (registrando `n_zeros`) e o sistema SHALL acrescentar `smape` na linha, mantendo MAD, MSE e RMSE calculados sobre todos os pontos.
- WHEN o diretório `reports/` já contém artefatos de execução anterior THEN o pipeline SHALL sobrescrever os arquivos de mesmo nome sem apagar arquivos alheios (nenhum `rm -rf` do diretório).
- WHEN o CSV traz um produto extra além dos 3 esperados THEN o pipeline SHALL processá-lo normalmente (o conjunto de produtos é dado, não fixo em código).
- WHEN `--horizon-years` é 2 ou 3 THEN a previsão recursiva SHALL usar previsões como `lag_12` após o primeiro ano e registrar `WARNING` sobre acúmulo de erro, mantendo o MAPE de holdout publicado como referência de confiança.
- WHEN o ambiente não tem display (container) THEN o backend do matplotlib SHALL ser `Agg` sem falhar.
- WHEN o disco de saída é somente-leitura THEN o pipeline SHALL abortar com exit code `2` e mensagem indicando o caminho não gravável.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| DEM-01 | P1: Ingestão — loader wide/long | Design | Pending |
| DEM-02 | P1: Ingestão — validação e exit codes | Design | Pending |
| DEM-03 | P1: Ingestão — meses ausentes/duplicados | Design | Pending |
| DEM-04 | P1: Gráfico de pontos | Design | Pending |
| DEM-05 | P1: Interpolação linear | Design | Pending |
| DEM-06 | P1: Interpolação polinomial | Design | Pending |
| DEM-07 | P1: Média móvel | Design | Pending |
| DEM-08 | P1: Matriz de features | Design | Pending |
| DEM-09 | P1: Comparação Ridge/RF/GB | Design | Pending |
| DEM-10 | P1: Backtest 2024 + métricas | Design | Pending |
| DEM-11 | P1: Previsão 2025 mensal e anual | Design | Pending |
| DEM-12 | P1: Clusterização de meses | Design | Pending |
| DEM-13 | P1: Clusterização de séries produto-ano | Design | Pending |
| DEM-14 | P1: Exportação PNG/SVG/PDF determinística | Design | Pending |
| DEM-15 | P1: CLI e exit codes | Design | Pending |
| DEM-16 | P1: Notebook narrativo | Design | Pending |
| DEM-17 | P2: Dockerfile do script (`docker/pipeline.Dockerfile`) | Design | Pending |
| DEM-18 | P2: Dockerfile do Jupyter (`docker/jupyter.Dockerfile`) | Design | Pending |
| DEM-19 | P2: Cenário capacidade × demanda | Design | Pending |
| DEM-20 | P3: README e índice de artefatos | Design | Pending |
| DEM-21 | P1: Anotação da equação polinomial nas figuras | Design | Pending |
| DEM-22 | P1: Fórmulas formais documentadas | Design | Pending |
| DEM-23 | P1: Regressão linear (equação normal) | Design | Pending |
| DEM-24 | P1: Regressão exponencial (linearizada e equação normal) | Design | Pending |
| DEM-25 | P2: Regressão logística de regime + matriz de confusão | Design | Pending |

**ID format:** `DEM-NN`
**Status values:** Pending → In Design → In Tasks → Implementing → Verified
**Coverage:** 25 requisitos totais; mapeamento para tasks em `tasks.md`.

---

## Success Criteria

- [ ] `uv run bebibem-forecast` termina em exit code `0` e grava 28 figuras × 3 formatos + 13 tabelas CSV.
- [ ] `forecast_annual.csv` responde a questão 5 com um inteiro de unidades por linha de produto, mais MAPE e MAD de holdout.
- [ ] Duas execuções consecutivas produzem SVG/PDF com hash idêntico e métricas idênticas até `1e-10`.
- [ ] `uv run pytest` passa com cobertura ≥ 85% em `src/bebibem`.
- [ ] `docker build -f docker/pipeline.Dockerfile` + `docker run` reproduz os artefatos em máquina sem Python instalado; `docker build -f docker/jupyter.Dockerfile` + `docker run -p 8888:8888` serve o notebook.
- [ ] Toda figura de interpolação polinomial exibe a equação ajustada (`y = …`) com grau e R² legíveis na imagem exportada.
- [ ] Tabela comparativa de erros (MAD, MAPE, MSE, RMSE, MPE) disponível em CSV e como figura-tabela com as fórmulas no rodapé.
- [ ] Todas as fórmulas do formulário matemático aparecem em LaTeX no `design.md`, no notebook e (as de erro) no README, com símbolos consistentes.
- [ ] Notebook executa ponta a ponta via `pytest --nbmake` sem erro.
