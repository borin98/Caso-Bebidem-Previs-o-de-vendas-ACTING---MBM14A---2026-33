# POC Planejamento de Demanda Web — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implemente estas tasks com o skill `tlc-spec-driven`: **ative-o pelo nome e siga o fluxo Execute e as Critical Rules.** Não procure arquivos do skill pelo caminho do filesystem.

**Se o skill não puder ser ativado, PARE e avise o usuário — não prossiga sem ele.**

**Desvios aprovados pelo usuário (2026-09-30):**

- **Sem testes automatizados** ("é apenas um POC"):
  - gate de cada task = lint/build + a verificação manual de "Done when";
  - nenhum teste é escrito ou alterado;
  - Verifier final = roteiro **V-01…V-20** (fim deste arquivo) + checagem de POC-05, com o resultado em `validation.md`;
  - sem sensor de discriminação (não há testes para mutar).
- **Tudo em `poc/`:** nenhuma task cria ou altera arquivo fora de `poc/` e `.specs/` (POC-05).
- **P2/P3 na primeira rodada:** T17–T20 são obrigatórias, não opcionais.
- **Entrega só na branch** `feat/poc-html-rsys`: sem PR e sem push, salvo pedido explícito.
- **Um commit atômico por task.**
- 3 fases → execução inline, sem oferta de sub-agentes.
- **Diretriz:** "o mais simples possível".

---

**Spec**: `.specs/features/poc-demand-planning-web/spec.md`
**Design**: `.specs/features/poc-demand-planning-web/design.md`
**Context**: `.specs/features/poc-demand-planning-web/context.md`
**Branch**: `feat/poc-html-rsys`
**Status**: Executado (2026-09-30) — T1–T20 concluídas na branch `feat/poc-html-rsys`; T18–T20 sem alterações de código (revisão ponta a ponta no compose); verificação em `validation.md`

---

## Test Coverage Matrix

> Decisão do usuário: nenhum teste automatizado no POC. Diretrizes do repositório (`pyproject.toml` da raiz: ruff `line-length = 100`) são replicadas em `poc/api/pyproject.toml`.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Motor e reposição (`poc/api/src/poc_api/engine.py`, `replenishment.py`) | none | Verificação manual V-01…V-05, V-20 | — | Lint Py |
| API (`poc/api/src/poc_api/**`) | none | Verificação manual V-06…V-12, V-18 via `curl` / tela | — | Lint Py + Smoke API |
| Web (`poc/web/**`) | none | Verificação manual V-13, V-17, V-19 na tela | — | Build Web |
| Docker / docs (`poc/docker-compose.yml`, Dockerfiles, `poc/README.md`) | none | Compose smoke + V-14 | — | Compose smoke |

## Parallelism Assessment

| Test Type | Parallel-Safe? | Isolation Model | Evidence |
| --- | --- | --- | --- |
| — | N/A | Sem testes automatizados; tasks em sequência | Decisão do usuário |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Lint Py | Tasks Python | `cd poc/api && uv run ruff check . && uv run ruff format --check .` |
| Smoke API | Tasks de API | `cd poc/api && uv run uvicorn poc_api.app:app --port 8000` e `curl -fsS http://127.0.0.1:8000/api/v1/health` + as chamadas da task |
| Escopo | Fim de cada fase | `git diff dev --stat -- . ':!poc' ':!.specs'` vazio (POC-05) |
| Build Web | Tasks web | `cd poc/web && bun run lint && bun run build` |
| Compose smoke | T16 e fechamento | `cd poc && docker compose config --services` (esperado: `api`, `web`) `&& docker compose up -d --build && curl -fsS http://127.0.0.1:8000/api/v1/health && curl -fsS -o /dev/null http://127.0.0.1:3000/` |

Scripts de conferência das verificações manuais são descartáveis e não são commitados.

---

## Execution Plan

```
Fase 1 — Backend (poc/api):  T1 → T2 → T3 → T4 → T5 → T6 → T7
Fase 2 — Web (poc/web):      T8 → T9 → T10 → T11 → T12 → T13 → T14 → T15
Fase 3 — Entrega + P2/P3:    T16 → T17 → T18 → T19 → T20
```

