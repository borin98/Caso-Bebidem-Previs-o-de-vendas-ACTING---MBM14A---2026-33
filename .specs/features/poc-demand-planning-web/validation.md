# Validação — POC Planejamento de Demanda Web

**Feature:** `poc-demand-planning-web` · **Branch:** `feat/poc-html-rsys`
**Verificador:** independente (autor ≠ verificador), 2026-09-30
**Commits cobertos:** `a835d5d..95e4a7b` (HEAD): tasks T1–T20 (até `bf1de6c`) + iteração de correção 1 (`95e4a7b`)
**Método:** roteiro manual V-01…V-20 (`tasks.md`) + POC-05, sem testes automatizados (desvio aprovado). Scripts descartáveis em `/tmp` (`v_engine.py`, `v_engine2.py`, `v_api.py`, `v_api2.py`, `v_api3.py`), API isolada em `127.0.0.1:8001`/`8002` com `POC_DATA_DIR=/tmp/…`, navegador headless contra a stack do compose.

## Veredito

**PASS (final, depois da iteração 1)**: todos os itens executáveis (V-01…V-16, V-18…V-20 e POC-05) passaram e as lacunas 1 e 3 da primeira rodada foram corrigidas e reconferidas. Dois itens dependem de pessoa e ficam pendentes (ver abaixo). Nenhuma lacuna restante bloqueia.

**Pendente — verificação humana:**
- **V-17** (roteiro completo por pessoa de negócio em ≤ 5 min). Evidência parcial: o fluxo importar → treino (status "Executando · máx. 60 s") → redirecionamento automático para `/app/versoes?base=…&alvo=…` rodou na UI sem terminal em ~5 s.
- **V-14, parte Wi-Fi desligado.** Evidência parcial: `performance.getEntriesByType('resource')` em `/` e `/app` só tem o host `127.0.0.1:3000`, sem nenhum host externo. A web usa a pilha de fontes do sistema (desvio registrado no design).

## Gates

| Gate | Comando | Resultado |
| --- | --- | --- |
| Lint Py | `cd poc/api && uv run ruff check . && uv run ruff format --check .` | `All checks passed!` · `9 files already formatted` (exit 0) |
| Build Web | `cd poc/web && bun run lint && bun run build` | eslint sem saída; `next build` ✓ com rotas `/`, `/app`, `/app/dados`, `/app/modelos`, `/app/versoes` (exit 0) |
| Compose smoke | `docker compose config --services` | `api`, `web` |
| | portas (`docker compose config`) | `host_ip: 127.0.0.1` em 8000 e 3000; `INTERNAL_API_URL: http://api:8000`; volume `poc-data` → `poc_poc-data` |
| | `docker compose down` → `up -d --build` | health `{"status":"ok"}`; web `/` 200; `/app` 200 |
| | persistência | runs antes = 5, depois de `down`/`up` = 5 (volume mantido) |
| | usuário não-root | `exec api id -u` = **10001**; `exec web id -u` = **1000** |
| Escopo (POC-05) | `git diff dev --stat -- . ':!poc' ':!.specs'` | **vazio** |

Stack deixada no ar (api + web). Depois do smoke, a API foi parada e religada com `stop`/`start` para o teste de POC-32. Uma importação pela UI (V-08) criou mais uma versão `importacao` + run no volume.

## Roteiro V-01…V-20

