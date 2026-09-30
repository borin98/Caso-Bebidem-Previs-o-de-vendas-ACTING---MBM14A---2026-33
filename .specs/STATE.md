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
- **Status**: superseded by AD-020

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

### AD-014
- **Decision**: O motor do POC (`poc/api/src/poc_api/engine.py`) usa janela de avaliação móvel: holdout = últimos 12 meses observados; treino = meses anteriores; mínimo de 36 meses por produto; `random_state=42`; previsão recursiva. CLI e notebook continuam com AD-004 (holdout 2024).
- **Reason**: O POC anexa meses ("fechar mês"); sem testes, refatorar o pipeline arriscaria mudar as saídas do CLI sem detecção, então a janela fica isolada no motor novo.
- **Trade-off**: Duas regras de janela no repositório (CLI fixa 2024, POC móvel) e orquestração de backtest repetida no motor; para `data/raw` as duas coincidem (conferido em V-02). Unificação adiada.
- **Scope**: `poc/api/src/poc_api/engine.py`.
- **Date**: 2026-09-30
- **Status**: active

### AD-015
- **Decision**: No motor do POC a previsão começa no mês seguinte ao último observado e cobre `12 × horizon_years` meses (`horizon_years ∈ {1,2,3}`, padrão 2). O CLI continua com AD-011.
- **Reason**: Com meses anexados, a data fixa 2025-01 preveria meses já observados.
- **Trade-off**: CLI e POC com regras de início diferentes até a unificação.
- **Scope**: `poc/api/src/poc_api/engine.py`.
- **Date**: 2026-09-30
- **Status**: active

### AD-016
- **Decision**: O POC web usa Next.js (App Router) + Bun + Tailwind + shadcn/ui + TanStack Query, com tipos TypeScript (sem Zod), em `poc/web/`, e FastAPI plano em `poc/api/` (projeto uv próprio que depende de `bebibem` por caminho). Sem autenticação; sem testes automatizados; portas publicadas só em 127.0.0.1; treino limitado a 60 s. Empacotamento: **uma imagem Docker para a FastAPI** (`poc/api/Dockerfile`), **uma para o Next.js** (`poc/web/Dockerfile`) e **um único `poc/docker-compose.yml`** com os serviços `api` e `web`; as imagens de AD-005 ficam fora desse compose.
- **Reason**: Decisões do usuário: stack RSYS, demo local sem login, "usar shadcn", "o mais simples possível", "sem testes (é apenas um POC)", "uma imagem docker para o fast-api, uma para o nextjs e ambas em um docker-compose.yml", "re-treino em até 60 segundos".
- **Trade-off**: Desvios do `rsys-frontend-stack` (sem Auth.js, sem Zod) e do `rsys-fastapi-guidelines` (sem camadas separadas, sem SQLModel, sem testes); a versão SaaS precisa voltar ao padrão.
- **Scope**: `poc/**`.
- **Date**: 2026-09-30
- **Status**: active

### AD-017
- **Decision**: O estado do POC vive em arquivos sob `POC_DATA_DIR` (volume `poc-data` no Docker): versões de dados e treinos imutáveis, ponteiro `active.json` e `settings.json`, com escrita atômica; sem banco de dados.
- **Reason**: Usuário único e demo local; banco está fora de escopo; arquivos são auditáveis e fáceis de zerar (remover o volume).
- **Trade-off**: Sem consultas nem concorrência multiusuário; migrar para SaaS exigirá repositório com banco.
- **Scope**: `poc/api/src/poc_api/store.py`.
- **Date**: 2026-09-30
- **Status**: active

### AD-018
- **Decision**: As regras de reposição (estoque de segurança `z × RMSE × √max(L,1)`, necessidade arredondada ao múltiplo, projeção, cobertura, "comprar até", situação ruptura/comprar/adequado/excesso, alerta de capacidade) e as posições de demonstração (aleatórias, semente 42, lead time 1) vivem só em `poc/api/src/poc_api/replenishment.py`; a web apenas exibe.
- **Reason**: Fonte única das regras do POC; fórmulas portadas do HTML de referência validado no chat do usuário.
- **Trade-off**: Cada recálculo de parâmetro passa pela API em vez de rodar no navegador.
- **Scope**: `poc/api/src/poc_api/replenishment.py` e consumidores.
- **Date**: 2026-09-30
- **Status**: active

### AD-019
- **Decision**: Todo o POC vive na pasta `poc/` e consome `bebibem` como biblioteca, só pelas funções públicas. Nenhum arquivo fora de `poc/` e `.specs/` é criado ou alterado pelo POC (pacote, CLI, notebook, testes, `docker/`, `pyproject.toml`, `uv.lock`, `README.md` da raiz). A lógica exclusiva do POC (janela móvel, reposição) fica em `poc/api/`, como exceção explícita e delimitada ao AD-006.
- **Reason**: Pedido do usuário ("deixe o arquivo do jupyter notebook; crie uma pasta nova para isso"); isola o entregável acadêmico da demo comercial.
- **Trade-off**: Parte da lógica de cálculo fora de `src/bebibem/` e orquestração de backtest repetida; unificação adiada para a versão SaaS.
- **Scope**: `poc/**` e sua relação com `src/bebibem/**`.
- **Date**: 2026-09-30
- **Status**: active

### AD-020
- **Decision**: Stack analítica do projeto: `numpy`, `pandas`, `scikit-learn`, `matplotlib` e `statsmodels` (Holt-Winters e SARIMA, DEM-26), com `pandas-stubs` para tipos. `scipy` entra só como dependência transitiva (sem import direto) e `seaborn` continua fora.
- **Reason**: O AD-002 proibia `statsmodels`, mas o pacote já depende dele desde DEM-26 (`pyproject.toml`: `statsmodels>=0.15.0`). O usuário pediu para desmarcar o AD-002.
- **Trade-off**: Dependência maior (statsmodels + scipy transitivo) na imagem e no lock.
- **Scope**: `src/bebibem/**`, notebooks, `poc/api/`.
- **Date**: 2026-09-30
- **Status**: active

## Handoff

- **Feature**: poc-demand-planning-web (`.specs/features/poc-demand-planning-web/`)
- **Phase / Task**: PRD aprovado (rodada 2: POC em `poc/`, nome neutro, posições aleatórias com lead time 1, P2/P3 na primeira rodada, sem PR, SheetJS seguro, re-treino ≤ 60 s). Execute não iniciado — usuário pediu para não codar ainda.
- **Completed**: PRD (40 requisitos POC-01…40; 20 tasks em 3 fases; roteiro V-01…V-20); AD-014…AD-020 (AD-002 superseded por AD-020).
- **In-progress**: none
- **Next step**: Quando o usuário pedir, iniciar o Execute pela T1 (`poc/api/pyproject.toml`), seguindo `tasks.md` (sem testes; gate lint/build + verificação manual).
- **Blockers**: none. O usuário cria o card do épico no Plane (projeto P&D) e registra o id em `tasks.md` § Plane. Chat integral já registrado em `reference-chat.md` §5.
- **Validation**: previsao-demanda-bebibem continua PASS (`.specs/features/previsao-demanda-bebibem/validation.md`).
- **Uncommitted files**: `.DS_Store` e `reports/` preexistentes, não relacionados.
- **Branch**: `feat/poc-html-rsys` (cortada de `dev`)
