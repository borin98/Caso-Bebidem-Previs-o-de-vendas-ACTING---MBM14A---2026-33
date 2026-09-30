# POC Planejamento de Demanda Web — Contexto

**Gathered:** 2026-09-30
**Spec:** `.specs/features/poc-demand-planning-web/spec.md`
**Status:** Aprovado com ajustes (2026-09-30)

---

## Feature Boundary

POC comercial white-label, rodando local em Docker, que expõe o motor de previsão do pacote `bebibem` numa web com cara de produto:

- landing comercial;
- painel de reposição com necessidade de compra;
- comparativo dos 9 modelos;
- carga de planilha;
- fechar mês com re-treino;
- versões com comparativo antes×depois e reativação.

Público: founders e área de negócio da RSYS, apresentando para prospects. Sem login, sem deploy e sem banco.

---

## Implementation Decisions

### Arquitetura e stack (pergunta "Arquitetura")

- **Next.js (App Router) + shadcn/ui + Tailwind + Bun no front e FastAPI no back.** O usuário escolheu isso no lugar de HTML único ou Pyodide.
- O front segue o `rsys-frontend-stack` (Bun/Bunx, Tailwind, **shadcn via MCP**, REST, TanStack Query, sem tRPC), **exceto**:
  - Auth.js: o POC não tem login (ver Hospedagem);
  - Zod: tipos TypeScript bastam ("o mais simples possível");
  - linter: o padrão do `create-next-app`.
- O back segue o espírito do `rsys-fastapi-guidelines` (schemas Pydantic de entrada ≠ saída, erro de negócio com handler, código em inglês e docs em PT-BR), mas **plano**: módulos em `poc/api/src/poc_api/`, sem Routers/Services/Repositories separados e sem SQLModel.

### Localização do código (pergunta "Repo")

- **Pasta nova `poc/` neste repositório** (pedido do usuário: "deixe o arquivo do jupyter notebook; crie uma pasta nova para isso"):
  - `poc/api/`: FastAPI, projeto uv próprio que depende de `bebibem` por caminho;
  - `poc/web/`: Next.js;
  - `poc/docker-compose.yml`;
  - `poc/README.md`.
- Nada fora de `poc/` e `.specs/` é criado ou alterado: pacote, CLI, notebook, testes, `docker/`, `pyproject.toml` e `README.md` da raiz.

### Entrada de dados (pergunta "Re-treino", múltipla escolha)

- As três entradas foram escolhidas: **upload de planilha**, **fechar mês (append)** e **editar grade no navegador**.
- Prioridade (A4): upload e fechar mês = P1; grade = P2. **Todas entram na primeira rodada** (pedido do usuário).
- O upload segue o HTML de referência: `.xlsx/.xls/.csv`, formato longo ou largo (jan–dez), mapeamento automático de colunas com ajuste manual, colunas opcionais de estoque, a receber, lead time e múltiplo.

### Modelos (pergunta "Modelos")

- **Os 9 modelos + vencedor único**: Ridge, Random Forest, Gradient Boosting, regressão linear (equação normal), exponencial log-linear, exponencial (equação normal), Holt-Winters multiplicativo, SARIMA e harmônicos de Fourier.
- Critério AD-009 (menor MAPE; empate < 0,5 p.p. por menor MAD).
- O vencedor único, hoje só no notebook, é calculado pelo motor do POC (`poc/api/src/poc_api/engine.py`), que usa as funções públicas de `bebibem` sem alterar pipeline, CLI ou notebook (A17).

### Versões (pergunta "Versões")

- **Versão + comparativo + ativar**: cada treino é imutável (dados + métricas + previsão), com tela antes×depois e reativação de versão anterior.

### Experiência (pergunta "Experiência")

- **Landing + app demo**: hero comercial com proposta de valor e números reais do case, depois o painel funcional. Inspiração declarada: Neogrid e UniSoma/Prognos.

### Marca (pergunta "Marca")

- **White-label neutro** (confirmado: "deixe neutro"): nome padrão "Planejamento de Demanda", sem logo, sem marca RSYS nem BebiBem na moldura; nome, slogan, cor e logo configuráveis num arquivo único. Os produtos do caso aparecem pelo nome dos dados (Suco Premium, Geleia de frutas, Doce de frutas).

### Hospedagem (pergunta "Hospedagem")

- **Local Docker, sem login**, publicado em 127.0.0.1. Nenhuma ação externa (deploy) faz parte do POC.
- **Empacotamento (pedido do usuário):** uma imagem Docker para a FastAPI (`poc/api/Dockerfile`), uma para o Next.js (`poc/web/Dockerfile`) e ambas em **`poc/docker-compose.yml`**. `docker compose up --build` dentro de `poc/` sobe o POC inteiro.
- **Entrega:** somente na branch `feat/poc-html-rsys`; sem PR ("não precisa, deixe apenas na branch").

### Impacto de negócio (pergunta "Impacto", resposta livre)

