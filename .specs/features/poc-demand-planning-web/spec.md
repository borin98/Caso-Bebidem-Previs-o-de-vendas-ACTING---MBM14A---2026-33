# POC Planejamento de Demanda Web — Especificação

**Feature:** `poc-demand-planning-web`
**Branch:** `feat/poc-html-rsys`
**Escopo:** Complexo (motor Python + API + web + empacotamento)
**Status:** Aprovado (2026-09-30): assunções A1–A17 confirmadas; **sem testes automatizados**; shadcn; **o mais simples possível**; **todo o POC na pasta nova `poc/`**; P2/P3 entram na primeira rodada; re-treino em até 60 s
**Referências:** `reference-chat.md` (chat + HTML de referência, Neogrid, UniSoma/Prognos), `context.md` (decisões do usuário)

---

## Problem Statement

A previsão de demanda da BebiBem existe hoje só como pacote Python, CLI batch e notebook (`bebibem-forecast`). Ela gera ~100 figuras e 13 tabelas CSV que só quem roda o terminal consegue ler. Founders e a área de negócio da RSYS precisam ver essa capacidade como um produto: um painel web com o mesmo apelo de plataformas como Neogrid e Prognos (menos estoque, menos erro, menos ruptura). Nele, o usuário carrega vendas, fecha o mês, re-treina os 9 modelos e recebe a recomendação de compra. O objetivo é sustentar a conversa comercial e validar o produto antes de investir em versão SaaS.

## Goals

- [ ] Demonstrar ponta a ponta, sem terminal e em ≤ 5 minutos, o roteiro landing → painel → fechar mês → re-treino → comparativo antes×depois → recomendação de compra.
- [ ] Re-treinar os 9 modelos do pacote para os 3 produtos do caso em ≤ 60 s, com limite rígido de 60 s por treino (POC-40).
- [ ] Todo número exibido na landing e no painel é rastreável a um campo retornado pela API (zero número inventado).
- [ ] Nada fora de `poc/` e `.specs/` é alterado: pacote `bebibem`, CLI, notebook, `tests/`, `pyproject.toml`, `uv.lock`, `docker/` e `README.md` da raiz ficam intactos (POC-05).

## Out of Scope

| Item | Motivo |
| --- | --- |
| Login, perfis, Auth.js / RSYS Auth API | Decisão do usuário: demo local sem login (desvio registrado do `rsys-frontend-stack`) |
| Deploy em Dokploy/nuvem, domínio, TLS | Decisão do usuário: execução local via Docker |
| Interface em inglês | Decisão do usuário: somente PT-BR (AD-007) |
| Banco de dados | Estado em arquivos versionados basta para POC de usuário único |
| Multi-tenant / múltiplos workspaces | POC de um único workspace de demonstração |
| Intervalos de previsão probabilísticos | Adiado desde a feature anterior; o POC mostra faixa ±MAD rotulada como erro médio histórico |
| Os 8 métodos JS do HTML de referência | Usuário escolheu os 9 modelos Python do pacote |
| Ciclo sazonal configurável | Modelos do pacote fixam m = 12 |
| Simulador financeiro / ROI / preço e custo | Usuário escolheu só métricas reais + capacidade de estoque |
| Assistente de IA, workflow S&OP, aprovação colaborativa | Features do Prognos fora do POC |
| Integração com ERP ou fontes externas | Entrada só por planilha e digitação |
| Alterar qualquer arquivo fora de `poc/` (pacote, CLI, notebook, testes, Docker e README existentes), inclusive refatorar a janela de holdout | Pedido do usuário: "deixe o arquivo do jupyter notebook; crie uma pasta nova para isso". CLI mantém holdout 2024 (AD-004/AD-011) |
| Testes automatizados (unit, integration, e2e) | Decisão do usuário: "sem testes (é apenas um POC)"; verificação pelo roteiro manual em `tasks.md` |
| Deduplicação de versões de dados idênticas | Simplificação: cada importação cria uma versão |
| Preenchimento automático de meses faltantes | Simplificação: série com lacuna é recusada (A13) |
| Logos/cases de clientes reais na landing | White-label neutro; sem prova social de terceiros |

---

## Assumptions & Open Questions

