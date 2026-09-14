# Seleção unificada do melhor modelo (ML/clássico × séries temporais) — Achados e Plano

**Data:** 2026-09-21
**Escopo:** revisão de `.specs/features/previsao-demanda-bebibem/{spec,design,tasks}.md` contra `src/bebibem/`, `notebooks/01_analise_demanda_bebibem.ipynb`
**Status:** registrado — nenhuma correção aplicada ainda (docs-only)
**Requisito central:** DEM-27 (`spec.md:419-432`)

---

## 1. Problema

A previsão publicada pelo CLI não escolhe o melhor modelo entre todos os candidatos. Ela escolhe o melhor **dentro do grupo ML/regressão clássica** e ignora os métodos de séries temporais, mesmo quando estes têm MAPE de holdout menor.

Evidência:

| Local | Fato |
| --- | --- |
| `src/bebibem/models.py:136` | `select_overall_best(*metrics_tables)` existe e implementa a regra correta (menor MAPE; empate < 0,5 p.p. por menor MAD). |
| `src/bebibem/pipeline.py:803-828` | O estágio `forecast` itera `best_models`, derivado **apenas** de `error_metrics` (6 modelos ML/clássicos). `select_overall_best` nunca é chamado. |
| `src/bebibem/pipeline.py:875-884` | As séries temporais rodam **depois** de `_write_figures`, isto é, depois de `forecast_monthly.csv`/`forecast_annual.csv` já terem sido gravados. Ordem impede a comparação. |
| `notebooks/…ipynb:604` | Só o notebook chama `select_overall_best`. A resposta de negócio via CLI diverge da resposta do notebook. |
| `spec.md:423` | O próprio spec documenta o caso real: Doce de frutas previsto com `ridge` (MAPE 34,55%) enquanto `holt_winters_multiplicative` (MAPE 15,53%) estava disponível. |

Consequência: `forecast_annual.csv` — a resposta da questão 5 do case — pode publicar um número produzido por um modelo comprovadamente pior, com `mape_holdout` do grupo errado ao lado dele.

---

## 2. Achados do review (registro completo)

### 2.1 Bugs / contradições spec × código

| # | Local | Achado | Correção |
| --- | --- | --- | --- |
| B1 | `spec.md:421-430` × `pipeline.py:803-828` | DEM-27 AC2 exige previsão pelo vencedor geral; CLI usa vencedor do grupo ML. | Aplicar `select_overall_best` no pipeline (ver §3). |
| B2 | `spec.md:294` × `cli.py:34-38` | DEM-15 AC1 lista 11 flags e omite `--timeseries`. | Acrescentar a flag à AC. |
| B3 | `design.md:71-88` | Árvore de módulos não contém `src/bebibem/timeseries.py`. | Incluir no tree + seção em Components com interfaces DEM-26/27. |
| B4 | `design.md:306-321` × `pipeline.py:756`, `timeseries.py:807,820-821` | Tabela de saídas lista 12 CSVs; pipeline grava 13 (`features.csv` ausente do doc) + 3 de séries temporais. | Documentar as 4 linhas faltantes. |
| B5 | `tasks.md:364-392` | Não existe task para DEM-26 nem DEM-27 (T26 é `classification.py`). `spec.md:482` afirma cobertura total. | Criar T27 (timeseries) e T28 (seleção unificada). |
| B6 | `spec.md:488`, `tasks.md:518,537,664` | "32 figuras + 13 tabelas" não cobre execução com `--timeseries`. | Declarar catálogo base e catálogo `--timeseries`. |
| B7 | `design.md:311` × `spec.md:111-112` | `interpolation_fit.csv` documentado sem `r2_adj` e sem RMSE por candidato. | Alinhar contrato de colunas. |

### 2.2 Riscos

| # | Local | Achado | Correção |
| --- | --- | --- | --- |
| R1 | `timeseries.py:808,822-823` | `to_csv(index=False)` sem `lineterminator="\n"`, diferente de `_write_table` (`pipeline.py:152`). Bytes instáveis entre plataformas; contradiz `spec.md:490`. | Reutilizar `_write_table`. |
| R2 | `timeseries.py:434-788` | Módulo mistura modelagem, construção de figura e escrita em disco; `design.md:258` define `figures.py` sem I/O e `pipeline.py` como único escritor. | Mover `fig_timeseries_*` para `figures.py`; gravações para `pipeline.py`. |
| R3 | `design.md:101-118` × `pyproject.toml:17` | `statsmodels` ausente da tabela de reuso; nota "Nada de scipy" desatualizada. | Documentar dependência e o escopo dela. |
| R4 | `spec.md:404-415` | DEM-26 sem AC para falha/ausência de `statsmodels` e sem AC de determinismo (SARIMA emite `ConvergenceWarning`). | Acrescentar ACs. |
| R5 | seleção estatística | Menor MAPE sobre um holdout único de 12 meses com 9 candidatos ⇒ risco de escolher ruído. | Regra de parcimônia explícita (ver §3.5). |