| ID | Como | Observado | Status |
| --- | --- | --- | --- |
| V-01 | `evaluate_and_forecast(load_demand(DEFAULT_INPUT))` | 3 produtos; `janela` = treino até 2023-12, holdout 2024-01…2024-12; 9 modelos (conjunto = `MODEL_CATALOG`), 9/9 aplicáveis; previsão 24 meses 2025-01…2026-12, todos ≥ 0; holdout previsto com 12 pontos. Vencedor = `bebibem.models.select_best` sobre os aplicáveis: doce = Holt-Winters mult., geleia = Random Forest, suco = Gradient Boosting. Tempo local 2,2 s | PASS |
| V-02 | `uv run bebibem-forecast --timeseries --outdir /tmp/v02 --formats png` vs métricas do motor | 27 linhas CLI (6 ML/clássicos + 3 séries × 3 produtos); 135 comparações (MAD, MSE, RMSE, MAPE, MPE); **diferença máx. 5,7e-14** (≤ 1e-6); nenhuma linha faltante | PASS |
| V-03 | `data/raw` + 2025-01 anexado | holdout 2024-02…2025-01, treino até 2024-01, previsão começa em 2025-02 nos 3 produtos | PASS |
| V-04 | recortes do caso | 30 meses: `InputError: histórico insuficiente: suco_premium tem 30 meses; mínimo 36`. Lacuna: `doce_de_frutas: meses faltantes no meio da série: 2023-05, 2023-06`. Fim desalinhado: `produtos terminam em meses diferentes: doce_de_frutas termina em 2024-11, …` | PASS |
| V-05 | plano da API vs reimplementação independente de POC-06…12 (`ref_plan`) a partir de `previsao` e `rmse` retornados | caso (H = 3, L = 1, q = 1, 95%): doce SS = 14,309, N = 122, cob. 0,6; suco SS = 12,136, N = 109, cob. 1,4; geleia SS = 6,559, N = 22, cob. 1,6; todos "Imediato"/ruptura. Mais 12 cenários com posições mistas (L = 0,5 e 2,5, q = 5, D = 5000, H = 1/6/12/24) cobrem os ramos `comprar até = abr/2025`, `–`, `> 24`, `excesso`, `adequado`. **0 divergências** em SS, N, Dem, projeção, cobertura, comprar até, situação e `excede_capacidade` | PASS |
| V-06 | `PUT /settings` 95% → 99% | SS 14,31→20,24 / 12,14→17,16 / 6,56→9,28; N 122→128 / 109→114 / 22→25; lista de runs idêntica; reconferido com `ref_plan`. Fora da faixa: H = 25 → 422 `deve ser menor ou igual a 24`; LT = 1,3 → 422 `passos de 0,5` | PASS |
| V-07 | capacidade = D + N − 1 (162) no doce | `excede_capacidade = true`, N 122→122, situação ruptura→ruptura; demais produtos `null`. Badge "Excede capacidade" em `panel-table.tsx:157` e `product-detail.tsx:174` | PASS |
| V-08 | UI: "Baixar planilha modelo" → reenviar; depois com uma quantidade apagada | xlsx `modelo_previsao_compras.xlsx` com abas `Vendas` (108 linhas, formato longo) e `Instruções` (linha "Lead time (meses)" com o texto de POC-26). Reenvio pela UI: nova versão `importacao`, 2022-01…2024-12, 3 produtos. Com a célula 2022-09 apagada: mensagem "… frutas 2022-09: quantidade vazia ou não numérica", nenhuma versão criada (3→3). API direta: 422 `Geleia de frutas 2022-05: quantidade vazia ou não numérica` | PASS |
| V-09 | `POST /datasets/{ativa}/close-month` 2025-01 | 201, `origem = fechamento`, `pai_id` = ativa, `periodo_fim` 2025-01, run `na_fila` → `executando` → `concluido` (3,4 s), vira ativo. `GET /runs/compare`: `meses_adicionados = ['2025-01']`, `celulas_alteradas = 0`, holdout base 2024-01…2024-12 e alvo 2024-02…2025-01, Δ MAPE doce = 0,333 p.p. (= 15,863 − 15,530) | PASS |
| V-10 | durante o treino: `POST /runs`, `close-month`, `POST /datasets/case` | 409 `Já existe um treinamento em andamento` nos três; contagem de datasets inalterada; 1 run aberto | PASS |
| V-11 | `pkill -9` da API com run `na_fila` e religar | log `status: falhou, erro: Interrompido pelo reinício do serviço`; ativa inalterada; o filho órfão não gravou `result.json` | PASS |
| V-12 | `POST /runs/{anterior}/activate`; ativar run `falhou` | 200 e `/plan.run_id` passa ao anterior; `falhou` → 409 `Só treinos concluídos podem ser ativados`; UI só mostra "Ativar" quando `ativo === false && status === "concluido"` (`versions-view.tsx:93`) | PASS |
| V-13 | navegador em `/` + `GET /api/v1/overview` | h1 → faixa de números → "O problema" → "Como funciona" (`#como-funciona`) → "Por que confiar" → CTA final "Abrir o painel" → `/app`; "Ver demonstração" → `/app`. Faixa: 9 / 85,0% / 36 / 3 / 30/09/2026 19:29 = overview (`n_modelos` 9, `acuracia_media` 84,98, `meses_historico` 36, `n_produtos` 3, `concluido_em` 22:29Z). Nenhum `NN%` ou `R$` fixo em `app/` ou `components/` (grep) | PASS |
| V-14 | `docker compose config --services`; recursos da página | `api`, `web`; só `127.0.0.1:3000` nos recursos. **Wi-Fi desligado: pendente (humano)** | PASS (parcial) |
| V-15 | `git diff dev --stat -- . ':!poc' ':!.specs'` | vazio | PASS |
| V-16 | `duracao_s` do treino inicial do caso | local 3,1 s (seed em `/tmp/vapi`); container 4,6 s (run `caso` no volume) | PASS |
| V-17 | — | **Pendente — verificação humana** | — |
| V-18 | API em :8002 com `POC_TRAINING_TIMEOUT_S=2` | `POST /runs` 202 → `falhou` "Tempo limite de 2 s excedido", `duracao_s` 2,0; nenhum processo `multiprocessing.spawn` restante; ativa inalterada; novo `POST /runs` → 202 na hora. Padrão: `f"Tempo limite de {limit} s excedido"` com `limit = 60` (`training.py:42,148`) | PASS |
| V-19 | navegador: ícone `aria-label="O que é lead time?"` | parâmetros: tooltip com o texto exato; "Estoque e capacidade": 3 ícones + texto fixo abaixo do campo (3×); detalhe do produto: ícone em "Lead time · múltiplo"; Fechar mês: 3 ícones ("Lead time em uso"). Texto único em `lib/help.ts:1` | PASS |
| V-20 | seed + `POST /datasets/case` 2× | m = 39,67 / 15,00 / 64,75; estoque 10 / 30 / 84 ∈ [0; 3m]; a receber 31 / 7 / 56 ∈ [0; m]; inteiros; LT = 1; posições idênticas após a 2ª carga; `posicoes_demo` true → false depois de `PUT /settings` com posições; selo visível no painel e em "Estoque e capacidade" | PASS |