Cada fase começa com a anterior concluída e o gate da fase verde. A demo P1 fica pronta na T16; T17–T20 fecham a primeira rodada.

---

## Task Breakdown

### Fase 1 — Backend (`poc/api/`)

#### T1: Projeto `poc/api` e pasta do POC

**What**:
- `poc/.gitignore` (`api/var/`, `web/node_modules/`, `web/.next/`).
- `poc/api/pyproject.toml`:
  - `fastapi`, `uvicorn[standard]` e `bebibem` com `[tool.uv.sources] bebibem = { path = "../..", editable = true }`;
  - `hatchling`, layout `src/`;
  - `[tool.ruff] line-length = 100`; `ruff` no grupo dev.
- `poc/api/uv.lock` e `poc/api/src/poc_api/__init__.py`.

**Where**: `poc/.gitignore`, `poc/api/pyproject.toml`, `poc/api/uv.lock`, `poc/api/src/poc_api/__init__.py`
**Depends on**: None
**Reuses**: AD-001 (uv + hatchling + `src/`)
**Requirement**: POC-05

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [x] `cd poc/api && uv run python -c "import bebibem, poc_api"` sem erro
- [x] Gate: Lint Py + Escopo

**Tests**: none · **Gate**: Lint Py
**Commit**: `chore(poc): Cria projeto poc/api com dependência do pacote bebibem`

---

#### T2: Motor do POC

**What**: `MODEL_CATALOG`, `MIN_HISTORY_MONTHS`, `HOLDOUT_MONTHS` e `evaluate_and_forecast(frame, horizon_years=2, seed=SEED) -> dict`, conforme o design (janela móvel, 9 modelos, vencedor, previsão; sem CV nem figuras).
**Where**: `poc/api/src/poc_api/engine.py`
**Depends on**: T1
**Reuses**: funções públicas de `bebibem` da tabela "Code Reuse"; nada da lista "Não usar no motor"
**Requirement**: POC-01, POC-02, POC-03, POC-04

**Tools**: MCP: NONE · Skill: `code-conducts`

**Done when**:
- [x] V-01, V-02, V-03 e V-04 conferidos com script descartável
- [x] Tempo do caso medido (referência para POC-40)
- [x] Gate: Lint Py

**Tests**: none · **Gate**: Lint Py
**Commit**: `feat(poc-motor): Adiciona motor com janela móvel e 9 modelos`

---

#### T3: Regras de reposição e posições de demonstração

**What**: `SERVICE_LEVEL_Z`, `STATUS_ORDER`, `accuracy`, `plan_product` (POC-06…13) e `demo_positions` (A14: aleatório com semente 42, lead time 1).
**Where**: `poc/api/src/poc_api/replenishment.py`
**Depends on**: T2
**Reuses**: fórmulas de `~/Downloads/previsao-compras-local.html:460–475`
**Requirement**: POC-06 … POC-13, POC-14 (posições)

**Tools**: MCP: NONE · Skill: `code-conducts`

**Done when**:
- [x] V-05 e V-20 (parte motor) conferidos
- [x] Gate: Lint Py

**Tests**: none · **Gate**: Lint Py
**Commit**: `feat(poc-reposicao): Adiciona necessidade de compra e posições de demonstração`

---

#### T4: Base da API

**What**: `app.py` (lifespan mínimo, `ApiError` + handler, `/health`), `schemas.py` (todos os modelos do design) e `store.py` (arquivos, escrita atômica).
**Where**: `poc/api/src/poc_api/{app,schemas,store}.py`
**Depends on**: T3
**Reuses**: `rsys-fastapi-guidelines` (tratamento de erro), estrutura plana do design
**Requirement**: POC-34 (health)

**Tools**: MCP: NONE · Skill: `rsys-fastapi-guidelines`, `fastapi`

**Done when**:
- [x] `GET /api/v1/health` → 200 `{"status":"ok"}`; recurso inexistente no envelope `erro`
- [x] Gate: Lint Py + Smoke API

**Tests**: none · **Gate**: Smoke API
**Commit**: `feat(poc-api): Adiciona base FastAPI com health, schemas e armazenamento`

---

