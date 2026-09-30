# Referências do POC — Planejamento de Demanda Web

**Coletado em:** 2026-09-30
**Uso:** insumo de Specify/Design. Não é requisito por si só; o que entra no escopo está em `spec.md`.

---

## 1. Chat de referência (claude.ai/share/1bd0997c-…)

O link exige login (redireciona para "Sign in - Claude"), então não foi lido diretamente. Fontes: o conteúdo do chat colado pelo usuário (§5, integral) e o artefato gerado no chat, `~/Downloads/previsao-compras-local.html` (617 linhas, 1,1 MB com SheetJS 0.18.5 e Chart.js embutidos).

### 1.1 Resumo colado pelo usuário (verbatim)

> Vou testar a lógica de previsão com os dados do caso antes de publicar. A aplicação está pronta. O botão "Usar dados do caso BEBIBEM" carrega o histórico da loja própria do trabalho para você ver o fluxo completo.
>
> **Como funciona**
>
> Você carrega uma planilha (.xlsx, .xls ou .csv). O formato padrão é uma linha por produto e mês, com as colunas Produto, Período, Quantidade vendida e Estoque. A aplicação também aceita o formato das tabelas do trabalho, com uma linha por produto e ano e colunas de jan a dez. As colunas são identificadas pelo nome e podem ser ajustadas antes do cálculo. Há colunas opcionais para quantidade a receber, lead time e múltiplo de compra por produto.
>
> Para cada produto, a aplicação separa os últimos 12 meses como teste e compara oito métodos: média móvel, suavização exponencial, Holt, regressão linear, sazonal ingênuo, regressão com índices sazonais e Holt-Winters aditivo e multiplicativo. A escolha segue o critério do trabalho: menor MAPE e, se a diferença for menor que 0,5 ponto, menor MAD. No detalhe de cada produto você pode trocar o modelo manualmente.
>
> A previsão é então confrontada com o estoque:
> - **Necessidade** = previsão no horizonte + estoque de segurança − (estoque + a receber), arredondada para o múltiplo de compra.
> - **Estoque de segurança** = z × RMSE do modelo × √lead time.
> - A aplicação também mostra a projeção de estoque mês a mês, os meses de cobertura, a data limite para comprar ("comprar até", já descontado o lead time) e a situação: ruptura prevista, comprar, adequado ou excesso.
>
> O resultado pode ser exportado para Excel com três abas: resumo, previsão mensal e comparativo de modelos.
>
> **Diferença em relação ao trabalho**
>
> Os modelos de Random Forest e Gradient Boosting do trabalho não foram incluídos, porque dependem do scikit-learn em Python. Em compensação, os métodos de séries temporais rodam direto no navegador. Com os dados do caso, eles chegam a totais próximos aos do trabalho:
>
> | Produto | Trabalho | Aplicação |
> |---|---|---|
> | Suco | 814 | 837 (Holt-Winters multiplicativo, MAPE 7,4%) |
> | Geleia | 180 | 197 |
> | Doce | 523 | 506 |
>
> Os estoques do exemplo (180, 25 e 140 unidades) são fictícios, só para demonstração.

### 1.2 Comportamento extraído do HTML (fonte: código do artefato)