## Checagens extras (fora do roteiro, para cobrir ACs)

- **POC-16:** negativo → 422 `Doce de frutas 2022-04: quantidade negativa (-1)`; lacuna → 422 listando os meses; 108 problemas → 20 itens + `… e mais 88`. Nenhuma versão criada.
- **POC-18:** falta produto, 1,5 ou −1 → 422 com produto e mês (2025-02); nenhuma versão criada. Campo mês `readOnly disabled` (`close-month.tsx:88`).
- **POC-19:** `POST /runs` → 202 `na_fila`.
- **POC-20 (falha libera a versão):** o dataset do run que estourou o tempo foi re-treinado na hora (202).
- **POC-35:** `edits` vazio → 422 `sem_alteracoes`/"Nenhuma alteração"; −2 e 2,5 → 422; edição válida → 201 `edicao`, `pai_id` = ativa, sem run automático.
- **POC-36:** `PUT /runs/{id}/model-choice` ridge → plano usa ridge (previsão, RMSE e MAD idênticos ao modelo) com `escolha_manual = true`; outro run ativado → vencedor sem escolha; voltar ao run → escolha mantida; modelo desconhecido → 422.
- **POC-39:** `horizon_years = 4` → 422; run com h = 1 → `previsao` com 12 meses, `horizonte_max = 12`.
- **POC-32:** API parada → "Serviço de previsão indisponível" + "Tentar novamente", sem números do painel.
- **Edge case de armazenamento:** `result.json` corrompido → 500 `armazenamento_invalido`, arquivo preservado.
- **POC-34:** linhas de log JSON `{"evento":"treino","run_id","dataset_id","status","duracao_s"[, "erro"]}` em cada transição (vistas no stdout da API em :8001).

## Cobertura POC-01…POC-40