- Resposta: "Métricas reais e o usuário informa capacidade de estoque por mês + mostra o erro médio da predição".
- Capacidade: **por produto, em unidades** (pergunta "Capacidade").
- Erro médio: **número + faixa ±MAD** (pergunta "Erro médio"), com MAD e MAPE em cartões e faixa sombreada rotulada "Erro médio histórico (não é intervalo de confiança)".
- Interpretação confirmada (A1/A2): capacidade = armazenagem máxima, só alerta. Combina com a posição de estoque e a necessidade de compra do HTML de referência.
- **Posição de estoque da demo** (pedido do usuário, A14): valores **aleatórios** (semente 42, reprodutíveis) e **lead time 1**. A tela explica o que é lead time: "Lead time é o tempo, em meses, entre fazer o pedido de compra e a mercadoria chegar ao estoque. É usado no estoque de segurança e no prazo 'Comprar até'."

### Idioma (pergunta "Idioma")

- **PT-BR** apenas (AD-007).

### Escopo de trabalho desta etapa (interjeição do usuário)

- "Só implemente a escrita do PRD, não encoste no código": esta etapa produz só documentos em `.specs/`. Nenhum código, teste ou configuração é alterado.

### Issues (pergunta "Issue")

- Issues no **Plane**, no projeto **"P&D"**: **somente o épico "Fazer o POC"**. **O usuário cria o card** e registra o identificador em `tasks.md` § Plane. As tasks T1–T20 ficam em `tasks.md`.

### Aprovação do PRD (2026-09-30)

- Rodada 1: A1/A2 (capacidade = armazenagem máxima, só alerta), A3 (horizonte 2 anos), A4 (grade = P2) e A11 (limites) **confirmadas**. **Sem testes automatizados** ("é apenas um POC"), **usar shadcn**, **"o mais simples possível"**.
- Rodada 2:
  - A17: POC numa **pasta nova `poc/`**, notebook intacto;
  - A15: nome **neutro**;
  - A14: posições **aleatórias** com lead time 1 e explicação na tela;
  - demais regras (A5, A7–A10, A12, A13) ok;
  - **P2/P3 na primeira rodada**;
  - **sem PR**, só a branch;
  - AD-002 marcado como substituído (AD-020);
  - SheetJS na **versão segura**;
  - **re-treino em até 60 s** (POC-40, com limite rígido).
- Consequências de "o mais simples possível":
  - API plana;
  - web com 5 rotas (detalhe em `Sheet`, estoque e capacidade em `Dialog`, comparativo na página de versões);
  - sem deduplicação de versões;
  - meses faltantes recusados (A13).
- Verificação pelo roteiro manual V-01…V-20 em `tasks.md`.
- "Não faça o código ainda": estas atualizações alteram só `.specs/`.

### Agent's Discretion

- Leitura de planilha no navegador, com a API revalidando as linhas normalizadas (A10).
- Execução do treino em processo separado (`spawn`) com vigia de 60 s e `terminate()`: é o jeito mais simples de cumprir o limite rígido de POC-40. Estado em arquivos versionados.
- Biblioteca de gráficos: Recharts via componente `chart` do shadcn.
- Ordem, nomes e organização das telas do painel e das seções da landing.
- Limites numéricos de entrada (A11).
- Horizonte de treino padrão de 2 anos no POC (A3).

### Declined / Undiscussed Gray Areas → Assumptions

Nenhuma área foi recusada. Todas as assunções (A1–A17) foram confirmadas pelo usuário em 2026-09-30.

---

## Specific References

- **Chat claude.ai + artefato** `~/Downloads/previsao-compras-local.html`: fluxo, fórmulas de reposição, parâmetros, KPIs, colunas da tabela, detalhe, modelo de planilha, exportação. Detalhado em `reference-chat.md` §1.
- **Neogrid** (neogrid.com): faixa de números em destaque, CTA único repetido, cases com número no título.
- **UniSoma / Prognos** (unisoma.com.br/prognos): "Menos estoque, menos erro, menos ruptura"; pilares Inteligente / Flexível / Intuitivo; painel preditivo por SKU; aderência histórica.
- Tabela "Trabalho × Aplicação" do chat (Suco 814 × 837, Geleia 180 × 197, Doce 523 × 506). É só contexto: o POC usa os modelos do pacote e reporta os próprios números.

---

## Deferred Ideas

- Login com RSYS Auth API e perfis por usuário (estilo Prognos).
- Deploy em Dokploy com URL para founders e prospects.
- Interface bilíngue PT-BR/EN.
- Métodos-baseline do HTML de referência (média móvel 3, sazonal ingênuo, SES, Holt) como "concorrentes de planilha" no comparativo.
- Simulador financeiro (preço, custo de estoque, valor do erro evitado).
- Capacidade por mês do calendário (12 valores por produto) e limite total do armazém.
- Intervalos de previsão probabilísticos.
- Consumo do motor unificado pelo notebook (cutover do `select_overall_best` manual).
- Fórmulas LaTeX de `formulas.py` exibidas no comparativo de modelos.
- Unificar o motor do POC com o pipeline e o CLI (janela móvel única), com testes, na evolução para SaaS.
- Voltar ao padrão RSYS completo na versão SaaS: Auth.js + RSYS Auth, Zod ponta a ponta, camadas Router/Service/Repository, testes.