#### T5: Dados

**What**: `datasets.py` (`seed`, `load_case`, `import_rows`, `close_month`, `apply_edits`, `diff`) e as rotas `/datasets`, `/datasets/{id}`, `/datasets/import`, `/datasets/case`, `/datasets/{id}/close-month` e `/datasets/{id}/edits`. Seed no lifespan quando o diretório está vazio.
**Where**: `poc/api/src/poc_api/datasets.py`, `poc/api/src/poc_api/app.py`
**Depends on**: T4
**Reuses**: `bebibem.io_data.load_demand`, `validate_frame`; `replenishment.demo_positions`
**Requirement**: POC-14, POC-15, POC-16, POC-17, POC-18, POC-35 (API)

**Tools**: MCP: NONE · Skill: `rsys-fastapi-guidelines`

**Done when**:
- [x] V-08 (parte API) conferido via `curl`
- [x] Diretório vazio → versão `caso` com posições aleatórias e `posicoes_demo = true`
- [x] Gate: Lint Py + Smoke API

**Tests**: none · **Gate**: Smoke API
**Commit**: `feat(poc-api): Adiciona versões de dados, importação, fechamento e edição`

---

#### T6: Treinos com limite de 60 s

**What**: `training.py`:
- treino em processo `spawn` com vigia `join(60)` + `terminate()`;
- `ensure_idle`, `start`, `recover_interrupted`, `activate`, `compare` e logs estruturados;
- `POC_TRAINING_TIMEOUT_S` com padrão 60 (sobrescrita só para verificação).

Rotas `/runs`, `/runs/{id}`, `/runs/{id}/activate` e `/runs/compare`. O lifespan recupera treinos interrompidos e inicia o treino inicial.

**Where**: `poc/api/src/poc_api/training.py`, `poc/api/src/poc_api/app.py`, `poc/api/src/poc_api/datasets.py`
**Depends on**: T5
**Reuses**: `engine.evaluate_and_forecast`
**Requirement**: POC-19, POC-20, POC-21, POC-22, POC-34, POC-39 (validação 1–3), POC-40

**Tools**: MCP: NONE · Skill: `rsys-fastapi-guidelines`

**Done when**:
- [x] V-09 (parte API), V-10, V-11, V-12 (parte API), V-16 e V-18 conferidos
- [x] Gate: Lint Py + Smoke API

**Tests**: none · **Gate**: Smoke API
**Commit**: `feat(poc-api): Adiciona treinamento em processo com limite de 60 s`

---

#### T7: Plano, overview e configurações

**What**: `planning.py` (`plan`, `overview`, `save_settings`, `set_model_choice`) e as rotas `/plan`, `/overview`, `/settings` (GET/PUT) e `/runs/{id}/model-choice`.
**Where**: `poc/api/src/poc_api/planning.py`, `poc/api/src/poc_api/app.py`
**Depends on**: T6
**Reuses**: `replenishment.plan_product`, `accuracy`; `engine.MODEL_CATALOG`
**Requirement**: POC-12, POC-13, POC-23, POC-25, POC-26, POC-27, POC-30, POC-36 (API)

**Tools**: MCP: NONE · Skill: `rsys-fastapi-guidelines`

**Done when**:
- [x] `/plan` do caso bate com V-05; V-06 (parte API) conferido
- [x] Gate: Lint Py + Smoke API + Escopo (fim da Fase 1)

**Tests**: none · **Gate**: Smoke API + Escopo
**Commit**: `feat(poc-api): Adiciona plano de reposição, overview e configurações`

---

### Fase 2 — Web (`poc/web/`)

#### T8: Base da web

**What**:
- `bun create next-app` em `poc/web` (TypeScript, App Router, Tailwind, `src/`), `shadcn init` e os componentes do design.
- `next.config.ts` (`standalone` + `rewrites`); `src/config/brand.ts` (nome neutro).
- `providers.tsx` e `app/app/layout.tsx` (sidebar + indicador de treino).
- `src/lib/api.ts` (tipos, `apiFetch`, erros, hooks com polling), `src/lib/format.ts` e `src/lib/help.ts` (texto de lead time).
- Banner de API indisponível.

