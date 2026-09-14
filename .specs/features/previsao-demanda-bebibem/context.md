# Previsão de Demanda BebiBem — Context

**Gathered:** 2026-09-10
**Spec:** `.specs/features/previsao-demanda-bebibem/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Projeto Python (uv + `pyproject.toml`) que, a partir de um CSV de demanda mensal da loja própria BebiBem (3 linhas de produto, 2022–2024), gera: gráficos dos pontos observados, interpolação linear, interpolação polinomial com a equação anotada na figura, médias móveis, comparação de modelos scikit-learn com backtest, clusterização (meses e séries) e previsão de 2025 — exportando toda figura em PNG + SVG + PDF, com um script CLI, um notebook Jupyter e **dois** Dockerfiles independentes (script e notebook).

---

## Implementation Decisions

### Fonte de dados

- O **usuário fornecerá o CSV** no repositório (`data/raw/demanda_loja_propria.csv`). Não haverá extrator de PDF.
- Layout confirmado: **igual ao documento** — *wide* (`produto,ano,jan..dez`), transcrição direta da tabela da p. 4. O loader também aceita *long* (`produto,ano,mes,unidades`) e normaliza ambos para tidy (`produto, produto_label, ano, mes, data, unidades`).
- Rótulos das figuras usam os nomes do documento: `Suco Premium`, `Geleia de frutas`, `Doce de frutas`.
- Validação falha rápido (exit code `2`) para: arquivo ausente, coluna faltante, duplicidade (produto, ano, mês), valor não numérico/negativo/nulo.
- O PDF permanece em `docs/` apenas como referência de negócio.

### Escopo analítico

- Núcleo: **questão 5** — 3 linhas × 36 meses → previsão mensal e total anual **somente para anos futuros** (2025 em diante, `--horizon-years ∈ {1,2,3}`, default 1).
- Complemento: **dados agregados do case** (capacidade sucos 12.000 → 15.600 caixas/mês, geleias 3.000, doces 5.000, total 20.000 caixas/mês pré-expansão) em módulo próprio de cenário capacidade × demanda.
- **Unidades não se misturam**: loja própria em *unidades*, capacidade em *caixas/mês*. Conversão só com `--units-per-case N` explícito.
- Fora: questões dissertativas (1, 2, 3), break-even da linha de soja (4a/4b), previsão por SKU.

### Modelagem (ML)

- Comparação de três estimadores scikit-learn: `Ridge`, `RandomForestRegressor`, `GradientBoostingRegressor`.
- Features: `lag_1`, `lag_12`, dummies de mês (`drop_first`), índice de tendência linear, one-hot do cluster sazonal.
- Seleção por `TimeSeriesSplit(n_splits=3)` no treino (2022–2023); holdout = 2024 (12 meses) com previsão recursiva.
- **Tabela comparativa de erros com 5 métricas** (confirmado pelo usuário): **MAD, MAPE, MSE, RMSE e MPE**, por (produto, modelo), publicada em `error_metrics.csv` e na figura-tabela `17_tabela_erros` com as fórmulas no rodapé.
- Vencedor por menor MAPE de holdout; empate < 0,5 p.p. desempata por menor MAD. Com `y_t = 0`, MAPE/MPE ignoram esses instantes (`n_zeros`) e a linha ganha `smape`.
- Sem `GridSearchCV` (36 pontos ⇒ overfit maior que ganho). Hiperparâmetros fixos e documentados.
- **Anti-overfitting na interpolação polinomial**: grau escolhido em `d ∈ {1..5}` pelo menor RMSE de holdout (empate ⇒ menor grau), com `R²` e `R² ajustado` reportados; `--poly-degree` força um grau.
- `random_state=42` em tudo que é estocástico; duas execuções ⇒ métricas idênticas.
- **Modelos de regressão clássica** (pedido do usuário): `linear_normal_equation` (equação normal), `exponential_loglinear` (linearização de $y=ae^{bx}$) e `exponential_normal_equation` entram no **mesmo comparativo** dos modelos de ML, com as mesmas 5 métricas e o mesmo holdout; equações anotadas nas figuras.
- **Regressão logística**: classificador do regime mensal (`alta` vs `não alta`) avaliado por matriz de confusão + acurácia/precisão/recall/F1, em tabela e figura separadas — nunca no comparativo de erro de previsão.
- Os arquivos de referência do usuário (`Regressao_linear.py`, `Regressao_Exponencial.py`, `Regressao_Exponencial Equacao Normal.py`, `regrassao log confusion.py`) **não estão neste repositório**; a implementação segue a formulação matemática documentada, não o código original.

### Clusterização (ambas as visões)

- **Meses (regimes sazonais)**: vetor de índices sazonais por mês (média do mês ÷ média anual) das 3 linhas → `KMeans`, `k ∈ {2,3,4}` escolhido por silhouette. Rótulos reordenados por índice sazonal decrescente (`alta`, `media`, `baixa`) para estabilidade. Rótulo entra como feature do modelo.
- **Séries produto-ano**: 9 séries de 12 pontos normalizadas (z-score) → `KMeans` com seleção por silhouette; saída em `clustering_series.csv` + figura.

### Visualização e exportação

- Toda figura passa por `save_figure(fig, nome)` → grava em `reports/figures/{png,svg,pdf}/`.
- PNG a 300 dpi; SVG e PDF vetoriais com metadados de data suprimidos ⇒ hash estável entre execuções.
- `--formats` permite subconjunto; formato inválido aborta com exit `2`.
- `reports/figures/index.csv` cataloga nome, título, formatos e caminho de cada figura.
- **Equação polinomial na imagem** (pedido do usuário): cada figura de interpolação polinomial exibe, em caixa mathtext dentro dos eixos, `y = a_d x^d + … + a_0` com 4 algarismos significativos, mais `grau = d | R² | R²_aj`; `x` = índice do mês desde 2022-01 (declarado no rodapé, junto da forma genérica do modelo). A string vem de `polynomial_equation_label()`, testável isoladamente.
- **Fórmulas formais** (pedido do usuário): `formulas.py` é a fonte única em LaTeX (28 fórmulas) consumida pelo `design.md`, pelo notebook, pelo README e pelos rodapés das figuras de interpolação, de regressão, da tabela de erros e das matrizes de confusão.

### Empacotamento e execução

- Gerenciamento de dependências com **uv** (`pyproject.toml` + `uv.lock`), layout `src/`, entrypoint `bebibem-forecast`.
- Extras: `notebook` (jupyterlab, ipykernel) e grupo `dev` (pytest, pytest-cov, ruff, nbmake).
- **Dois Dockerfiles separados** (decisão do usuário, substitui multi-stage único):
  - `docker/pipeline.Dockerfile` → `ENTRYPOINT ["bebibem-forecast"]`, sem jupyter/dev, usuário não-root, `MPLBACKEND=Agg`;
  - `docker/jupyter.Dockerfile` → JupyterLab na 8888, extra `notebook`, usuário não-root, token via `JUPYTER_TOKEN`, `HEALTHCHECK` em `/api/status`.
- Mesmo contexto de build e `.dockerignore` compartilhado.
- Notebook chama funções de `bebibem.*` — zero lógica de cálculo duplicada — e é versionado sem outputs.

### Agent's Discretion

- Paleta, estilo e tipografia das figuras (desde que legíveis em PNG 300 dpi e nos vetoriais).
- Hiperparâmetros fixos de `RandomForest`/`GradientBoosting` (documentados no design).
- Organização interna dos módulos e nomes de funções privadas.
- Formato exato do resumo impresso no fim do CLI.

### Declined / Undiscussed Gray Areas → Assumptions

- Layout exato do CSV do usuário → registrado na tabela de Assumptions do spec (loader aceita wide e long).
- Fator de conversão unidade→caixa → registrado como assumption (`--units-per-case`, default sem conversão).
- Ano-alvo e horizonte → confirmados: anos futuros a partir de 2025, `--horizon-years` default 1.

---

## Specific References

- Tabela de demanda: `docs/Case BebiBem - MBM - Acting 2026.pdf`, p. 4 (Suco Premium, Geleia de frutas, Doce de frutas — 2022, 2023, 2024).
- Contexto de capacidade: p. 1–2 (expansão de 30% dos sucos; 12.000 → 15.600 caixas/mês; geleias 3.000; doces 5.000; total 20.000 caixas/mês).
- Pergunta de negócio a responder: questão 5, p. 3.

---

## Deferred Ideas

- Extrator automático da tabela do PDF (`pdfplumber`) — descartado nesta feature porque o usuário fornecerá o CSV; pode virar feature própria se o case ganhar novas tabelas.
- Break-even e comparação de preços da linha de soja (questão 4) — módulo separado, fora deste escopo.
- Intervalos de previsão (quantile regression / bootstrap) — melhora futura sobre o mesmo pipeline.
- Previsão por SKU quando houver histórico desagregado.