| Tema | Regra observada | Linha no HTML |
|---|---|---|
| Entrada | `.xlsx`, `.xls`, `.csv`, `.txt`; separador CSV detectado (`\t`, `;`, `,`); seleção de aba quando há várias | 395–423 |
| Formato largo | Detectado quando há coluna `ano*` e ≥ 6 cabeçalhos de mês; convertido para uma linha por produto e mês | 251–268 |
| Mapeamento de colunas | Campos: Produto*, Período*, Quantidade vendida*, Estoque, A receber, Lead time, Múltiplo de compra; auto-detecção por regex no nome; ajuste manual; prévia de 5 linhas × 8 colunas | 269–286, 424–432 |
| Período | Aceita `2024-01`, `01/2024`, `jan/24`, `202401`, data Excel, data | 234–250 |
| Agregação | Várias linhas do mesmo produto e mês são somadas; meses ausentes viram 0; estoque vale o da linha mais recente | 287–309 |
| Holdout | Últimos `m` meses (12) quando n ≥ 3m; senão `min(m, ⌊0,25n⌋)`; n < 6 cai em média móvel 3 | 361–375 |
| Critério | Menor MAPE; empate < 0,5 p.p. vence menor MAD | 370–373 |
| Parâmetros | Horizonte de cobertura 1–24 (padrão 3); lead time padrão 0–12, passo 0,5 (padrão 1); nível de serviço 90/95/97,5/99% (z 1,2816/1,6449/1,96/2,3263; padrão 95%); múltiplo de compra ≥ 1 (padrão 1); ciclo sazonal 2–24 (padrão 12) | 186–193 |
| Estoque de segurança | `SS = z × RMSE × √max(L, 1)` — lead time 0 usa √1 | 463 |
| Necessidade | `max(0, Σprevisão[0..H) + SS − (estoque + a receber))`, arredondada para cima ao múltiplo | 464 |
| Projeção | Mês a mês no horizonte: inicial, venda prevista, final (sem a nova compra) | 465–466 |
| Cobertura | Meses (1 casa) que o disponível cobre na previsão de 24 meses; "> 24" se não esgota | 468–470 |
| Comprar até | Primeiro mês cujo estoque final fica abaixo de SS (0 se disponível < SS), menos o lead time, arredondado para baixo; ≤ 0 = "Imediato" | 465–471, 479 |
| Situação | `ruptura` se necessidade > 0 e estoque final < 0 no horizonte; `comprar` se necessidade > 0; `excesso` se disponível > 2 × (demanda do horizonte + SS) e demanda > 0; senão `adequado` | 472–473 |
| KPIs | Produtos analisados; unidades previstas no horizonte; produtos com ruptura prevista; unidades a comprar (nº de produtos) | 488–492 |
| Tabela | Produto, modelo, MAPE, previsão H, estoque + a receber, barra de cobertura, meses cobertos, est. segurança, comprar, comprar até, situação; ordenada por gravidade (ruptura, comprar, adequado, excesso) e necessidade decrescente; filtro por nome e "só com necessidade" | 484–502 |
| Detalhe | Fatos; gráfico (vendido, previsão no teste, previsão, estoque projetado, estoque de segurança); tabela de projeção; comparativo de modelos com troca manual do modelo | 512–563 |
| Exemplo do caso | Histórico 2022–2024 dos 3 produtos; estoque fictício 180 / 25 / 140, a receber 0, lead time 1 | 567–584 |
| Modelo de planilha | Abas `Vendas` (exemplo) e `Instruções` (coluna, obrigatória, como preencher) | 585–599 |
| Exportação | `previsao_necessidade_compra.xlsx` com abas Resumo, Previsão mensal, Comparativo de modelos | 603–614 |

---

## 2. Neogrid (neogrid.com)

- Posicionamento: "Soluções de ponta a ponta para a gestão da sua empresa"; "a maior malha de dados da cadeia de consumo e abastecimento do Brasil".
- Prova social: faixa de logos de clientes, cases com resultado numérico no título (ex.: "reduziu o tempo de processamento de pedido de 4 horas para 10 minutos", DRP da Panvel).
- Números de escala em destaque (+660 mil PDVs, +8 mil indústrias).
- CTA único e repetido: "Quero conversar com vendas".

## 3. UniSoma / Prognos (unisoma.com.br, unisoma.com.br/prognos)

- Hero: "Estruturando decisões críticas com Inteligência Analítica"; Prognos: "Menos estoque, menos erro, menos ruptura."
- Três pilares: Inteligente (seleção automática de modelos estatísticos e de ML, sazonalidade e tendência), Flexível (ciclos S&OP, estrutura comercial), Intuitivo (100% web, dashboards por ciclo, modelo preditivo, outliers).
- Painel preditivo por SKU e ciclo, histórico de aderência, identificação de itens críticos.
- Resultados sempre atribuídos a um cliente ("19% de aumento na acuracidade — Cimed").
- Seções: clientes, impacto com resultados, divisões, cases, depoimentos, diferenciais, CTA "Falar com um especialista".

---

## 4. O que o POC herda de cada referência

| Origem | Herdado | Não herdado (motivo) |
|---|---|---|
| Chat / HTML | Fluxo planilha → mapeamento → previsão → necessidade de compra; parâmetros de reposição; KPIs; tabela por situação; detalhe com projeção; modelo de planilha; exemplo do caso; exportação Excel; troca manual de modelo | 8 métodos em JS (o POC usa os 9 modelos Python do pacote `bebibem`, decisão do usuário); ciclo sazonal configurável (modelos do pacote fixam m = 12); HTML único (usuário escolheu Next.js + FastAPI) |
| Neogrid | Faixa de números, CTA único, cases com número no título | Números de terceiros; logos de clientes (POC white-label, sem clientes reais) |
| Prognos | Três pilares como estrutura da landing; "menos estoque, menos erro, menos ruptura" como promessa qualitativa; painel por produto com modelo e aderência | Percentuais de ganho (não medidos neste POC); agente de IA; workflow S&OP; login por perfil |