| # | Assunto | Default escolhido | Motivo | Confirmado? |
| --- | --- | --- | --- | --- |
| A1 | Significado de "capacidade de estoque por mês" | **Capacidade máxima de armazenagem por produto, em unidades**, um valor por produto válido para todos os meses. A posição de estoque (estoque atual, a receber) é uma entrada separada, como no HTML de referência | Usuário respondeu "por produto, em unidades"; o HTML de referência usa estoque atual para a necessidade de compra. As duas entradas coexistem | y |
| A2 | Uso da capacidade | Só alerta: badge "Excede capacidade" quando `disponível + necessidade > capacidade`, mais uma linha no gráfico. A capacidade não limita a recomendação | Limitar a compra muda a regra de negócio do caso; alerta preserva a regra e mostra o risco | y |
| A3 | Horizonte de previsão do POC | `horizon_years = 2` (24 meses) fixo por treino no P1 | O horizonte de cobertura vai até 24 meses e a cobertura olha 24 meses, como no HTML de referência | y |
| A4 | Prioridade das três entradas de dados | Upload de planilha e fechar mês = P1; editar grade = P2. **Todas (P1, P2 e P3) entram na primeira rodada de implementação** | O roteiro de demo depende de upload e fechamento; o usuário pediu P2/P3 já na primeira rodada | y |
| A5 | Acurácia | `acurácia = max(0; 100 − MAPE)` do modelo, 1 casa decimal; "n/d" quando MAPE não aplicável | Métrica comercial usual; deriva só de MAPE já calculado (AD-009) | y |
| A6 | Faixa de erro médio | Previsão ± MAD do holdout do modelo em uso, limite inferior 0, legenda "Erro médio histórico (não é intervalo de confiança)" | Usuário pediu número + faixa ±MAD | y |
| A7 | Estoque não informado | Produto sem estoque informado entra com estoque 0 e aviso, como no HTML de referência | Mantém o fluxo sem bloquear | y |
| A8 | Lead time 0 | Estoque de segurança usa `√max(L; 1)`, idêntico à referência | Fidelidade à referência validada no chat | y |
| A9 | Ativação de versão | Treino concluído com sucesso vira a versão ativa automaticamente; versões anteriores podem ser reativadas | Roteiro de demo: fechar mês e ver o novo resultado sem passo extra | y |
| A10 | Leitura de planilha | Arquivo lido e mapeado no navegador; a API recebe linhas normalizadas em JSON e revalida tudo | Mapeamento de colunas é interação de UI; a validação de negócio fica na API | y |
| A11 | Limites de entrada | Arquivo ≤ 5 MB; ≤ 50 000 linhas antes da agregação; ≤ 50 produtos; ≤ 240 meses por produto; valores inteiros entre 0 e 1 000 000 000 | Evita travar o navegador/treino; cobre com folga o caso (3 × 36) | y |
| A12 | Histórico mínimo | 36 meses por produto (24 de treino + 12 de teste) | `MIN_OBS_FOR_ML = 24` (`src/bebibem/config.py:19`) + holdout de 12 meses | y |
| A13 | Meses faltantes no meio da série | **Recusados** com 422 listando produto e meses faltantes; todos os produtos precisam terminar no mesmo mês | "O mais simples possível": sem interpolação no POC; fim desalinhado quebra o mês de fechamento comum | y |
| A14 | Posição de estoque do caso | **Valores aleatórios** por produto, com `m` = média mensal dos últimos 12 meses: estoque inteiro uniforme em `[0; 3m]` e a receber inteiro uniforme em `[0; m]`, gerados com semente 42 (os mesmos a cada carga do caso). **Lead time = 1** para todos. Rotulados "Valores fictícios gerados aleatoriamente para demonstração" | Pedido do usuário ("valores aleatórios e lead time 1"); semente fixa deixa a demo reprodutível | y |
| A15 | Nome do produto na UI | White-label **neutro**: padrão "Planejamento de Demanda", sem logo; nome, slogan, cor e logo configuráveis num único arquivo | Pedido do usuário ("deixe neutro") | y |
| A16 | Verificação | Sem testes automatizados; cada task fecha com lint/build e verificação manual; o fechamento é o roteiro V-01…V-20 em `tasks.md` | Decisão do usuário ("é apenas um POC") | y |
| A17 | Localização e janela móvel | Todo o POC em `poc/` (`poc/api/` FastAPI + motor + reposição; `poc/web/` Next.js; `poc/docker-compose.yml`), consumindo `bebibem` como biblioteca. Janela móvel só no motor do POC; CLI e notebook seguem com holdout 2024 e não são tocados | Pedido do usuário ("deixe o arquivo do jupyter notebook; crie uma pasta nova para isso") | y |

**Open questions:** nenhuma. Todas as assunções foram confirmadas pelo usuário em 2026-09-30.

---

## User Stories

### P1-A: Motor unificado com janela móvel ⭐ MVP

**User Story:** Como apresentador, quero que cada re-treino avalie os 9 modelos nos últimos 12 meses observados e preveja a partir do mês seguinte, para que fechar um mês novo gere um resultado honesto e atualizado.

**Why P1:** No pacote atual o holdout está preso ao ano de 2024 (`src/bebibem/config.py:20`) e a previsão ML começa em 2025-01 (`src/bebibem/forecast.py:121`). Fechar 2025-01 quebraria as duas regras. O POC resolve isso num motor próprio em `poc/api/`, sem tocar no pacote nem no notebook (A17).

**Acceptance Criteria:**

1. **POC-01** WHEN o motor do POC recebe histórico cujo último mês observado é `U` THEN SHALL usar como holdout os 12 meses `U−11 … U` e como treino todos os meses anteriores a `U−11`, para todos os 9 modelos. Para `data/raw` (`U` = 2024-12) o holdout SHALL ser 2024-01 … 2024-12.
2. **POC-02** WHEN algum produto tem menos de 36 meses observados THEN o motor SHALL recusar o treino com erro que nomeia cada produto e sua contagem (ex.: `"histórico insuficiente: suco_premium tem 30 meses; mínimo 36"`). Nenhuma versão de treino é marcada como concluída.
3. **POC-03** WHEN o treino conclui THEN cada produto SHALL ter uma linha por modelo para os 9 modelos (`ridge`, `random_forest`, `gradient_boosting`, `linear_normal_equation`, `exponential_loglinear`, `exponential_normal_equation`, `holt_winters_multiplicative`, `sarima`, `fourier_harmonic`), com MAD, MSE, RMSE, MAPE e MPE do holdout (AD-009). Modelo não aplicável SHALL aparecer com `aplicavel = false`, motivo em texto e sem métricas. O vencedor único SHALL ser o resultado de `select_best` sobre os modelos aplicáveis: menor MAPE, e empate < 0,5 p.p. decidido por menor MAD.
4. **POC-04** WHEN o treino conclui com `horizon_years = h` THEN cada modelo aplicável SHALL ter previsão para os `12 × h` meses `U+1 … U+12h`, todos os valores ≥ 0, e previsão do holdout para os 12 meses de teste.
5. **POC-05** WHEN o POC está implementado THEN `git diff dev --stat` SHALL mostrar alterações **somente em `poc/**` e `.specs/**`**. Nenhum arquivo fora dessas pastas (pacote `src/bebibem/`, `notebooks/`, `tests/`, `docker/`, `pyproject.toml`, `uv.lock`, `README.md` da raiz) é criado ou modificado, e o CLI mantém o holdout 2024.