**Where**: `poc/web/**`
**Depends on**: T7
**Reuses**: `rsys-frontend-stack` (Bun, Tailwind, shadcn via MCP, REST, TanStack Query), exceto Auth.js e Zod
**Requirement**: POC-24, POC-26 (texto de ajuda), POC-31 (polling), POC-32

**Tools**: MCP: `shadcn` · Skill: `rsys-frontend-stack`, `shadcn`

**Done when**:
- [x] Navegação Painel · Modelos · Dados · Versões; API parada → banner "Serviço de previsão indisponível" + "Tentar novamente"
- [x] Gate: Build Web

**Tests**: none · **Gate**: Build Web
**Commit**: `feat(poc-web): Cria base Next.js com shadcn, marca neutra e cliente da API`

---

#### T9: Landing

**What**: `app/page.tsx` com hero, faixa de números, problema, como funciona, por que confiar e CTA final.
**Where**: `poc/web/src/app/page.tsx`, `poc/web/src/components/landing-*.tsx`
**Depends on**: T8
**Reuses**: `useOverview`, `brand`
**Requirement**: POC-23, POC-24

**Tools**: MCP: `shadcn` · Skill: `rsys-frontend-stack`, `shadcn`

**Done when**:
- [x] V-13 conferido
- [x] Gate: Build Web

**Tests**: none · **Gate**: Build Web
**Commit**: `feat(poc-web): Adiciona landing comercial`

---

#### T10: Painel

**What**:
- `/app` com 5 KPIs e os parâmetros de reposição (lead time com ícone de ajuda; salvam em `/settings`).
- Tabela de produtos com barra de cobertura, badges de situação e de capacidade, filtro por nome e "Só com necessidade".
- `Dialog` "Estoque e capacidade" (ajuda fixa de lead time + selo de valores fictícios).

**Where**: `poc/web/src/app/app/page.tsx`, `poc/web/src/components/panel-*.tsx`
**Depends on**: T9
**Reuses**: `usePlan`, `useSettings`, `format`, `help`
**Requirement**: POC-12, POC-25, POC-26, POC-27, POC-30, POC-38

**Tools**: MCP: `shadcn` · Skill: `rsys-frontend-stack`, `shadcn`

**Done when**:
- [x] V-06, V-07, V-19 (painel e diálogo) e V-20 (selo) conferidos; filtros conforme POC-38
- [x] Gate: Build Web

**Tests**: none · **Gate**: Build Web
**Commit**: `feat(poc-web): Adiciona painel de reposição`

---

#### T11: Detalhe do produto

**What**: `Sheet` com fatos (lead time com ajuda), gráfico (vendido, holdout, previsão, faixa ±MAD, estoque projetado, SS, capacidade), tabela de projeção e seletor de modelo com selo "Escolha manual".
**Where**: `poc/web/src/components/product-detail.tsx`, `poc/web/src/components/forecast-chart.tsx`
**Depends on**: T10
**Reuses**: shadcn `sheet`, `chart`, `tooltip`
**Requirement**: POC-12, POC-13, POC-28, POC-36

**Tools**: MCP: `shadcn` · Skill: `rsys-frontend-stack`, `shadcn`

**Done when**:
- [x] Fatos iguais ao `/plan`; legenda "Erro médio histórico (não é intervalo de confiança)"; linhas com final < 0 destacadas
- [x] Trocar o modelo altera SS e necessidade; ativar outro run volta ao vencedor (POC-36); V-19 (detalhe)
- [x] Gate: Build Web

**Tests**: none · **Gate**: Build Web
**Commit**: `feat(poc-web): Adiciona detalhe do produto com gráfico e escolha de modelo`

---

#### T12: Modelos

**What**: `/app/modelos` com seletor de produto, 9 modelos (ranking, "Vencedor", não aplicáveis com motivo), janela, texto do critério e gráfico do holdout com legenda clicável.
**Where**: `poc/web/src/app/app/modelos/page.tsx`
**Depends on**: T11
**Reuses**: `useRun`, shadcn `chart`
**Requirement**: POC-29

**Tools**: MCP: `shadcn` · Skill: `rsys-frontend-stack`, `shadcn`