## 5. Conteúdo integral do chat (colado pelo usuário em 2026-09-30)

### 5.1 Pedido original (verbatim)

> aseado no grabalho científico, quero que me crie uma aplicação html, onde eu possa inserir a partir de uma planilha, o produto, a quantidade vendida e a posição de estoque do produto. Quero projetoar a quantidade de venda nos próximos período e confrontar com  a quantidade de estoque e a necessidade de compra?

### 5.2 Passos do assistente (verbatim)

> Read a file, ran a command, created a file
> Read a file, ran a command, created a file
>
> Vou testar a lógica de previsão com os dados do caso antes de publicar.
> Ran a command
> Ran a command
>
> Artifact — Published artifact: /artifact/57fCuVzm5M4pFLu9wrxHnR

### 5.3 Resposta final (verbatim)

> A aplicação está pronta. O botão "Usar dados do caso BEBIBEM" carrega o histórico da loja própria do trabalho para você ver o fluxo completo.
>
> **Como funciona**
>
> Você carrega uma planilha (.xlsx, .xls ou .csv). O formato padrão é uma linha por produto e mês, com as colunas Produto, Período, Quantidade vendida e Estoque. A aplicação também aceita o formato das tabelas do trabalho, com uma linha por produto e ano e colunas de jan a dez. As colunas são identificadas pelo nome e podem ser ajustadas antes do cálculo. Há colunas opcionais para quantidade a receber, lead time e múltiplo de compra por produto.
>
> Para cada produto, a aplicação separa os últimos 12 meses como teste e compara oito métodos: média móvel, suavização exponencial, Holt, regressão linear, sazonal ingênuo, regressão com índices sazonais e Holt-Winters aditivo e multiplicativo. A escolha segue o critério do trabalho: menor MAPE e, se a diferença for menor que 0,5 ponto, menor MAD. No detalhe de cada produto você pode trocar o modelo manualmente.
>
> A previsão é então confrontada com o estoque:
>
> - Necessidade = previsão no horizonte + estoque de segurança − (estoque + a receber), arredondada para o múltiplo de compra.
> - Estoque de segurança = z × RMSE do modelo × √lead time.
> - A aplicação também mostra a projeção de estoque mês a mês, os meses de cobertura, a data limite para comprar ("comprar até", já descontado o lead time) e a situação: ruptura prevista, comprar, adequado ou excesso.
>
> O resultado pode ser exportado para Excel com três abas: resumo, previsão mensal e comparativo de modelos.
>
> **Diferença em relação ao trabalho**
>
> Os modelos de Random Forest e Gradient Boosting do trabalho não foram incluídos, porque dependem do scikit-learn em Python. Em compensação, os métodos de séries temporais rodam direto no navegador. Com os dados do caso, eles chegam a totais próximos aos do trabalho:
>
> | Produto | Trabalho | Aplicação |
> |---|---|---|
> | Suco | 814 | 837 (Holt-Winters multiplicativo, MAPE 7,4%) |
> | Geleia | 180 | 197 |
> | Doce | 523 | 506 |
>
> Os estoques do exemplo (180, 25 e 140 unidades) são fictícios, só para demonstração.

### 5.4 Pedido original × PRD

| Item do pedido original | Onde está no PRD |
| --- | --- |
| Aplicação a partir do trabalho científico | Motor do POC reusa os 9 modelos do pacote `bebibem` (POC-01…04, A17) |
| Inserir por planilha: produto, quantidade vendida, posição de estoque | Importação com mapeamento de colunas Produto / Período / Quantidade vendida / Estoque / A receber / Lead time / Múltiplo (POC-15…17) |
| Projetar a venda nos próximos períodos | Previsão de `12 × h` meses a partir do mês seguinte ao último observado (POC-04, A3) |
| Confrontar com o estoque e a necessidade de compra | Plano de reposição: SS, necessidade, projeção, cobertura, comprar até, situação (POC-06…12) |
| "Aplicação html" | Decisão posterior do usuário: Next.js + FastAPI em `poc/`, com duas imagens Docker e `poc/docker-compose.yml` (AD-016, AD-019) |
| RF e GB ficaram de fora no chat por falta de scikit-learn no navegador | O POC roda em Python e inclui RF e GB entre os 9 modelos |

Sem requisito novo: o chat integral confirma o escopo já especificado.