**Independent Test:** Rodar o motor sobre `data/raw` e sobre o mesmo CSV com 2025-01 anexado. O holdout muda de 2024-01…2024-12 para 2024-02…2025-01 e a previsão passa a começar em 2025-02.

---

### P1-B: Plano de reposição (necessidade de compra) ⭐ MVP

**User Story:** Como gestor de compras, quero ver para cada produto quanto comprar, até quando e qual o risco, calculado a partir da previsão e do meu estoque, para decidir o pedido do mês.

**Why P1:** É o que transforma previsão em decisão: o núcleo do HTML de referência e a promessa "menos estoque, menos ruptura".

Notação: `f[i]` = previsão do modelo em uso no mês `U+1+i`; `H` = horizonte de cobertura (meses); `L` = lead time do produto, ou o padrão; `q` = múltiplo de compra do produto, ou o padrão; `z` = fator do nível de serviço; `D = estoque + a_receber`; `Dem = Σ f[0..H−1]`.

**Acceptance Criteria:**

1. **POC-06** WHEN o plano é calculado THEN o estoque de segurança SHALL ser `SS = z × RMSE_holdout × √max(L; 1)`, com `z` = 1,2816 / 1,6449 / 1,96 / 2,3263 para nível de serviço 90% / 95% / 97,5% / 99%.
2. **POC-07** WHEN o plano é calculado THEN a necessidade SHALL ser `N = max(0; Dem + SS − D)`. Se `N > 0`, `N` SHALL ser arredondada para cima ao múltiplo `q` (`N = ⌈N / q⌉ × q`).
3. **POC-08** WHEN o plano é calculado THEN a projeção SHALL listar, para `i = 0 … H−1`, `inicial_i`, `venda_prevista_i = f[i]` e `final_i = inicial_i − f[i]`, com `inicial_0 = D` e `inicial_{i+1} = final_i`, sem considerar a nova compra.
4. **POC-09** WHEN o plano é calculado THEN a cobertura SHALL ser o número de meses (1 casa decimal) que `D` cobre ao consumir `f[0 … 12h−1]` em ordem. Mês com `f[i] ≤ 0` conta como coberto; o mês que esgota o disponível conta fração `restante / f[i]`. Se `D` não se esgota no horizonte previsto, a cobertura SHALL ser exibida como `"> 12h"` (ex.: `"> 24"`).
5. **POC-10** WHEN existe um primeiro índice `k` com `final_k < SS` (ou `D < SS`, caso em que `k = 0`) THEN "comprar até" SHALL ser o mês `U+1+⌊k − L⌋`, exibido como `"Imediato"` quando `⌊k − L⌋ ≤ 0`. WHEN esse índice não existe THEN SHALL exibir `"–"`.
6. **POC-11** WHEN o plano é calculado THEN a situação SHALL ser, nesta ordem: `ruptura` se `N > 0` e algum `final_i < 0`; `comprar` se `N > 0`; `excesso` se `D > 2 × (Dem + SS)` e `Dem > 0`; senão `adequado`. Rótulos: "Ruptura prevista", "Comprar", "Excesso", "Adequado".
7. **POC-12** WHEN o produto tem capacidade de armazenagem `C` informada e `D + N > C` THEN o plano SHALL marcar `excede_capacidade = true` e o painel SHALL exibir o badge "Excede capacidade". A situação e `N` não mudam. WHEN `C` não foi informada THEN `excede_capacidade = null` e nenhum badge aparece.
8. **POC-13** WHEN o plano é exibido THEN cada produto SHALL mostrar o erro médio do modelo em uso: MAD do holdout (unidades, 1 casa), MAPE (%, 1 casa) e acurácia `max(0; 100 − MAPE)` (%, 1 casa; "n/d" se MAPE não aplicável).

**Independent Test:** Com o caso (posições aleatórias de A14 lidas em `GET /settings`, L = 1, q = 1, z = 1,6449, H = 3), calcular à mão SS, N, projeção, cobertura, comprar até e situação a partir de `f` e RMSE retornados pela API. O plano retornado precisa bater exatamente.

---

### P1-C: Landing comercial white-label ⭐ MVP

**User Story:** Como founder da RSYS, quero abrir a demo numa página com cara de produto (proposta de valor, como funciona, números reais do case), para apresentar a solução a prospects antes de entrar no painel.

**Why P1:** O público do POC é negócio/founders; a landing é a moldura comercial (estilo Neogrid/Prognos).

**Acceptance Criteria:**