| AC | Evidência |
| --- | --- |
| POC-01 | V-01, V-03 |
| POC-02 | V-04 (mensagem exata) |
| POC-03 | V-01 (9 modelos, vencedor = `select_best`), V-02 (métricas). Ramo não aplicável não exercitado com dados reais: código `engine.py:285` (`_empty_model`) |
| POC-04 | V-01 (24 meses ≥ 0, 12 de holdout); h = 1 → 12 meses |
| POC-05 | V-15; CLI mantém holdout 2024 (V-02 bate com o motor sobre 2024) |
| POC-06…POC-11 | V-05 (reimplementação independente, 15 cenários, 0 divergências), V-06 |
| POC-12 | V-07 |
| POC-13 | `/plan` com `mad`, `mape`, `acuracia` = 100 − MAPE (84,47 = 100 − 15,53); detalhe exibe MAD 6,1 un. · MAPE 15,5% · Acurácia 84,5% |
| POC-14 | V-20 (seed em diretório vazio → `caso` + treino inicial); persistência no volume (compose smoke) |
| POC-15 | V-08 pela UI (auto-mapeamento, prévia de 5 linhas, "108 linha(s) de 3 produto(s)"). Formato largo e os 5 formatos de período: só código (`lib/spreadsheet.ts`), não exercitados |
| POC-16 | V-08 + checagens extras (vazio, negativo, lacuna, desalinhado, histórico < 36, limite de 20 itens) |
| POC-17 | V-08 (planilha modelo), V-20 ("Usar dados do caso") |
| POC-18 | V-09 + checagens extras |
| POC-19 | V-09, V-18 (202, transições, `duracao_s`) |
| POC-20 | V-10, V-11, V-18 |
| POC-21 | V-12; `/app/versoes` lista data, origem, período, status, duração, vencedores e selo "Ativa" (navegador) |
| POC-22 | V-09 (compare: vencedores, MAPE, Δ p.p., soma12 e períodos, Δ%, holdouts, meses adicionados, células) |
| POC-23 | V-13; nota da faixa sem "com os dados do case" desde `95e4a7b` (iteração 1) |
| POC-24 | `config/brand.ts` (nome, slogan, cor, logo) consumido em `app/layout.tsx`, `app/page.tsx`, `app-sidebar.tsx`, `landing-sections.tsx`. Rebuild com marca trocada não foi executado |
| POC-25 | navegador `/app`: 5 KPIs (3 / 440 / 3 / 257 (3 produtos) / 85,0%) |
| POC-26 | V-06 (recálculo sem treino, validação de faixa na API), V-19. Tempo ≤ 1 s na tela não cronometrado |
| POC-27 | navegador: 11 colunas na ordem especificada; ordenação `(STATUS_ORDER, −necessidade)` em `planning.py:93` |
| POC-28 | navegador: fatos, legenda do gráfico (Vendido, teste, Previsão, faixa, Estoque projetado, Estoque de segurança), tabela mês a mês |
| POC-29 | `app/app/modelos/page.tsx:250-253` (período treino/teste e critério); vencedor = `select_best` (V-01). Toggle da legenda não exercitado |
| POC-30 | V-20 (selo some depois de salvar); diálogo com os 5 campos por produto (navegador) |
| POC-31 | V-08 pela UI: "Executando · máx. 60 s" e redirecionamento ao comparativo; "Tentar novamente" em `run-tracker.tsx:54` |
| POC-32 | checagem extra (API parada) |
| POC-33 | compose smoke (2 serviços, 127.0.0.1, `http://api:8000`, volume, uid ≠ 0); offline parcial (V-14) |
| POC-34 | health + logs estruturados (checagens extras) |
| POC-35 | checagens extras (API); "Nenhuma alteração"/"Re-treinar agora" em `edit-grid.tsx:128,204` |
| POC-36 | checagens extras (API); selo "Escolha manual" em `panel-table.tsx:132`, `product-detail.tsx:172` |
| POC-37 | código `lib/spreadsheet.ts:309-352` (arquivo, 3 abas, colunas), igual à referência. Download não exercitado. Ver lacuna 1 |
| POC-38 | código `panel-table.tsx:83,107`, `lib/format.ts:47` (NFD). Não exercitado na tela |
| POC-39 | checagens extras; limite também na gravação desde `95e4a7b` (iteração 1: h = 1 → `PUT` 13 = 422, 12 = 200) |
| POC-40 | V-16, V-18 |

## T18–T20 — "sem alterações"

`git log dev..HEAD` não tem commit `fix(poc): …` de T18, T19 ou T20: depois de T17 (`edbae2b`) vem só `bf1de6c` (docs em `.specs/`). O registro "sem alterações de código" está confirmado. O comportamento revisado nessas tasks foi reconferido de forma independente:
- T18 (grade): POC-35 na API;
- T19 (escolha manual): POC-36 na API e no painel;
- T20 (horizonte): POC-39 com h = 1, h = 4 → 422 e plano limitado a 12.

## Iteração 1 — correção `95e4a7b` (reverificação independente)

Diff conferido: `planning.py` (+`_horizon_problem`, chamado em `save_settings`) e `landing-numbers.tsx` (nota da faixa). Nenhum outro arquivo mudou.

