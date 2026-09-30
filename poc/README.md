# POC Planejamento de Demanda (web)

Demo local, sem login, do motor de previsão do pacote `bebibem`: landing comercial, painel de
reposição, comparativo dos 9 modelos, carga de planilha, fechamento de mês com re-treino (máx. 60 s)
e versões com comparativo antes × depois.

Tudo do POC vive nesta pasta. O pacote `bebibem`, o CLI, o notebook e o `docker/` da raiz não são
alterados; a API usa o pacote como biblioteca.

```
poc/
  docker-compose.yml   serviços api e web (nenhum outro)
  api/                 FastAPI (projeto uv próprio, depende do pacote da raiz por caminho)
  web/                 Next.js + shadcn/ui (Bun)
```

Especificação: `.specs/features/poc-demand-planning-web/` (spec, design, tasks).

## Subir com Docker

Pré-requisito: Docker com Compose v2.

```bash
cd poc
docker compose up --build        # primeira vez (baixa imagens base e dependências)
```

- Web: http://127.0.0.1:3000 (landing) e http://127.0.0.1:3000/app (painel)
- API: http://127.0.0.1:8000/api/v1/health

As duas portas ficam publicadas só em `127.0.0.1`. A web fala com a API pela rede interna do
compose (`http://api:8000`); o navegador só acessa a web.

Na primeira subida, com o volume vazio, a API cria a versão de dados `caso` a partir de
`data/raw/demanda_loja_propria.csv`, gera posições de estoque fictícias (semente 42, lead time 1) e
roda o treino inicial (alguns segundos). A landing mostra "Treinamento inicial em andamento" até
ele concluir.

| Ação | Comando (dentro de `poc/`) |
| --- | --- |
| Parar, mantendo os dados | `docker compose down` |
| Subir de novo sem rebuild | `docker compose up -d` |
| Zerar os dados (volume `poc-data`) | `docker compose down -v` |
| Logs do treino (JSON por transição) | `docker compose logs -f api` |

**Sem internet na apresentação:** faça o `docker compose up --build` uma vez com internet antes da
demo. Depois disso as imagens ficam no cache local e `docker compose up` sobe sem rede. A web não
carrega fontes, scripts nem bibliotecas de CDN em tempo de execução.

## Rodar sem Docker (desenvolvimento)

```bash
# API (Python ≥ 3.11 via uv); dados em poc/api/var/
cd poc/api
uv run uvicorn poc_api.app:app --reload --port 8000

# Web, em outro terminal
cd poc/web
bun install
bun run dev        # http://127.0.0.1:3000 (proxy /api/v1 → http://127.0.0.1:8000)
```

Gates usados na implementação: `uv run ruff check . && uv run ruff format --check .` (em `poc/api`)
e `bun run lint && bun run build` (em `poc/web`).

### Variáveis de ambiente da API

| Variável | Padrão | Uso |
| --- | --- | --- |
| `POC_DATA_DIR` | `./var` (`/data` no Docker) | Versões de dados, treinos, `active.json`, `settings.json` |
| `POC_HORIZON_YEARS` | `2` | Horizonte do treino inicial do caso |
| `POC_TRAINING_TIMEOUT_S` | `60` | Limite rígido do treino; sobrescrever só para verificação |

## Marca (white-label)

Nome, slogan, cor primária e logo ficam em `web/src/config/brand.ts`. Altere e reconstrua a web
(`docker compose up --build web`). O padrão é neutro: "Planejamento de Demanda", sem logo.

## Roteiro da demo (≤ 5 minutos)

1. **Landing (`/`)**: proposta de valor e a faixa de números lida da API (modelos avaliados,
   acurácia média dos vencedores, meses de histórico, produtos, último treino). Clique em
   "Ver demonstração".
2. **Painel (`/app`)**: 5 KPIs, parâmetros de reposição e a tabela por prioridade (ruptura →
   comprar → adequado → excesso). Troque o nível de serviço de 95% para 99%: estoque de segurança e
   necessidade sobem na hora, sem novo treino.
3. **Detalhe**: clique num produto. Fatos (previsão, estoque de segurança, necessidade, comprar
   até, MAD, MAPE, acurácia), gráfico com a faixa de erro médio e a projeção mês a mês. Mostre a
   troca manual de modelo.
4. **Estoque e capacidade**: informe a capacidade de um produto abaixo de estoque + necessidade e
   veja o selo "Excede capacidade".
5. **Modelos (`/app/modelos`)**: os 9 modelos por produto, o critério (menor MAPE; empate < 0,5
   p.p. pelo menor MAD) e o gráfico real × previsto no período de teste.
6. **Dados → Fechar mês**: informe as vendas do mês seguinte e clique em "Fechar mês e
   re-treinar". O progresso mostra o tempo decorrido (máx. 60 s).
7. **Versões**: ao concluir, a tela abre o comparativo antes × depois (meses adicionados, período
   de teste deslocado, Δ MAPE e Δ da soma dos 12 meses). Reative um treino anterior se quiser.
8. Volte ao painel: a recomendação de compra agora usa o treino novo.

Outras entradas: **Dados → Importar** (planilha `.xlsx/.xls/.csv/.txt` até 5 MB, com mapeamento de
colunas; "Baixar planilha modelo" gera um exemplo) e **Dados → Grade** (edita células e cria uma
versão de edição; "Re-treinar agora" roda o treino).