1. **POC-23** WHEN o visitante abre `/` THEN a página SHALL exibir, nesta ordem: hero (título, subtítulo, CTA primário "Ver demonstração" que leva a `/app` e CTA secundário "Como funciona" que rola até a seção); faixa de números; seção "O problema" (3 dores); seção "Como funciona" (3 passos: dados → competição de modelos → recomendação de compra); seção "Por que confiar" (métricas abertas, re-treino a cada fechamento, versões auditáveis); CTA final "Abrir o painel".
2. **POC-23** WHEN há versão ativa THEN a faixa de números SHALL mostrar, todos lidos da API: nº de modelos avaliados por produto, acurácia média dos vencedores (média simples entre produtos, POC-13), meses de histórico, nº de produtos e a data do último treino. WHEN não há versão ativa THEN a faixa SHALL mostrar placeholders de carregamento e o texto "Treinamento inicial em andamento".
3. **POC-23** WHEN a landing é renderizada THEN nenhum percentual, valor monetário ou nome de cliente SHALL aparecer como texto fixo. Todo número vem da API.
4. **POC-24** WHEN o arquivo de marca (nome, slogan, cor primária, logo) é alterado e a web é reconstruída THEN landing e painel SHALL exibir os novos valores sem outra mudança de código. O padrão SHALL ser o nome "Planejamento de Demanda", sem logo de terceiros.

**Independent Test:** Abrir `/` com a stack local: todas as seções aparecem, cada número bate com `GET /api/v1/overview`, e o CTA leva a `/app`.

---

### P1-D: Painel de reposição ⭐ MVP

**User Story:** Como gestor, quero um painel com KPIs, a lista de produtos por prioridade e o detalhe de cada produto, para ver em segundos onde há ruptura e quanto comprar.

**Why P1:** É a tela principal da demo.

**Acceptance Criteria:**

1. **POC-25** WHEN o usuário abre `/app` com versão ativa THEN o painel SHALL exibir 5 KPIs: produtos analisados; unidades previstas nos próximos `H` meses (Σ `Dem`); produtos com ruptura prevista; unidades a comprar (Σ `N`) com o nº de produtos com `N > 0`; acurácia média dos modelos em uso.
2. **POC-26** WHEN o usuário altera horizonte de cobertura (1–24, inteiro), lead time padrão (0–12, passo 0,5), nível de serviço (90 / 95 / 97,5 / 99%) ou múltiplo de compra padrão (inteiro ≥ 1) THEN KPIs, tabela e detalhe SHALL recalcular em até 1 s, sem novo treino. Os valores SHALL persistir como padrão do workspace. Valor fora da faixa SHALL ser recusado com mensagem no campo, mantendo o último valor válido.
3. **POC-26** WHEN o rótulo "Lead time" aparece na tela (parâmetros do painel, "Estoque e capacidade", detalhe do produto, fechar mês) THEN SHALL haver um ícone de ajuda que exibe: "Lead time é o tempo, em meses, entre fazer o pedido de compra e a mercadoria chegar ao estoque. É usado no estoque de segurança e no prazo 'Comprar até'." Em "Estoque e capacidade", o mesmo texto SHALL aparecer também fixo abaixo do campo.
4. **POC-27** WHEN o painel é exibido THEN a tabela de produtos SHALL ter as colunas: Produto, Modelo em uso, MAPE, Previsão `H`m, Estoque + a receber, Cobertura (barra), Meses cobertos, Est. segurança, Comprar, Comprar até, Situação. A ordem SHALL ser por situação (ruptura, comprar, adequado, excesso) e, dentro dela, por necessidade decrescente.
5. **POC-28** WHEN o usuário seleciona um produto THEN o detalhe SHALL exibir: fatos (previsão `H`m, estoque + a receber, estoque de segurança, necessidade, comprar até, lead time · múltiplo, MAD, MAPE, acurácia); gráfico com vendido (histórico), previsão no holdout, previsão futura, faixa ±MAD (POC-13), estoque projetado, estoque de segurança e capacidade (se informada); tabela da projeção mês a mês (POC-08), com as linhas de estoque final < 0 destacadas.
6. **POC-30** WHEN o usuário abre "Estoque e capacidade" no painel THEN SHALL poder editar, por produto, estoque atual, a receber, lead time (vazio = padrão), múltiplo de compra (vazio = padrão) e capacidade de armazenagem (vazio = sem limite). Salvar SHALL recalcular o plano sem re-treino. Valores negativos ou não numéricos SHALL ser recusados com mensagem no campo. WHEN as posições ainda são as geradas para a demo (A14) THEN a tela e o painel SHALL mostrar o selo "Valores fictícios gerados aleatoriamente para demonstração", que some depois que o usuário salva posições ou importa uma planilha com estoque.
7. **POC-32** WHEN a API não responde ou responde 5xx THEN a web SHALL exibir o aviso "Serviço de previsão indisponível" com botão "Tentar novamente", sem mostrar números antigos como atuais.

**Independent Test:** Com o caso carregado, mudar o nível de serviço de 95% para 99%: SS e necessidade sobem e a ordem da tabela reflete a nova situação, sem treino novo (a lista de versões não muda).

---

### P1-E: Comparativo de modelos ⭐ MVP

**User Story:** Como founder, quero mostrar que 9 modelos competem por produto e que o vencedor é escolhido por critério objetivo, para transmitir rigor técnico.

**Why P1:** Diferencial "Inteligente/transparente" contra planilha.

**Acceptance Criteria:**