**Done when**:
- [x] Vencedor destacado = `vencedor` do run para os 3 produtos
- [x] Gate: Build Web

**Tests**: none · **Gate**: Build Web
**Commit**: `feat(poc-web): Adiciona comparativo de modelos`

---

#### T13: Dados — importação e grade

**What**:
- `src/lib/spreadsheet.ts`: SheetJS na **versão corrigida mais recente do canal oficial**; ler, formato largo → longo, `autoMap`, `normalize`, planilha modelo com a ajuda de lead time na aba `Instruções`.
- Aba "Importar": dropzone, seletor de aba, mapeamento, prévia, "Baixar planilha modelo", "Usar dados do caso".
- Aba "Grade": edição produto × mês, "Nenhuma alteração", "Re-treinar agora".

**Where**: `poc/web/src/lib/spreadsheet.ts`, `poc/web/src/app/app/dados/page.tsx`, `poc/web/src/components/data-import.tsx`, `poc/web/src/components/edit-grid.tsx`
**Depends on**: T12
**Reuses**: `~/Downloads/previsao-compras-local.html:222–309`, `:585–599`
**Requirement**: POC-15, POC-16, POC-17, POC-35

**Tools**: MCP: `shadcn` · Skill: `rsys-frontend-stack`, `shadcn`

**Done when**:
- [x] V-08 conferido na tela; grade conforme POC-35
- [x] Versão do SheetJS registrada em `design.md` (Tech Decisions), sem vulnerabilidade conhecida (`bun audit` ou aviso oficial)
- [x] Gate: Build Web

**Tests**: none · **Gate**: Build Web
**Commit**: `feat(poc-web): Adiciona importação de planilhas e grade editável`

---

#### T14: Dados — fechar mês e progresso

**What**: Aba "Fechar mês" (mês `U+1` fixo, vendas por produto, estoque e a receber opcionais, horizonte 1/2/3 anos) e progresso do treino (tempo decorrido + "máx. 60 s"). Ao concluir, leva ao comparativo.
**Where**: `poc/web/src/components/close-month.tsx`, `poc/web/src/app/app/dados/page.tsx`
**Depends on**: T13
**Reuses**: `useRun` (polling)
**Requirement**: POC-18, POC-20, POC-31, POC-39, POC-40 (UI)

**Tools**: MCP: `shadcn` · Skill: `rsys-frontend-stack`, `shadcn`

**Done when**:
- [x] V-09 e V-10 na tela; treino com 1 ano limita o horizonte de cobertura a 12 (POC-39); V-19 (fechar mês)
- [x] Gate: Build Web

**Tests**: none · **Gate**: Build Web
**Commit**: `feat(poc-web): Adiciona fechamento de mês com re-treino e horizonte`

---

#### T15: Versões e comparativo

**What**: `/app/versoes` com lista (selo "Ativa", ativar) e comparativo base × alvo na mesma página.
**Where**: `poc/web/src/app/app/versoes/page.tsx`
**Depends on**: T14
**Reuses**: `useRuns`, `useCompare`
**Requirement**: POC-21, POC-22

**Tools**: MCP: `shadcn` · Skill: `rsys-frontend-stack`, `shadcn`

**Done when**:
- [x] V-12 conferido na tela
- [x] Gate: Build Web + Escopo (fim da Fase 2)

**Tests**: none · **Gate**: Build Web + Escopo
**Commit**: `feat(poc-web): Adiciona versões e comparativo antes×depois`

---

### Fase 3 — Entrega e P2/P3 (obrigatórias nesta rodada)

#### T16: Imagem FastAPI, imagem Next.js, `poc/docker-compose.yml` e `poc/README.md`

**What**:
- `poc/api/Dockerfile` + `poc/api/Dockerfile.dockerignore`: imagem **só da FastAPI**, contexto na raiz do repositório.
- `poc/web/Dockerfile` + `poc/web/.dockerignore`: imagem **só do Next.js**.
- `poc/docker-compose.yml`: exatamente `api` e `web`, volume `poc-data`, portas em 127.0.0.1, `INTERNAL_API_URL=http://api:8000`, `depends_on` com healthcheck.
- `poc/README.md`: `docker compose up --build`, `down`, `down -v`, execução local sem Docker e o roteiro da demo.

