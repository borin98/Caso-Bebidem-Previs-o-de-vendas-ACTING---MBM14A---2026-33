# Previsão de Demanda BebiBem — Implementation Review

**Date:** 2026-09-14  
**Scope:** `.specs/features/previsao-demanda-bebibem/`, `src/bebibem/`, `tests/`, `notebooks/`, Dockerfiles, README, generated artifacts  
**Reference:** `.specs/features/previsao-demanda-bebibem/spec.md`

## Confirmed behavior checks

- `wide-null`: loader accepted a blank wide-format cell and returned `nan_count=1`, month `6`.
- `classical-negative`: declining linear series produced `11` negative future values, minimum `-11.0`.
- `one-year-cluster`: three 12-month product series returned `skipped=False`, `k=2`.
- `classification-leakage`: `cluster_alta` exists in classifier input and equals the target on all `24` modeled rows.
- `capacity-period`: `--units-per-case 12` produced four capacity rows with horizon totals `9881`, `2570`, `3728` beside monthly capacities.
- `stale-format`: PDF remained after rerunning the same figure name with `formats=("png",)`.
- LSP diagnostics reported no static errors in `src/bebibem`; findings below are behavioral and contract defects.
- Visual inspection confirmed raw LaTeX in interpolation footers, literal `\n` in regression annotations, duplicate exponential curves, overlapping model names in the error table, and no forecast-demand series in the capacity figure.

## Correctness findings

`notebooks/01_analise_demanda_bebibem.ipynb:L59-L64,237-L240`: 🔴 bug: notebook reads synthetic data and writes into the production `reports/` directory, replacing T23 real-data tables and PNGs during `pytest --nbmake`. Default to `reports/notebook-example` or an environment-provided isolated output, then add a preservation test around the real report directory.

`reports/tables/forecast_annual.csv:L2-L4`: 🔴 bug: current report contains synthetic totals `44650`, `30750`, `118496`, while final validation records real totals `511`, `180`, `814`. Isolate notebook/example outputs, rerun T23 last, and verify all three formats plus tables come from the real CSV.

`src/bebibem/pipeline.py:L592-L619`: 🔴 bug: seasonal clusters use all 2022–2024 demand before the 2024 holdout evaluation, leaking holdout targets into model features. Fit evaluation clusters on 2022–2023 only; refit separate full-history clusters only for the 2025 forecast.

`src/bebibem/pipeline.py:L329-L343`: 🔴 bug: classification target is derived from `month_clusters`, while `product_features` passed to `LogisticRegression` contains the identical `cluster_alta` one-hot column. Select only month dummies, `trend`, and `lag_12` as DEM-25 requires; assert no `cluster_*` or `lag_1` column reaches the classifier.

`src/bebibem/io_data.py:L186-L187`: 🔴 bug: `allow_missing=True` accepts explicit null demand in wide input, violating DEM-01 validation and silently interpolating bad source data. Reject null source cells; reserve `NaN` only for rows inserted by `fill_missing_months`.
`src/bebibem/pipeline.py:L365-L370`: 🔴 bug: `_forecast_classical` returns negative forecasts without truncation or product/month warning, unlike `forecast_recursive`. Apply the same nonnegative post-processing contract to every winning model path.

`src/bebibem/pipeline.py:L591-L603`: 🔴 bug: monthly and product-year clustering still run for a one-year dataset, although the `<24`-observation contract requires `insufficient_data`. Filter eligible product histories before clustering and emit schema-stable skipped outputs when no eligible series remains.

`src/bebibem/pipeline.py:L669-L683`: 🔴 bug: `demand_cases.groupby("produto").sum()` compares annual or multi-year demand totals with monthly capacity. Persist demand and capacity on the same monthly basis, including `ano` and `mes`, or explicitly compare peak monthly demand.

`src/bebibem/pipeline.py:L533-L536`: 🔴 bug: `_write_figures` passes converted demand as the second argument but never passes `units_per_case`, so `fig_capacity` suppresses the forecast-demand layer. Define one unambiguous interface—raw forecast plus factor, or preconverted cases—and pass every required value exactly once.

`src/bebibem/figures.py:L724-L736`: 🔴 bug: even when called directly with a factor, `fig_capacity` sums all products and months into one global line and does not annotate the factor in the title. Plot product-aligned monthly or peak-month demand and include `N unidades/caixa` in the title.

