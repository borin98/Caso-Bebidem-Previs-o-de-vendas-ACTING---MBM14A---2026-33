# STATE

## Decisions

### AD-001
- **Decision**: Gerenciamento de ambiente e dependências com `uv` + `pyproject.toml` (+ `uv.lock` versionado), Python ≥ 3.11, layout `src/` com build backend `hatchling`.
- **Reason**: Pedido explícito do usuário; lock reprodutível e instalação rápida no container.
- **Trade-off**: Exige `uv` instalado (ou baixado no build Docker); abandona `requirements.txt`/venv manual.
- **Scope**: Todo o repositório `insper-bebidem`.
- **Date**: 2026-09-10
- **Status**: active

### AD-002
- **Decision**: Stack analítica limitada a `numpy`, `pandas`, `scikit-learn`, `matplotlib` — sem `scipy`, `statsmodels`, `seaborn` ou frameworks de séries temporais.
- **Reason**: Stack fixada pelo usuário; `numpy`/`pandas` já cobrem interpolação e média móvel.
- **Trade-off**: Sem splines cúbicas prontas nem SARIMA; ajuste polinomial por mínimos quadrados substitui a spline.
- **Scope**: `src/bebibem/**`, notebooks.
- **Date**: 2026-09-10
- **Status**: active

### AD-003
- **Decision**: Toda figura é exportada por `plotting.save_figure` em PNG (300 dpi), SVG e PDF, com metadados de data suprimidos (`metadata={"Date": None}` / `{"CreationDate": None}`).
- **Reason**: Entrega exige raster e vetorial; supressão de metadados torna a saída byte-estável e testável por hash.
- **Trade-off**: Perde-se o carimbo de data nos arquivos; 3× mais arquivos por figura.
- **Scope**: Todas as figuras do projeto.
- **Date**: 2026-09-10
- **Status**: active

### AD-004
- **Decision**: Reprodutibilidade obrigatória: `random_state=42` em todo estimador estocástico, avaliação com `TimeSeriesSplit(3)` no treino 2022–2023 e holdout 2024; previsão sempre recursiva.
- **Reason**: 36 observações por série; sem partição temporal rígida qualquer métrica seria otimista.
- **Trade-off**: Menos dados de treino na fase de seleção; nenhuma busca de hiperparâmetros.
- **Scope**: `models.py`, `forecast.py` e qualquer feature futura de previsão.
- **Date**: 2026-09-10
- **Status**: active

### AD-005
- **Decision**: Duas imagens Docker independentes — `docker/pipeline.Dockerfile` (executa o CLI) e `docker/jupyter.Dockerfile` (serve o JupyterLab) — ambas com usuário não-root (uid 10001) e `MPLBACKEND=Agg`.
- **Reason**: Pedido explícito do usuário (substitui a proposta inicial de imagem multi-stage única); mantém a imagem do script sem JupyterLab.
- **Trade-off**: Duas imagens para manter e dois builds no CI; camadas de dependência duplicadas.
- **Scope**: Empacotamento e entrega do projeto.
- **Date**: 2026-09-10
- **Status**: active

### AD-006
- **Decision**: Toda lógica de cálculo vive em `src/bebibem/**`; notebooks e Dockerfiles apenas consomem essas funções (notebook versionado sem outputs).
- **Reason**: Evita divergência entre script e notebook e mantém tudo testável por unidade.
- **Trade-off**: Notebook fica menos "autoexplicativo" isoladamente — depende do pacote instalado.
- **Scope**: `notebooks/**`, `docker/**`, `src/bebibem/**`.
- **Date**: 2026-09-10
- **Status**: active

### AD-007
- **Decision**: Artefatos voltados ao usuário (títulos, rótulos, README, notebook, mensagens de erro) em PT-BR; identificadores de código, módulos e nomes de arquivo em inglês/slug ASCII.
- **Reason**: Case e interlocutor em PT-BR; nomes de arquivo ASCII evitam problemas de encoding em container e Git.
- **Trade-off**: Mistura de idiomas entre superfície e código.
- **Scope**: Todo o repositório.
- **Date**: 2026-09-10
- **Status**: active

### AD-008
- **Decision**: Escalas não se misturam: demanda da loja própria em *unidades*, capacidade fabril em *caixas/mês*; conversão só com `--units-per-case N` explícito.
- **Reason**: O case não fornece fator caixa→unidade; somar as escalas produziria número falso.
- **Trade-off**: Duas figuras/tabelas em vez de uma visão única por padrão.
- **Scope**: `capacity.py`, figuras de capacidade e qualquer análise agregada futura.
- **Date**: 2026-09-10
- **Status**: active