**Where**: `poc/api/Dockerfile`, `poc/api/Dockerfile.dockerignore`, `poc/web/Dockerfile`, `poc/web/.dockerignore`, `poc/docker-compose.yml`, `poc/README.md`
**Depends on**: T15
**Reuses**: `docker/pipeline.Dockerfile` (só como referência de padrão; não é alterado)
**Requirement**: POC-33, POC-34

**Tools**: MCP: NONE · Skill: NONE

**Done when**:
- [x] Compose smoke verde; `docker compose exec api id -u` e `docker compose exec web id -u` ≠ 0; volume preserva versões após `down`/`up`
- [x] V-14, V-16 (no container) e V-17 conferidos
- [x] Gate: Compose smoke + Escopo

**Tests**: none · **Gate**: Compose smoke
**Commit**: `build(poc): Adiciona imagens FastAPI e Next.js, docker-compose e README do POC`

---

#### T17: Exportar para Excel (P2)

**What**: Botão "Exportar para Excel" no painel, gerando `previsao_necessidade_compra.xlsx` com as 3 abas de POC-37.
**Where**: `poc/web/src/lib/spreadsheet.ts`, `poc/web/src/components/panel-*.tsx`
**Depends on**: T16
**Reuses**: `~/Downloads/previsao-compras-local.html:603–614`
**Requirement**: POC-37

**Tools**: MCP: `shadcn` · Skill: `rsys-frontend-stack`, `shadcn`

**Done when**:
- [x] Arquivo com as 3 abas e colunas exatas; valores iguais aos da tela
- [x] Gate: Build Web

**Tests**: none · **Gate**: Build Web
**Commit**: `feat(poc-web): Adiciona exportação Excel`

---

#### T18: Revisão P2 — grade editável ponta a ponta

**What**: Conferir o fluxo completo da grade (T5 API + T13 UI) dentro do compose: editar, salvar, re-treinar, comparar. Corrigir o que faltar.
**Where**: `poc/api/src/poc_api/datasets.py`, `poc/web/src/components/edit-grid.tsx` (só se houver correção)
**Depends on**: T17
**Reuses**: —
**Requirement**: POC-35

**Tools**: MCP: `shadcn` · Skill: `rsys-frontend-stack`

**Done when**:
- [x] Editar → nova versão `edicao` → re-treino → comparativo mostra células alteradas; salvar sem mudança → "Nenhuma alteração"
- [x] Gate: Compose smoke

**Tests**: none · **Gate**: Compose smoke
**Commit**: `fix(poc): Ajusta fluxo da grade editável` (só se houver alteração; senão registrar "sem alterações" em `validation.md`)

---

#### T19: Revisão P2 — escolha manual de modelo ponta a ponta

**What**: Conferir no compose: escolher o modelo no detalhe, ver o plano mudar, ativar outro run e ver o vencedor voltar. Corrigir o que faltar.
**Where**: `poc/api/src/poc_api/planning.py`, `poc/web/src/components/product-detail.tsx` (só se houver correção)
**Depends on**: T18
**Reuses**: —
**Requirement**: POC-36

**Tools**: MCP: `shadcn` · Skill: `rsys-frontend-stack`

**Done when**:
- [x] Critérios de POC-36 conferidos no compose
- [x] Gate: Compose smoke

**Tests**: none · **Gate**: Compose smoke
**Commit**: `fix(poc): Ajusta escolha manual de modelo` (só se houver alteração)

---

#### T20: Revisão P3 — horizonte selecionável ponta a ponta

**What**: Conferir no compose treinos com 1, 2 e 3 anos e o limite do horizonte de cobertura `min(24; 12h)`. Corrigir o que faltar.
**Where**: `poc/web/src/components/close-month.tsx`, `poc/web/src/components/panel-*.tsx` (só se houver correção)
**Depends on**: T19
**Reuses**: —
**Requirement**: POC-39

**Tools**: MCP: `shadcn` · Skill: `rsys-frontend-stack`