`src/bebibem/pipeline.py:L347-L355`: 🔴 bug: `regime_classification.csv` exports `accuracy` and `precision`, but DEM-25 requires `acuracia` and `precisao`. Rename exported columns at the table boundary and assert the exact schema.

`src/bebibem/pipeline.py:L595-L599`: 🔴 bug: `clustering_months.csv` repeats only the selected silhouette and discards `month_result.scores` for candidate `k` values. Serialize every evaluated `k` score plus the selected marker.

`src/bebibem/plotting.py:L102-L121`: 🔴 bug: rerunning a figure with a format subset leaves stale same-name files from previously selected formats, so disk contents contradict `index.csv`. Delete only unrequested siblings for the same figure name before updating the index; preserve unrelated files.

## Modeling and reliability risks

`src/bebibem/classification.py:L52-L53`: 🟡 risk: mixed-scale features trigger `ConvergenceWarning` at the default 100 iterations, so published classification metrics may come from a non-converged fit. Use `StandardScaler` in an sklearn pipeline, set a justified `max_iter`, and treat residual convergence warnings as a skipped/error result.

`src/bebibem/smoothing.py:L57-L63`: 🟡 risk: centered 2×12 moving average exists but is never emitted by `moving_average_table`, leaving DEM-07’s centered-series behavior inaccessible. Add an explicit centered column and document its alignment.

`src/bebibem/figures.py:L215-L216`: 🟡 risk: figure shows only trailing `MA(12)` although the specification documents centered 2×12 behavior. Plot and label the centered series distinctly, then verify its first and last valid positions.

`src/bebibem/pipeline.py:L373-L381`: 🟡 risk: `figure.clf()` clears axes but keeps pyplot figure managers alive, producing `More than 20 figures have been opened` on every full run. Close each figure with `plt.close(figure)` in `finally` after saving.

`src/bebibem/figures.py:L192-L193`: 🟡 risk: polynomial footer writes `FORMULAS["poly_fit"]` outside math delimiters, so exported images show raw LaTeX commands. Render the formula as mathtext and reserve enough bottom margin.

`src/bebibem/figures.py:L460-L475`: 🟡 risk: regression annotations render literal `\n`, and the two mathematically equivalent exponential fits create duplicate annotations and one hidden curve. Use a real newline and render one exponential curve/equation with both fitting methods identified as equivalent.

`src/bebibem/figures.py:L395-L421`: 🟡 risk: long model names overlap product cells in `17_tabela_erros`, making rows ambiguous. Allocate explicit column widths or wrapped display labels and verify rendered bounding boxes do not intersect.

`src/bebibem/plotting.py:L125-L135`: 🟡 risk: equation placement is always lower-right despite the design requiring the least-dense corner, so valid extra-product data can be obscured. Select placement from point density and regression-test a lower-right-heavy series.

`src/bebibem/interpolation.py:L118-L121`: 🟡 risk: `holdout_year` is discarded, so the API always treats the final 12 observations as holdout. Honor calendar-year selection for dated inputs or remove the parameter and narrow the documented contract.

`README.md:L233-L237`: 🟡 risk: documented example validation writes into the same `reports/` path as real execution, reproducing report contamination outside the notebook. Change example commands to `--outdir reports/example` or a temporary directory.

`.dockerignore:L10-L12`: 🟡 risk: T20 says pipeline context excludes `notebooks/`, but the shared ignore file re-includes the notebook for the Jupyter image. Add Dockerfile-specific ignore files so pipeline excludes notebooks while Jupyter includes its notebook, or update the accepted contract explicitly.

`.specs/features/previsao-demanda-bebibem/validation.md:L162-L169`: 🟡 risk: bulk claim `All other DEM-01..25 Verified` has no acceptance-criterion-to-assertion citations and conflicts with confirmed defects. Regenerate a full evidence-or-zero matrix and mark every criterion without executable evidence as uncovered.

`.specs/features/previsao-demanda-bebibem/spec.md:L5,15-L20,443-L451`: 🟡 risk: status says real CSV is still pending and all goal/success checkboxes remain open while traceability says `Verified`. Update status only after defects are fixed and a fresh validation pass succeeds.

`.specs/features/previsao-demanda-bebibem/tasks.md:L13-L16`: 🟡 risk: task plan still says `Draft — aguardando aprovação` and real CSV pending after all tasks were checked complete. Reconcile lifecycle metadata with actual execution state after revalidation.

## Missing regression coverage