1. **POC-29** WHEN o usuário abre `/app/modelos` e escolhe um produto THEN a tabela SHALL listar os 9 modelos com nome em PT-BR, família (Machine learning / Regressão clássica / Séries temporais), MAPE, MAD, RMSE, MSE, MPE e acurácia, na ordem de ranking do critério (POC-03), com o vencedor destacado como "Vencedor". Modelos não aplicáveis ficam no fim, com o motivo.
2. **POC-29** WHEN a tabela é exibida THEN SHALL mostrar o período de treino e de teste (ex.: "Treino até 12/2023 · Teste 01/2024–12/2024") e o texto do critério: "Menor MAPE; empate abaixo de 0,5 p.p. decidido pelo menor MAD. MPE positivo indica que o modelo subestimou as vendas."
3. **POC-29** WHEN o usuário liga ou desliga modelos na legenda THEN o gráfico do holdout SHALL mostrar o real e as previsões dos modelos visíveis nos 12 meses de teste.
4. **POC-29** WHEN a tabela de modelos é exibida THEN SHALL mostrar, para cada um dos 9 modelos, sua fórmula em **LaTeX renderizado localmente**. As fórmulas SHALL descrever a forma de ajuste realmente executada pelo motor do POC; a renderização SHALL usar ativos empacotados na aplicação, sem CDN nem recursos externos em tempo de execução, preservando POC-33.


**Independent Test:** Para o caso, o vencedor destacado de cada produto é igual ao `select_best` aplicado à tabela de métricas retornada pela API. Abrir `/app/modelos` e conferir as 9 fórmulas tipografadas; a página não pode exibir comandos LaTeX crus nem solicitar recursos fora de `127.0.0.1`.

---

### P1-F: Carga de dados ⭐ MVP

**User Story:** Como analista, quero carregar minha planilha de vendas (ou os dados do caso), conferir as colunas e gerar uma nova versão dos dados, para rodar a previsão sobre a minha realidade.

**Why P1:** Sem carga de dados não há demo para o prospect.

**Acceptance Criteria:**

1. **POC-14** WHEN a API sobe com o diretório de dados vazio THEN SHALL criar a versão de dados `caso` a partir de `data/raw/demanda_loja_propria.csv`, gerar as posições de estoque aleatórias de A14 (semente 42, lead time 1) e iniciar o treino inicial. WHEN o diretório já tem dados THEN SHALL manter tudo como está.
2. **POC-15** WHEN o usuário solta ou escolhe um arquivo `.xlsx`, `.xls`, `.csv` ou `.txt` de até 5 MB THEN a web SHALL: ler a primeira aba (com seletor quando há várias); detectar o formato largo (coluna `ano*` + ≥ 6 colunas de mês) e convertê-lo para uma linha por produto e mês; auto-mapear as colunas Produto*, Período*, Quantidade vendida*, Estoque, A receber, Lead time, Múltiplo de compra pelo nome; permitir ajuste manual; e mostrar prévia das 5 primeiras linhas. Formatos de período aceitos: `2024-01`, `01/2024`, `jan/24`, `202401`, data.
3. **POC-15** WHEN o usuário confirma o mapeamento THEN a web SHALL somar as quantidades de linhas com mesmo produto e mês e enviar as linhas normalizadas à API. A API SHALL criar uma nova versão de dados (`origem = importacao`) e responder com id, produtos, período e avisos. Cada importação cria uma versão nova, mesmo com conteúdo igual a uma anterior.
4. **POC-16** WHEN as linhas violam alguma regra (campo obrigatório vazio, período não reconhecido, quantidade negativa ou não numérica, mês faltante no meio da série, produtos terminando em meses diferentes, limites de A11, histórico < 36 meses) THEN a API SHALL recusar com HTTP 422 e mensagem PT-BR que nomeia produto e período de cada problema (até 20 itens, depois "… e mais N"). Nenhuma versão é criada.
5. **POC-17** WHEN o usuário clica "Baixar planilha modelo" THEN a web SHALL gerar um `.xlsx` com a aba `Vendas` (dados do caso no formato longo) e a aba `Instruções` (coluna, obrigatória, como preencher; a linha "Lead time" traz o texto de ajuda de POC-26). WHEN o usuário clica "Usar dados do caso" THEN SHALL criar uma versão `caso` com os dados de `data/raw` e as posições aleatórias de A14 (mesmos valores, semente 42) e iniciar o treino.

**Independent Test:** Baixar a planilha modelo e reenviá-la sem mudanças: a API cria uma versão `importacao` com os mesmos 3 produtos e o período 2022-01…2024-12. Apagar uma célula de quantidade e reenviar: 422 com produto e período citados.

---

### P1-G: Fechar mês e re-treinar ⭐ MVP

**User Story:** Como gestor, quero informar as vendas do mês que fechou e ver os modelos re-treinados na hora, para mostrar ao prospect o ciclo mensal de planejamento.

**Why P1:** É o momento "uau" da demo: dado novo → modelo novo → decisão nova.

**Acceptance Criteria:**