### AD-009
- **Decision**: Avaliação de erro sempre com o conjunto **MAD, MAPE, MSE, RMSE e MPE**, publicado como tabela comparativa por (produto, modelo) em CSV e em figura-tabela; vencedor por menor MAPE, desempate < 0,5 p.p. por menor MAD.
- **Reason**: Confirmado pelo usuário; MPE expõe viés sistemático que métricas absolutas escondem.
- **Trade-off**: Mais colunas para manter e explicar; MAPE/MPE precisam de tratamento explícito para `y_t = 0`.
- **Scope**: `models.py`, `figures.fig_error_table`, notebook, README.
- **Date**: 2026-09-10
- **Status**: active

### AD-010
- **Decision**: Grau da interpolação polinomial limitado a `d ∈ {1..5}` e escolhido por menor RMSE fora da amostra (holdout 2024), com `R²` e `R² ajustado` sempre reportados.
- **Reason**: Confirmado pelo usuário: evitar overfitting; erro fora da amostra é o único juiz honesto de complexidade.
- **Trade-off**: Curva pode ficar menos "colada" aos pontos históricos.
- **Scope**: `interpolation.py` e figuras de interpolação.
- **Date**: 2026-09-10
- **Status**: active

### AD-011
- **Decision**: Previsão cobre **somente anos futuros** (início 2025-01), com `--horizon-years ∈ {1,2,3}` (default 1); histórico nunca é reprevisto fora do backtest de avaliação.
- **Reason**: Confirmado pelo usuário ("apenas para os próximos anos").
- **Trade-off**: Sem previsão in-sample para comparação visual além do backtest.
- **Scope**: `forecast.py`, CLI, tabelas `forecast_monthly.csv` / `forecast_annual.csv`.
- **Date**: 2026-09-10
- **Status**: active

### AD-012
- **Decision**: `src/bebibem/formulas.py` é a fonte única das 28 fórmulas em LaTeX/mathtext; `design.md`, notebook, README e rodapés de figuras consomem dela, com símbolos padronizados (`y_t`, `\hat{y}_t`, `n`, `w`, `d`, `k`, `\beta`, `X`).
- **Reason**: Pedido do usuário de escrever as fórmulas formalmente; fonte única evita divergência documento × código.
- **Trade-off**: Alterar uma fórmula exige atualizar o módulo e reexecutar as figuras que a exibem.
- **Scope**: Todo o projeto (documentação, figuras, notebook).
- **Date**: 2026-09-10
- **Status**: active

### AD-013
- **Decision**: O comparativo de previsão inclui, além de Ridge/RandomForest/GradientBoosting, três regressões clássicas implementadas em numpy — `linear_normal_equation`, `exponential_loglinear` e `exponential_normal_equation` — avaliadas nas mesmas 5 métricas e no mesmo holdout; a regressão logística entra como **classificador do regime `alta`** com matriz de confusão, em tabela e figura separadas.
- **Reason**: Pedido do usuário (referências `Regressao_linear.py`, `Regressao_Exponencial.py`, `Regressao_Exponencial Equacao Normal.py`, `regrassao log confusion.py`, não disponíveis neste repositório — a implementação segue a formulação matemática do `design.md`).
- **Trade-off**: Mais modelos para manter e explicar; regressões de tendência pura tendem a perder para os modelos sazonais, mas servem de baseline interpretável com equação legível na figura.
- **Scope**: `regression.py`, `classification.py`, `models.py`, figuras `18_regressao_*` e `21_confusao_*`, tabelas `regression_fit.csv` e `regime_classification.csv`.
- **Date**: 2026-09-10
- **Status**: active

## Handoff

- **Feature**: previsao-demanda-bebibem (`.specs/features/previsao-demanda-bebibem/`)
- **Phase / Task**: Planejamento concluído (Specify + Discuss + Design + Tasks). Execute não iniciado.
- **Completed**: spec.md (25 requisitos), context.md, design.md (+ Formulário matemático, 28 fórmulas), tasks.md (26 tasks), STATE.md (AD-001..AD-013), README.md (formulário matemático em LaTeX)
- **In-progress** (file:line): nenhum
- **Next step**: usuário aprova spec/design/tasks, confirma matriz de testes e entrega `data/raw/demanda_loja_propria.csv`; então iniciar Fase 1 (T1–T4) com a oferta de sub-agentes (6 fases ⇒ 1 worker por fase + Verifier final).
- **Blockers**: CSV real ainda não fornecido (bloqueia apenas T23); repositório ainda sem `git init` (T1)
- **Uncommitted files**: `.specs/**` (repositório ainda não inicializado no Git)
- **Branch**: n/a (sem repositório Git)