**Done when**:
- [x] 1 ano → cobertura limitada a 12; 3 anos → previsão de 36 meses; valor fora de 1–3 → 422
- [x] Gate: Compose smoke + Escopo

**Tests**: none · **Gate**: Compose smoke + Escopo
**Commit**: `fix(poc): Ajusta horizonte selecionável` (só se houver alteração)

---

## Diagram-Definition Cross-Check

| Task | Depends On | Diagrama | Status |
| --- | --- | --- | --- |
| T1 | None | início Fase 1 | ✅ |
| T2–T7 | tarefa anterior | cadeia T1 → … → T7 | ✅ |
| T8 | T7 | início Fase 2 | ✅ |
| T9–T15 | tarefa anterior | cadeia T8 → … → T15 | ✅ |
| T16 | T15 | início Fase 3 | ✅ |
| T17–T20 | tarefa anterior | cadeia T16 → … → T20 | ✅ |

Nenhuma task `[P]`: execução sequencial.

## Test Co-location Validation

| Task | Camada | Matriz exige | Task declara | Status |
| --- | --- | --- | --- | --- |
| T1–T3 | Projeto / motor | none | none | ✅ OK (decisão do usuário) |
| T4–T7 | API | none | none | ✅ OK |
| T8–T15, T17 | Web | none | none | ✅ OK |
| T16 | Docker / docs | none | none | ✅ OK |
| T18–T20 | Revisão ponta a ponta | none | none | ✅ OK |

## Requirement → Task Coverage

| Requisito | Tasks |
| --- | --- |
| POC-01 … POC-04 | T2 |
| POC-05 | T1 + gate Escopo (T7, T15, T16, T20) |
| POC-06 … POC-11 | T3 |
| POC-12 | T3, T7, T10, T11 |
| POC-13 | T3, T7, T11 |
| POC-14 | T3, T5, T6 |
| POC-15, POC-16, POC-17 | T5, T13 |
| POC-18 | T5, T14 |
| POC-19 | T6 |
| POC-20 | T6, T14 |
| POC-21, POC-22 | T6, T15 |
| POC-23 | T7, T9 |
| POC-24 | T8, T9 |
| POC-25, POC-27 | T7, T10 |
| POC-26 | T7, T8, T10, T11, T14 |
| POC-28 | T11 |
| POC-29 | T6, T12 |
| POC-30 | T7, T10 |
| POC-31 | T8, T14 |
| POC-32 | T8 |
| POC-33 | T16 |
| POC-34 | T4, T6, T16 |
| POC-35 | T5, T13, T18 |
| POC-36 | T7, T11, T19 |
| POC-37 | T17 |
| POC-38 | T10 |
| POC-39 | T6, T14, T20 |
| POC-40 | T6, T14 |

**Coverage:** 40/40.

---

## Roteiro de verificação manual (V-01…V-20)

Executado task a task ("Done when") e, por completo, pelo Verifier ao final. Resultado em `validation.md`.