1. **POC-18** WHEN o usuário abre "Fechar mês" THEN o formulário SHALL mostrar o mês `U+1` da versão de dados ativa, fixo e não editável, com um campo obrigatório de vendas por produto (inteiro 0–1 000 000 000) e campos opcionais de estoque ao fim do mês e a receber. WHEN salvo THEN a API SHALL criar a versão `origem = fechamento` (pai = versão ativa) com `U+1` anexado, atualizar as posições informadas e iniciar o treino.
2. **POC-18** WHEN falta valor de vendas para algum produto, ou o valor é negativo ou não inteiro THEN o salvamento SHALL ser bloqueado com mensagem no campo, e a API (se chamada) SHALL responder 422 sem criar versão.
3. **POC-19** WHEN um treino é iniciado THEN a API SHALL responder HTTP 202 com status `na_fila`. O status SHALL seguir só as transições `na_fila → executando → concluido` ou `na_fila → executando → falhou`. `concluido` registra duração em segundos; `falhou` registra mensagem PT-BR.
4. **POC-20** WHEN um treino está `na_fila` ou `executando` e outro é pedido (inclusive via fechar mês ou importação com treino) THEN a API SHALL responder HTTP 409 "Já existe um treinamento em andamento", sem criar versão de dados nem de treino.
5. **POC-20** WHEN a API reinicia com treino `na_fila` ou `executando` THEN esse treino SHALL passar a `falhou` com a mensagem "Interrompido pelo reinício do serviço". A versão ativa não muda.
6. **POC-20** WHEN um treino falha THEN a versão ativa SHALL continuar a anterior, e a versão de dados criada SHALL ficar disponível para novo treino.
7. **POC-40** WHEN um treino roda por mais de 60 s THEN a API SHALL encerrar o processo do treino, marcá-lo `falhou` com "Tempo limite de 60 s excedido", manter a versão ativa e liberar novo treino imediatamente. WHEN o treino é o do caso (3 produtos, 36 a 48 meses) THEN SHALL concluir em ≤ 60 s, com `duracao_s` registrado.
8. **POC-31** WHEN um treino está em andamento THEN a web SHALL mostrar o status, o tempo decorrido (atualizado a cada ≤ 2 s) e o limite "máx. 60 s", e desabilitar os botões que iniciam treino. WHEN conclui THEN SHALL levar ao comparativo antes×depois (POC-22) da versão anterior contra a nova. WHEN falha THEN SHALL mostrar a mensagem de erro e o botão "Tentar novamente".

**Independent Test:** Fechar 2025-01 com vendas quaisquer: surge o status `executando` e, ao concluir, o comparativo mostra holdout 02/2024–01/2025 na versão nova contra 01/2024–12/2024 na anterior.

---

### P1-H: Versões e comparativo antes×depois ⭐ MVP

**User Story:** Como founder, quero ver o histórico de treinos, comparar dois treinos e reativar um anterior, para mostrar governança e rastreabilidade (estilo "histórico de aderência").

**Why P1:** Usuário escolheu versão + comparativo + ativar.

**Acceptance Criteria:**

1. **POC-21** WHEN o usuário abre `/app/versoes` THEN SHALL ver os treinos do mais novo ao mais antigo, com: data, origem dos dados (caso / importação / fechamento / edição), período dos dados, status, duração, vencedor por produto e o selo "Ativa" na versão ativa.
2. **POC-21** WHEN o usuário ativa um treino `concluido` THEN ele SHALL virar a versão ativa, e landing, painel e modelos SHALL refletir esse treino. WHEN tenta ativar um treino não concluído THEN a API SHALL responder 409 e a web não SHALL oferecer a ação.
3. **POC-21** WHEN um treino conclui com sucesso THEN SHALL virar a versão ativa automaticamente (A9).
4. **POC-22** WHEN o usuário compara o treino base B com o treino alvo A THEN SHALL ver, por produto: vencedor B e A; MAPE B, MAPE A e Δ em p.p. (A − B); soma dos 12 primeiros meses previstos em B e em A, com os períodos, e Δ% `(A − B) / B × 100` ("n/d" se B = 0); períodos de holdout de cada um. Do lado dos dados: meses adicionados e nº de células alteradas de B para A.

**Independent Test:** Após fechar um mês, comparar o treino anterior com o novo: meses adicionados = 1 e o Δ de MAPE bate com a diferença das duas tabelas de métricas.

---

### P1-I: Execução local ⭐ MVP

**User Story:** Como apresentador, quero subir a demo com um comando no meu notebook, sem internet durante a apresentação, para não depender de infraestrutura.

**Why P1:** Usuário escolheu Docker local sem login.

**Acceptance Criteria:**

1. **POC-33** WHEN o POC é empacotado THEN SHALL existir **exatamente duas imagens Docker próprias**, uma por aplicação: `poc/api/Dockerfile` (só a FastAPI) e `poc/web/Dockerfile` (só o Next.js). Ambas SHALL ser orquestradas por **um único `poc/docker-compose.yml`**, com os serviços `api` e `web` e nenhum outro. As imagens `pipeline` e `jupyter` (AD-005) não entram nesse compose e não são alteradas.
2. **POC-33** WHEN o apresentador roda `docker compose up --build` dentro de `poc/` THEN a web SHALL ficar acessível em `http://127.0.0.1:3000` e a API em `http://127.0.0.1:8000`, ambas publicadas só em 127.0.0.1. A web SHALL falar com a API pela rede interna do compose (`http://api:8000`). Os dados SHALL persistir no volume nomeado `poc-data` entre `down`/`up` (zerados só com `docker compose down -v`), e os dois containers SHALL rodar como usuário não-root.
3. **POC-33** WHEN a stack está no ar e sem acesso à internet THEN todas as telas SHALL funcionar (sem fontes, scripts ou bibliotecas carregados de CDN em tempo de execução).
4. **POC-34** WHEN a API recebe `GET /api/v1/health` THEN SHALL responder 200 `{"status": "ok"}`. WHEN um treino muda de status THEN a API SHALL registrar uma linha de log estruturado com `run_id`, `dataset_id`, `status` e `duracao_s` (quando houver).

**Independent Test:** Desligar o Wi-Fi, subir a stack e rodar o roteiro da demo completo.

---

### P2-J: Editar grade no navegador