`tests/unit/test_io_data.py:L105-L120`: 🟡 risk: null rejection covers long layout only, allowing the wide-layout null defect. Add a wide blank-cell case expecting `InputError` with product/year/month.

`tests/unit/test_classification.py:L16-L25`: 🟡 risk: standalone separable arrays cannot detect pipeline target leakage or wrong feature schema. Capture classifier columns through the integration path and assert exactly month dummies, `trend`, and `lag_12`.

`tests/unit/test_forecast.py:L58-L67`: 🟡 risk: negative truncation covers only `forecast_recursive`, not classical winners. Add an end-to-end declining-series case where a classical model wins and all published monthly values remain nonnegative with warnings.

`tests/unit/test_capacity.py:L18-L31`: 🟡 risk: conversion-unit tests never exercise pipeline aggregation or capacity-figure wiring. Add `--units-per-case` integration coverage asserting monthly-period alignment, factor annotation, and a visible demand artist.

`tests/unit/test_clustering.py:L57-L63`: 🟡 risk: fewer-than-three samples is covered, but three products with only one year still cluster. Add the specification’s exact one-year pipeline scenario and assert `insufficient_data` outputs.

`tests/unit/test_plotting.py:L60-L66`: 🟡 risk: format-subset test starts from an empty directory and cannot detect stale siblings. Save all formats first, rerun PNG-only, and assert same-name SVG/PDF removal plus unrelated-file preservation.

`tests/integration/test_notebook.py:L78-L83`: 🟡 risk: notebook tests check metadata but not output isolation. Execute with a temporary output path and assert a sentinel real report remains byte-identical.

`tests/unit/test_figures.py:L187-L208`: 🟡 risk: error-table test checks one numeric cell and cannot detect overlapping labels. Draw the full 18-row table, assert full model labels remain present, and verify text bounding boxes do not cross adjacent cells.

`tests/integration/test_pipeline_e2e.py:L15-L32`: 🟡 risk: happy-path counts do not prove artifact provenance or cross-format consistency after notebook execution. Assert source dataset identity, index format set, and matching run identifiers or hashes across generated outputs.

## Maintainability findings

`src/bebibem/cli.py:L104-L109`: 🔵 nit: `else` keeps the non-debug error path nested. Return immediately after the debug traceback branch, then print the normal error on the flat path.

`src/bebibem/regression.py:L121-L130`: 🔵 nit: boolean algorithm selection mixes two fitting formulations in one branch. Dispatch to separate normal-equation and sum-formula helpers.

`src/bebibem/figures.py:L703-L705`: 🔵 nit: negated compound validation hides which capacity columns are missing. Compute the missing-column set and guard it explicitly.

## Required fix order

1. Isolate notebook and example outputs; rerun T23 so real-data artifacts cannot be overwritten by validation.
2. Remove holdout leakage and classification target leakage; scale classifier inputs and prove convergence.
3. Enforce wide null rejection, classical nonnegative forecasts, one-year skip behavior, candidate-score export, and exact classification schema.
4. Redesign capacity comparison on a monthly basis and wire converted demand into the figure without double conversion.
5. Complete centered moving-average output, stale-format cleanup, figure closing, and visual rendering fixes.
6. Add the regression cases above; run focused tests for each defect, then the build gate and notebook gate with isolated output.
7. Run the real CSV pipeline last in two clean directories; compare table/SVG/PDF hashes, verify totals `814`, `180`, `511`, and inspect all 28 PNGs.
8. Replace `validation.md` with per-criterion evidence, update spec/task statuses, and record only results produced after every gate.

## Completion conditions

- Notebook execution leaves real `reports/` artifacts byte-identical.
- 2024 target mutations cannot affect 2022–2023 clusters or training features.
- Classifier input excludes target-derived columns and completes without convergence warnings.
- Wide null demand exits `2`; inserted missing long-layout months still interpolate with warning.
- Every model path publishes nonnegative forecasts and identifies each truncation.
- One-year input skips clusters and ML with schema-stable `insufficient_data` records.
- Capacity tables and figures compare monthly demand with monthly capacity and show the conversion factor.
- Format-subset reruns contain no stale same-name files; unrelated output remains untouched.
- Full pipeline emits no open-figure warning; formulas and table labels are legible in exported PNG/SVG/PDF.
- Fresh validation cites every acceptance criterion with `file:line` plus exact assertion; no bulk `Verified` claims.