### 2.3 Nits de documentação

- `design.md:5`: Status `Draft` enquanto `spec.md:5` e `tasks.md:13` dizem implementado/validado.
- `spec.md:450-478`: coluna `Phase` = `Design` nas 27 linhas com `Status = Verified`.
- `spec.md:58`: afirma CSV real pendente; `tasks.md:16` diz fornecido e verificado.
- `design.md:13-39`: mermaid sem `regression`, `classification`, `timeseries`, `formulas`.
- `design.md:449,452`: esboço com `name = "bebibem-demanda"`; real é `bebibem-forecast` (`pyproject.toml:6`).
- `design.md:575`: "argparse para 11 flags"; são 12.
- `design.md:259`: lista de `figures.py` sem `fig_best_model_fit` (usada em `…ipynb:737`).
- `design.md:316` × `spec.md:153-154`: `smape` documentado como coluna fixa em um lado e condicional no outro.
- `spec.md:320-321`: ACs com 5+ cláusulas e racional embutido impedem teste 1:1.
- `spec.md:323`: nota histórica de mudança de pedido dentro da spec — pertence a `.specs/STATE.md`.

---

## 3. Plano de correção — seleção do menor erro entre os dois grupos

### 3.1 Reordenar o pipeline

Ordem canônica atual (`pipeline.py:281`): `load → interp → ma → cluster → features → ml → forecast → capacity → plots`.
Ordem alvo: `load → interp → ma → cluster → features → ml → timeseries → forecast → capacity → plots`.

- Promover séries temporais a **estágio** (`"timeseries"` em `resolve_steps`), ativado por `--timeseries`, executado **antes** de `forecast`.
- Remover a chamada tardia de `generate_and_save_timeseries_artifacts` em `pipeline.py:875-884`; separar em `evaluate_timeseries(...)` (métricas, sem I/O) + escrita via `_write_table`/`_save_figure` no pipeline.

### 3.2 Selecionar o vencedor geral

```
overall_best = select_overall_best(error_metrics, timeseries_metrics)   # models.py:136
```

- Sem `--timeseries`: `select_overall_best(error_metrics)` — degrada para o comportamento atual, sem ramo especial.
- Linhas com `mape` `NaN`, `not_applicable` ou `insufficient_data` são ignoradas (DEM-27 AC4, já implementado).
- Produto sem nenhum candidato aplicável fica fora do dicionário e da previsão, com `WARNING`.

### 3.3 Rotear a previsão pelo grupo do vencedor

Três caminhos, um único ponto de decisão:

| Vencedor | Caminho de previsão | Origem |
| --- | --- | --- |
| `ridge`, `random_forest`, `gradient_boosting` | `fit_final` + `forecast_recursive` | `pipeline.py:805-812` (atual) |
| `linear_normal_equation`, `exponential_loglinear`, `exponential_normal_equation` | `_classical_fit` + `_forecast_classical` | `pipeline.py:814-822` (atual) |
| `holt_winters_multiplicative`, `sarima`, `fourier_harmonic` | `forecast_timeseries_future` **por produto**, com o método daquele produto | `timeseries.py` (a ligar) |

Invariantes a preservar em todos os caminhos: truncamento de negativos em 0 com `WARNING` (DEM-11 AC6) e reajuste em todo o histórico 2022–2024 (DEM-11 AC1).

### 3.4 Publicar a evidência da escolha

- `forecast_tables(...)` passa a receber as **métricas combinadas**, de modo que `modelo`, `mape_holdout` e `mad_holdout` em `forecast_monthly.csv`/`forecast_annual.csv` correspondam ao vencedor geral — nunca ao vencedor do grupo.
- Nova tabela `reports/tables/model_selection.csv`: `produto, modelo_vencedor_geral, grupo, mape, mad, modelo_vencedor_ml, mape_ml, delta_mape_pp`. Torna auditável cada troca de grupo.
- `fig_combined_error_table` (`figures.py:542`) entra no catálogo do CLI como `metricas/33_tabela_comparativa_modelos`, hoje exclusiva do notebook.
- `timeseries_forecast_monthly.csv` permanece como artefato do grupo; `forecast_monthly.csv` passa a ser a **resposta única** de negócio.