**User Story:** Como analista, quero corrigir valores na grade produto × mês antes de re-treinar, para tratar outliers sem editar a planilha.

**Why P2:** Refinamento do fluxo de dados; a demo principal usa upload e fechamento.

**Acceptance Criteria:**

1. **POC-35** WHEN o usuário edita células da grade da versão ativa e salva THEN a API SHALL criar a versão `origem = edicao` (pai = ativa) com as células alteradas, e a web SHALL oferecer "Re-treinar agora". Valores negativos ou não inteiros SHALL ser recusados na célula.
2. **POC-35** WHEN o usuário salva sem alterar nenhuma célula THEN nenhuma versão SHALL ser criada, e a web SHALL informar "Nenhuma alteração".

---

### P2-K: Troca manual de modelo

**User Story:** Como gestor, quero escolher manualmente o modelo de um produto, para aplicar meu conhecimento de negócio quando o vencedor não me convence.

**Why P2:** Presente no HTML de referência; não é necessário ao roteiro principal.

**Acceptance Criteria:**

1. **POC-36** WHEN o usuário escolhe um modelo aplicável diferente do vencedor para um produto no treino ativo THEN plano, KPIs e detalhe SHALL usar a previsão, o RMSE e o MAD desse modelo, exibindo o selo "Escolha manual". A escolha SHALL persistir para esse treino.
2. **POC-36** WHEN outro treino é ativado THEN as escolhas manuais do treino anterior NÃO SHALL se aplicar a ele; o novo treino usa os vencedores.

---

### P2-L: Exportar Excel e filtrar

**User Story:** Como gestor, quero exportar o resultado e filtrar a tabela, para levar a recomendação para a reunião de compras.

**Why P2:** Presente na referência; não é necessário ao roteiro principal.

**Acceptance Criteria:**

1. **POC-37** WHEN o usuário clica "Exportar para Excel" THEN a web SHALL baixar `previsao_necessidade_compra.xlsx` com as abas: `Resumo` (Produto, Modelo, MAPE (%), Previsão H meses, Estoque, A receber, Meses cobertos, Estoque de segurança, Necessidade de compra, Comprar até, Situação); `Previsão mensal` (Produto, Mês, Venda prevista, Estoque inicial, Estoque final, para `max(12; H)` meses; como a projeção cobre só `H` meses, Estoque inicial e Estoque final ficam em branco nos meses além de `H`, como no HTML de referência); `Comparativo de modelos` (Produto, Modelo, Escolhido, MAPE (%), MAD, RMSE, MPE (%)). Os valores SHALL ser os mesmos exibidos na tela.
2. **POC-38** WHEN o usuário digita no filtro ou marca "Só com necessidade" THEN a tabela SHALL mostrar só os produtos cujo nome contém o texto (sem diferenciar acento e maiúscula) e, se marcado, com `N > 0`. Sem resultados, SHALL exibir "Nenhum produto corresponde ao filtro". Os KPIs continuam somando todos os produtos.

---

### P3-M: Horizonte de treino selecionável

**User Story:** Como apresentador, quero escolher 1, 2 ou 3 anos de previsão ao re-treinar, para mostrar planejamento de longo prazo.

**Acceptance Criteria:**

1. **POC-39** WHEN o usuário inicia um treino com horizonte de 1, 2 ou 3 anos THEN o treino SHALL prever `12 × h` meses. O horizonte de cobertura do painel SHALL ficar limitado a `min(24; 12 × h)`, e a cobertura a `12 × h`. Outro valor SHALL ser recusado com 422.

---

## Edge Cases

- WHEN a planilha tem várias linhas do mesmo produto e mês THEN as quantidades SHALL ser somadas antes do envio (referência), e a prévia SHALL informar quantas linhas foram agregadas.
- WHEN linhas têm período não reconhecido THEN SHALL ser ignoradas, com aviso "N linhas ignoradas por período não reconhecido". WHEN todas são ignoradas THEN a importação SHALL ser bloqueada com a lista dos formatos aceitos.
- WHEN a aba selecionada está vazia THEN a web SHALL exibir "A aba selecionada está vazia".
- WHEN o arquivo passa de 5 MB ou não é planilha legível THEN a web SHALL recusar antes de enviar, com mensagem.
- WHEN um produto tem valor 0 em meses do holdout THEN MAPE e MPE SHALL ignorar esses meses (regra de `models.metrics`), e a nota do modelo SHALL indicar quantos zeros foram ignorados.
- WHEN o histórico tem valores ≤ 0 THEN os modelos exponenciais e o Holt-Winters multiplicativo SHALL ficar não aplicáveis, com motivo, sem impedir o vencedor entre os demais.
- WHEN nenhum modelo tem MAPE aplicável para um produto THEN o treino SHALL falhar com mensagem que nomeia o produto.
- WHEN a previsão de algum modelo sai negativa THEN SHALL ser truncada em 0 e o treino SHALL registrar um aviso (comportamento atual de `forecast.py`).
- WHEN `Dem = 0` THEN a situação nunca SHALL ser `excesso` (POC-11), e a barra de cobertura SHALL ficar vazia.
- WHEN estoque e a receber não foram informados para um produto THEN `D = 0` e o painel SHALL exibir o aviso "sem estoque informado, considerado zero" (A7).
- WHEN a versão ativa é trocada durante um treino em andamento THEN a troca SHALL ser permitida, e o treino, ao concluir, SHALL virar ativo (A9).
- WHEN a comparação usa o mesmo treino como base e alvo THEN a web SHALL impedir a seleção.
- WHEN o JSON armazenado de uma versão está corrompido ou ausente THEN a API SHALL responder 500 com código `armazenamento_invalido`, sem apagar arquivos, e a web SHALL mostrar o aviso de POC-32.
- WHEN a série de um produto tem mês faltante no meio THEN a importação SHALL ser recusada (POC-16, A13), listando os meses faltantes.

