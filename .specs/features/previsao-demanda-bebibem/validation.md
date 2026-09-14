# Previsão de Demanda BebiBem — Validation

**Date**: 2026-09-14
**Spec**: `.specs/features/previsao-demanda-bebibem/spec.md`
**Scope**: correções do `code-review.md`, cobertura direcionada e verificação ponta a ponta
**Status**: PASS

## Review Findings Closed

| Área | Evidência |
| --- | --- |
| Isolamento de saídas | `.dockerignore`, ignores por Dockerfile e notebook usam diretórios separados; teste de execução do notebook protege `reports/tables`. |
| Dados e leakage | Células vazias do layout wide são rejeitadas; classificação seleciona somente features permitidas; clusterização e ML usam treino 2022–2023; entrada de um ano retorna `insufficient_data`. |
| Modelos | Classificador usa `StandardScaler` dentro de `Pipeline`; convergência é tratada; previsão clássica trunca valores negativos e registra warning; holdout da interpolação respeita ano-calendário. |
| Capacidade | Comparação usa pico mensal em caixas; total do horizonte permanece separado; fator unidades/caixa aparece na figura e é aplicado uma vez. |
| Clustering | Tabela exporta scores de todos os candidatos `k` com marcador de seleção; matrizes vazias não chamam KMeans. |
| Apresentação | Média móvel centrada para janela par; formatos obsoletos são removidos somente para o mesmo nome; figuras são fechadas após exportação; equações usam math delimiters e âncoras com menor densidade; tabela de erros não sobrepõe textos longos. |
| Código e isolamento | CLI usa guard clauses; regressões exponenciais despacham builders explícitos; notebook não grava no diretório compartilhado por padrão. |

## Verification Commands

### Full gate

```text
uv run ruff check .
uv run ruff format --check .
uv run pytest -q --cov=src/bebibem --cov-report=term-missing
```

Resultados:

- Ruff: `All checks passed!`
- Formatação: `41 files already formatted`
- Pytest: `103 passed`, 4 warnings não fatais
- Cobertura: `90.23%` (`2048` statements), acima do mínimo de `85%`

Warnings restantes são `ConvergenceWarning` dos fixtures sintéticos de clustering; não ocorrem no pipeline com CSV real.

### Notebook

```text
uv run pytest --nbmake notebooks/01_analise_demanda_bebibem.ipynb
```

Resultado: `1 passed`. Warning apenas de `id` ausente em células, emitido pelo `nbformat` durante validação.

### Docker

```text
docker build -f docker/pipeline.Dockerfile -t bebibem-pipeline-review .
docker build -f docker/jupyter.Dockerfile -t bebibem-jupyter-review .
```

Ambos os builds terminaram com exit code `0`. A imagem pipeline executada com `data/raw/demanda_loja_propria.csv` produziu `28` PNG, `28` SVG, `28` PDF, `13` tabelas e totais anuais `511`, `180`, `814` para Doce, Geleia e Suco. A imagem Jupyter respondeu `HTTP 200` em `/lab` com porta publicada dinamicamente.

### CSV real e reprodutibilidade

Duas execuções independentes do comando abaixo foram gravadas em diretórios temporários limpos:

```text
uv run bebibem-forecast --input data/raw/demanda_loja_propria.csv --outdir <temp> --formats png,svg,pdf
```

Resultados:

- `28` figuras em cada formato por execução.
- Hashes SHA-256 iguais para PNG, SVG e PDF entre as execuções.
- Tabelas CSV idênticas entre as execuções.
- `demand_tidy.csv`: `108` observações.
- `forecast_annual.csv`: Doce de frutas `511`, Geleia de frutas `180`, Suco Premium `814` unidades em 2025.

## Targeted Regression Tests

- Wide input com nulo explícito: rejeitado com produto/ano/mês ofensores.
- Holdout de interpolação com datas: usa 2023 quando `holdout_year=2023`, não os últimos 12 registros cegamente.
- Previsão linear decrescente: nenhum valor negativo permanece e warnings são emitidos.
- Entrada de um ano: clustering, métricas e ML retornam status estável `insufficient_data`.
- Capacidade: pico mensal e total do horizonte permanecem distintos.
- Stale formats: rerun PNG-only remove SVG/PDF do mesmo nome e preserva arquivo não relacionado.
- Notebook: execução usa diretório temporário e não altera tabela sentinela em `reports/tables`.
- Tabela de erros: 18 linhas e textos permanecem dentro das células para os seis modelos.

## Residual Warnings

- Fixtures unitários de clustering geram quatro `ConvergenceWarning` esperados por pontos duplicados.
- `nbformat` avisa sobre IDs ausentes no notebook; execução passa.

Nenhum blocker funcional permanece.