| ID | Verificação | Esperado |
| --- | --- | --- |
| V-01 | `evaluate_and_forecast` sobre `data/raw` | Holdout 2024-01…2024-12; previsão 2025-01…2026-12 (24 meses); 9 modelos por produto; valores ≥ 0 |
| V-02 | Paridade com o CLI: `bebibem-forecast --timeseries --outdir <tmp>` (fora do repositório) vs. métricas do motor | MAD, MAPE, MSE, RMSE e MPE de cada (produto, modelo) iguais a `error_metrics.csv` + `timeseries_error_metrics.csv` com diferença ≤ 1e-6 |
| V-03 | Mesmo CSV com 2025-01 anexado | Holdout 2024-02…2025-01; previsão começa em 2025-02 |
| V-04 | Produto com 30 meses; lacuna no meio; fins diferentes | `InputError` com a mensagem de POC-02 / lacuna listada / desalinhados listados |
| V-05 | Plano do caso (H = 3, L = 1, q = 1, 95%, posições de `GET /settings`) a partir de `f` e RMSE do run | SS = 1,6449 × RMSE; N, projeção, cobertura, comprar até e situação conferidos à mão para os 3 produtos (POC-06…11) |
| V-06 | Nível de serviço 95% → 99% | SS e N sobem; lista de runs inalterada |
| V-07 | Capacidade de um produto < `D + N` | Badge "Excede capacidade"; N e situação iguais |
| V-08 | Planilha modelo reenviada; depois com uma quantidade apagada | Nova versão `importacao` 2022-01…2024-12 com 3 produtos; depois 422 citando produto e período |
| V-09 | Fechar 2025-01 | 201 + run `na_fila` → `executando` → `concluido`; comparativo com meses adicionados = [2025-01], holdout base 01/2024–12/2024 e alvo 02/2024–01/2025 |
| V-10 | Pedir outro treino ou fechar mês durante um treino | 409 "Já existe um treinamento em andamento"; nenhuma versão nova |
| V-11 | Matar a API durante um treino e subir de novo | `falhou` "Interrompido pelo reinício do serviço"; ativa inalterada |
| V-12 | Ativar treino anterior; tentar ativar `falhou` | Painel muda; ação indisponível / 409 |
| V-13 | Landing | Seções na ordem de POC-23; números = `GET /api/v1/overview`; nenhum percentual ou número de marketing fixo no código |
| V-14 | Empacotamento + offline | Em `poc/`, `docker compose config --services` = `api`, `web`; com Wi-Fi desligado, `docker compose up --build` sobe e todas as telas funcionam; DevTools sem requisições externas |
| V-15 | `git diff dev --stat -- . ':!poc' ':!.specs'` | Vazio (POC-05) |
| V-16 | `duracao_s` do treino inicial do caso (local e no container) | ≤ 60 s |
| V-17 | Roteiro completo da demo por uma pessoa de negócio | ≤ 5 min, sem terminal |
| V-18 | API com `POC_TRAINING_TIMEOUT_S=2` e um treino iniciado | `falhou` "Tempo limite de 2 s excedido"; processo encerrado; ativa inalterada; novo treino aceito na hora. Com o padrão, a mensagem é "Tempo limite de 60 s excedido" |
| V-19 | Ajuda de lead time | Ícone com o texto exato de POC-26 em parâmetros, "Estoque e capacidade" (também fixo abaixo do campo), detalhe do produto e fechar mês |
| V-20 | Posições de demonstração | "Usar dados do caso" duas vezes gera as mesmas posições; estoque ∈ `[0; 3m]`, a receber ∈ `[0; m]`, lead time 1; selo "Valores fictícios gerados aleatoriamente para demonstração" visível até salvar posições |

---

## Ferramentas por task

- **MCP:** `shadcn` em toda task de UI.
- **Skills:**
  - `code-conducts` (T2–T3);
  - `rsys-fastapi-guidelines` + `fastapi` (T4–T7), com a estrutura plana do design;
  - `rsys-frontend-stack` + `shadcn` (T8–T20), sem Auth.js e sem Zod.

---

## Plane

O usuário cria o card do épico no projeto **P&D** e registra o identificador aqui.

| Item | Issue Plane |
| --- | --- |
| [Épico] Fazer o POC — Planejamento de Demanda Web | _(preencher pelo usuário)_ |

Sugestão de descrição do épico:

- **Objetivo:** POC comercial white-label, local em Docker (Next.js + shadcn + FastAPI), numa pasta própria `poc/`, com os 9 modelos do pacote `bebibem`, fechar mês com re-treino (≤ 60 s), versões com comparativo e recomendação de compra. Público: founders e negócio (referências: Neogrid, UniSoma/Prognos).
- **Documentos (branch `feat/poc-html-rsys`):** `.specs/features/poc-demand-planning-web/{spec,context,design,tasks,reference-chat}.md`.
- **Escopo:** 40 requisitos (P1 = 35, P2 = 4, P3 = 1), todos na primeira rodada; 20 tasks em 3 fases: Backend (T1–T7) · Web (T8–T15) · Entrega e P2/P3 (T16–T20). Sem testes automatizados; verificação pelo roteiro V-01…V-20.
- **Pronto quando:**
  - roteiro da demo em ≤ 5 min sem terminal;
  - re-treino do caso ≤ 60 s;
  - nenhum número fixo na UI;
  - nada alterado fora de `poc/`;
  - funciona sem internet.