| Gate / checagem | Resultado |
| --- | --- |
| Lint Py (`ruff check` + `ruff format --check`) | `All checks passed!` · `9 files already formatted` |
| Build Web (`bun run lint && bun run build`) | lint exit 0; `✓ Compiled successfully`, 8/8 páginas, exit 0 |
| POC-05 (`git diff dev --stat -- . ':!poc' ':!.specs'`) | vazio |
| Container com o fix | `grep _horizon_problem` no `planning.py` do container da api = 2 ocorrências; web `/` 200 |
| Lacuna 1 (POC-39), na stack do compose | ativa antes: `run-20260930T223723-e14c`, H = 3. `POST /runs` com h = 1 → 202, `executando → concluido` em 5,2 s, ativo, `horizonte_max = 12`. `PUT horizonte_meses = 13` → **422** `parametros.horizonte_meses: deve ser menor ou igual a 12`, e o valor gravado continua 3. `PUT 12` → **200**, com `/plan` usando 12. Restaurado: run anterior reativado (200) e H = 3 (200); `posicoes_demo` inalterado (true). Com a ativa h = 2, `PUT 24` → 200 |
| Lacuna 3 (POC-23), no navegador em `/` | nota: "Histórico 01/2022–12/2024 · acurácia medida no teste 01/2024–12/2024."; o texto "dados do case" não aparece mais |

Reclassificações acordadas com o autor e conferidas nas fontes:
- **Lacuna 4 (POC-16, slug vs rótulo): não é lacuna.** O exemplo normativo de POC-02 usa o slug (`"histórico insuficiente: suco_premium tem 30 meses; mínimo 36"`), e POC-16 só exige que a mensagem "nomeie produto e período". Nenhuma cláusula da spec exige o rótulo.
- **Lacuna 2 (POC-37, células de estoque vazias depois do mês H): comportamento da referência.** `~/Downloads/previsao-compras-local.html` (bloco de exportação, ~l. 609) usa `r ? Math.round(r.ini) : ''`, ou seja, também deixa em branco o mês sem linha de projeção. Fica só como nota de precisão da spec: POC-37 poderia citar isso de forma explícita.

Efeito colateral residual, sem impacto no resultado: um `horizonte_meses` gravado quando a ativa tinha h ≥ 2 (ex.: 24) continua gravado se depois for ativado um run com h = 1. Nesse caso `/plan` limita a 12 (`planning.py:81`) e o plano continua correto.

## Lacunas (ordem de prioridade)

Primeira rodada: as lacunas 1 (POC-39, limite só na leitura) e 3 (POC-23, nota "com os dados do case") foram **corrigidas em `95e4a7b`**. A lacuna 2 (POC-37) e a 4 (POC-16) foram reclassificadas (ver "Iteração 1"). Restam:

1. **POC-37 (nota de precisão da spec, sem mudança de código).** "Estoque inicial/final" fica vazio depois do mês H na aba "Previsão mensal", igual à referência. *Sugestão:* registrar esse comportamento no texto de POC-37.
2. **POC-39 (residual):** o valor gravado pode ficar acima do limite depois de ativar um run de horizonte menor; o plano limita na leitura. *Sugestão (opcional):* limitar também em `activate`.
3. **ACs só com evidência de código, não exercitados:**
   - POC-15: formato largo e os 5 formatos de período;
   - POC-24: rebuild com marca trocada;
   - POC-26: tempo de recálculo ≤ 1 s;
   - POC-29: toggle da legenda;
   - POC-37: download do export;
   - POC-38: filtro na tela.

   *Sugestão:* conferir no ensaio humano de V-17.
4. **Informativo.** O MAPE do Holt-Winters varia cerca de 1e-6 entre execuções (15,529689 no motor vs 15,529690 num run da stack). V-02 continua dentro da tolerância numa mesma execução (5,7e-14). Não há ação necessária, a não ser que se exija reprodutibilidade bit a bit.
5. **Higiene do worktree.** Há `reports/` e `.DS_Store` não rastreados na raiz. Estão fora dos commits, então POC-05 vale, mas não devem entrar num commit.
6. **Pendências humanas:** V-17 e a parte offline de V-14.

## Encaminhamento do autor (após a verificação)

- Lacuna 1 (POC-37): texto de POC-37 em `spec.md` passou a dizer que Estoque inicial/final ficam em branco nos meses além de `H`, como no HTML de referência. Sem mudança de código.
- Lacunas 2–6: sem ação nesta rodada (opcional, informativo ou verificação humana).