### 3.5 Guarda contra seleção por ruído (R5)

Com 12 pontos de holdout e 9 candidatos, diferenças pequenas de MAPE não são significativas. Regra proposta, a confirmar:

1. Menor MAPE vence.
2. Empate < 0,5 p.p. ⇒ menor MAD (regra atual, mantida).
3. Empate < 1,0 p.p. entre grupos ⇒ preferir o modelo mais parcimonioso, na ordem `fourier_harmonic` < `holt_winters_multiplicative` < `linear_normal_equation` < `ridge` < `sarima` < ensembles.
4. Registrar em `model_selection.csv` qual regra decidiu (`mape`, `mad`, `parcimonia`).

Sem a regra 3, a previsão publicada pode alternar de modelo entre execuções com dados levemente diferentes, sem ganho real de acurácia.

### 3.6 Atualizar a documentação

- `spec.md`: nova AC em DEM-27 dizendo que o **CLI** (não só o notebook) publica pelo vencedor geral; `--timeseries` na lista de flags de DEM-15 AC1; ACs de DEM-26 para dependência ausente e determinismo; contagens de artefatos por modo.
- `design.md`: componente `timeseries.py`; `features.csv` e as 3 tabelas de séries temporais; catálogo de figuras por modo; `statsmodels` no reuso; mermaid com o novo estágio; status e nits de §2.3.
- `tasks.md`: T27 (séries temporais) e T28 (seleção unificada) com `Done when` e gates.

---

## 4. Ordem de execução

1. Extrair avaliação de séries temporais de I/O (`evaluate_timeseries`) e mover figuras para `figures.py` (R2).
2. Gravar as tabelas de séries temporais por `_write_table` (R1).
3. Inserir o estágio `timeseries` antes de `forecast` em `resolve_steps` (§3.1).
4. Trocar `best_models` por `select_overall_best(...)` e implementar o roteamento de três vias (§3.2, §3.3).
5. Propagar métricas combinadas para `forecast_tables` e emitir `model_selection.csv` (§3.4).
6. Decidir e implementar a regra de parcimônia (§3.5).
7. Acrescentar `metricas/33_tabela_comparativa_modelos` ao catálogo do CLI.
8. Testes (§5).
9. Atualizar spec/design/tasks (§3.6) e reexecutar a validação com CSV real.

---

## 5. Testes exigidos

| Teste | Local | Asserção |
| --- | --- | --- |
| Roteamento cross-group | `tests/unit/test_pipeline.py` | Vencedor `holt_winters_multiplicative` para um produto ⇒ a série publicada é a do método de séries temporais daquele produto, não a de `ridge`. |
| Coerência de métrica publicada | `tests/unit/test_forecast.py` | `mape_holdout` em `forecast_annual.csv` é igual ao MAPE do vencedor geral na tabela combinada. |
| Degradação sem `--timeseries` | `tests/integration/test_pipeline_e2e.py` | Sem a flag, `forecast_annual.csv` é byte-idêntico ao comportamento atual. |
| Não-negatividade em todos os caminhos | `tests/unit/test_forecast.py` | Série decrescente com vencedor de séries temporais ⇒ nenhum valor negativo publicado e `WARNING` emitido. |
| Regra de parcimônia | `tests/unit/test_models.py` | MAPEs a 0,8 p.p. de distância entre grupos ⇒ vence o modelo mais parcimonioso e `model_selection.csv` registra `parcimonia`. |
| Produto sem candidato | `tests/unit/test_models.py` | Todas as linhas `not_applicable` ⇒ produto ausente do dicionário, pipeline não aborta. |
| Determinismo | `tests/integration/test_pipeline_e2e.py` | Duas execuções com `--timeseries --seed 42` ⇒ CSVs idênticos e hashes SVG/PDF iguais. |

---

## 6. Critérios de aceite

- `forecast_annual.csv` e a última seção do notebook publicam **o mesmo modelo e o mesmo total** por produto.
- Nenhum produto é publicado com um modelo cujo MAPE de holdout seja maior que o de outro candidato avaliado, salvo quando a regra de parcimônia decidiu — e isso está registrado em `model_selection.csv`.
- Sem `--timeseries`, o comportamento e os artefatos permanecem os de hoje.
- Cada troca de grupo é auditável por `model_selection.csv` + `metricas/33_tabela_comparativa_modelos`.
- `uv run pytest -q --cov=src/bebibem` mantém cobertura ≥ 85%.
- Spec, design e tasks descrevem os artefatos realmente gravados em cada modo.