---

## Implicit-Requirement Dimensions Sweep

| Dimensão | Cobertura |
| --- | --- |
| Validação de entrada e limites | POC-15, POC-16, POC-18, POC-26, POC-30, POC-35, POC-39; limites em A11 |
| Falha / falha parcial | POC-19, POC-20 (falha mantém a ativa; dados preservados), POC-40 (limite de 60 s encerra o processo e libera novo treino), POC-32; escrita atômica em design |
| Idempotência / retry / duplicidade | POC-20 (409 em treino concorrente), POC-35 (salvar sem alteração não cria versão); importações repetidas criam versões novas por decisão de simplicidade (Out of Scope) |
| Autenticação e rate limit | N/A porque a demo é local, usuário único, publicada só em 127.0.0.1 (POC-33); decisão do usuário |
| Concorrência / ordem | POC-20 (um treino por vez); troca de ativa durante treino definida nos Edge Cases |
| Ciclo de vida / expiração dos dados | Versões imutáveis e mantidas indefinidamente no volume; sem expiração no POC. Apagar = remover o volume (documentado no README) |
| Observabilidade | POC-34 (health + log estruturado por transição de treino) |
| Falha de dependência externa | POC-33 (sem CDN em execução); POC-32 (API indisponível na web) |
| Integridade de transições de estado | POC-19 (transições permitidas), POC-20 (recuperação no reinício), POC-21 (só `concluido` ativa) |

---

## Requirement Traceability

| ID | Story | Fase | Status |
| --- | --- | --- | --- |
| POC-01 | P1-A Motor | Execute | Implemented |
| POC-02 | P1-A Motor | Execute | Implemented |
| POC-03 | P1-A Motor | Execute | Implemented |
| POC-04 | P1-A Motor | Execute | Implemented |
| POC-05 | P1-A Motor | Execute | Implemented |
| POC-06 | P1-B Reposição | Execute | Implemented |
| POC-07 | P1-B Reposição | Execute | Implemented |
| POC-08 | P1-B Reposição | Execute | Implemented |
| POC-09 | P1-B Reposição | Execute | Implemented |
| POC-10 | P1-B Reposição | Execute | Implemented |
| POC-11 | P1-B Reposição | Execute | Implemented |
| POC-12 | P1-B Reposição | Execute | Implemented |
| POC-13 | P1-B Reposição | Execute | Implemented |
| POC-14 | P1-F Carga | Execute | Implemented |
| POC-15 | P1-F Carga | Execute | Implemented |
| POC-16 | P1-F Carga | Execute | Implemented |
| POC-17 | P1-F Carga | Execute | Implemented |
| POC-18 | P1-G Fechar mês | Execute | Implemented |
| POC-19 | P1-G Fechar mês | Execute | Implemented |
| POC-20 | P1-G Fechar mês | Execute | Implemented |
| POC-21 | P1-H Versões | Execute | Implemented |
| POC-22 | P1-H Versões | Execute | Implemented |
| POC-23 | P1-C Landing | Execute | Implemented |
| POC-24 | P1-C Landing | Execute | Implemented |
| POC-25 | P1-D Painel | Execute | Implemented |
| POC-26 | P1-D Painel | Execute | Implemented |
| POC-27 | P1-D Painel | Execute | Implemented |
| POC-28 | P1-D Painel | Execute | Implemented |
| POC-29 | P1-E Modelos | Execute | Implemented |
| POC-30 | P1-D Painel | Execute | Implemented |
| POC-31 | P1-G Fechar mês | Execute | Implemented |
| POC-32 | P1-D Painel | Execute | Implemented |
| POC-33 | P1-I Execução | Execute | Implemented |
| POC-34 | P1-I Execução | Execute | Implemented |
| POC-35 | P2-J Grade | Execute | Implemented |
| POC-36 | P2-K Modelo manual | Execute | Implemented |
| POC-37 | P2-L Exportar/filtrar | Execute | Implemented |
| POC-38 | P2-L Exportar/filtrar | Execute | Implemented |
| POC-39 | P3-M Horizonte | Execute | Implemented |
| POC-40 | P1-G Fechar mês | Execute | Implemented |

**Coverage:** 40 total, 40 mapeados para tasks (ver `tasks.md`), 0 sem mapeamento.

---

## Success Criteria

- [ ] Roteiro da demo (landing → painel → fechar mês → re-treino → comparativo → plano) executado por uma pessoa de negócio, sem terminal, em ≤ 5 minutos.
- [ ] Re-treino dos 9 modelos × 3 produtos do caso concluído em ≤ 60 s no notebook do apresentador, com limite rígido de 60 s por treino (POC-40).
- [ ] Carregamento de `/` e `/app` ≤ 3 s com a stack local já no ar.
- [ ] 0 número fixo no código da landing/painel (checado no review: todo valor vem de campo da API).
- [ ] `git diff dev --stat` com alterações somente em `poc/**` e `.specs/**` (POC-05).
- [ ] Roteiro de verificação manual de `tasks.md` (valores esperados do caso) conferido item a item antes da demo (A16).
- [ ] Demo funciona sem internet (POC-33).
