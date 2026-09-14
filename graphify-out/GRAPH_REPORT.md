# Graph Report - .  (2026-09-21)

## Corpus Check
- Corpus is ~45,715 words - fits in a single context window. You may not need a graph.

## Summary
- 592 nodes · 1544 edges · 21 communities (17 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 65 edges (avg confidence: 0.62)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Visualizations & Plotting|Visualizations & Plotting]]
- [[_COMMUNITY_ML Models & Validation|ML Models & Validation]]
- [[_COMMUNITY_Project Config & Utilities|Project Config & Utilities]]
- [[_COMMUNITY_Data Interpolation|Data Interpolation]]
- [[_COMMUNITY_Business Domain & Context|Business Domain & Context]]
- [[_COMMUNITY_Regression Models|Regression Models]]
- [[_COMMUNITY_Data IO & Preprocessing|Data I/O & Preprocessing]]
- [[_COMMUNITY_Plotting Helpers|Plotting Helpers]]
- [[_COMMUNITY_CLI Interface|CLI Interface]]
- [[_COMMUNITY_Feature Engineering|Feature Engineering]]
- [[_COMMUNITY_Regime Classification|Regime Classification]]
- [[_COMMUNITY_Time Series Clustering|Time Series Clustering]]
- [[_COMMUNITY_Demand Forecasting|Demand Forecasting]]
- [[_COMMUNITY_LaTeX Formulas|LaTeX Formulas]]
- [[_COMMUNITY_Factory Capacity|Factory Capacity]]
- [[_COMMUNITY_Documentation & Spec|Documentation & Spec]]
- [[_COMMUNITY_Determinism & Conventions|Determinism & Conventions]]
- [[_COMMUNITY_Logistic Regression|Logistic Regression]]
- [[_COMMUNITY_Gradient Boosting|Gradient Boosting]]
- [[_COMMUNITY_Random Forest|Random Forest]]
- [[_COMMUNITY_Docker Configuration|Docker Configuration]]

## God Nodes (most connected - your core abstractions)
1. `InputError` - 65 edges
2. `run()` - 49 edges
3. `DataFrame` - 30 edges
4. `_new_figure()` - 24 edges
5. `load_demand()` - 22 edges
6. `Figure` - 21 edges
7. `_empty_message()` - 21 edges
8. `fig_forecast_all()` - 19 edges
9. `fig_interpolation()` - 18 edges
10. `RegressionFit` - 18 edges

## Surprising Connections (you probably didn't know these)
- `Previsão de Demanda BebiBem Specification` --references--> `Case BebiBem - MBM - Acting 2026`  [EXTRACTED]
  .specs/features/previsao-demanda-bebibem/spec.md → docs/Case BebiBem - MBM - Acting 2026.pdf
- `Previsão de Demanda BebiBem Specification` --references--> `Questão 5 - Demand Forecast for Own Store`  [EXTRACTED]
  .specs/features/previsao-demanda-bebibem/spec.md → docs/Case BebiBem - MBM - Acting 2026.pdf
- `Fourier Harmonic Regression (P=12, K=2 harmonics)` --semantically_similar_to--> `Polynomial Interpolation (anti-overfitting degree selection d∈{1..5})`  [INFERRED] [semantically similar]
  README.md → .specs/features/previsao-demanda-bebibem/design.md
- `Holt-Winters Multiplicative Exponential Smoothing (m=12)` --semantically_similar_to--> `Recursive Forecasting (lag_1 from prediction, lag_12 from real then predicted)`  [INFERRED] [semantically similar]
  README.md → .specs/features/previsao-demanda-bebibem/design.md
- `DataFrame` --uses--> `ClassificationResult`  [INFERRED]
  tests/unit/test_figures.py → src/bebibem/classification.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **ML/Classical Model Comparison Pipeline (6+3 models evaluated under same holdout)** — concept_ridge_regression, concept_random_forest, concept_gradient_boosting, concept_linear_regression_normal_eq, concept_exponential_regression, concept_holt_winters, concept_sarima, concept_fourier_harmonic, concept_error_metrics [EXTRACTED 1.00]
- **Data Pipeline Flow (CSV→tidy→features→models→forecast→figures)** — design_io_data, design_tidy_dataframe, design_interpolation, design_smoothing, design_clustering, design_features, design_models, design_forecast, design_figures [EXTRACTED 1.00]
- **Spec Lifecycle (spec→context→design→tasks→code-review→validation)** — spec_previsao_demanda, context_doc, design_previsao_demanda, tasks_plan, code_review, validation_report, state_decisions [EXTRACTED 1.00]

## Communities (21 total, 4 thin omitted)

### Community 0 - "Visualizations & Plotting"
Cohesion: 0.09
Nodes (84): _as_frame(), _bridge(), _centered_moving_average_or_nan(), _dates(), _empty_message(), fig_backtest(), fig_best_model_fit(), fig_capacity() (+76 more)

### Community 1 - "ML Models & Validation"
Cohesion: 0.07
Nodes (63): Ferramentas de previsão de demanda da BebiBem., build_estimators(), cross_validate_temporal(), _feature_row(), metrics(), metrics_table(), Model comparison, temporal validation, metrics, and recursive backtests., Select lowest MAPE, using MAD for ties within 0.5 percentage points. (+55 more)

### Community 2 - "Project Config & Utilities"
Cohesion: 0.07
Nodes (63): CapacityLine, global_month_index(), month_index(), Defaults and case constants shared by the forecasting pipeline., Integer month index T = 12*(ano-ORIGIN_YEAR) + (mes-ORIGIN_MONTH); T=0 is Januar, Convert calendar dates to the integer month index T used on every timeline x-axi, Monthly capacity in cases before and after the documented expansion., apply_style() (+55 more)

### Community 3 - "Data Interpolation"
Cohesion: 0.07
Nodes (51): _as_numeric_x(), DegreeSelection, fill_gaps_linear(), _fit_coefficients(), _format_number(), _holdout_indices(), linear_interpolation(), PolyFitResult (+43 more)

### Community 4 - "Business Domain & Context"
Cohesion: 0.06
Nodes (39): BebiBem Company (Jundiaí-SP, organic premium foods), Factory Capacity Data (sucos 12k→15.6k, geleias 3k, doces 5k caixas/mês), Historical Demand Data Table (3 products × 36 months, 2022-2024), Error Metrics Suite (MAD, MSE, RMSE, MAPE, MPE, sMAPE), Exponential Regression (log-linear + normal equation, y=ae^{bx}), Fourier Harmonic Regression (P=12, K=2 harmonics), Holt-Winters Multiplicative Exponential Smoothing (m=12), KMeans Clustering (seasonal month regimes + product-year series) (+31 more)

### Community 5 - "Regression Models"
Cohesion: 0.15
Nodes (30): as_estimator(), _as_x(), _design_matrix(), _exponential_equation(), exponential_regression_loglinear(), exponential_regression_normal_equation(), _fit_exponential(), _format() (+22 more)

### Community 6 - "Data I/O & Preprocessing"
Cohesion: 0.13
Nodes (32): detect_layout(), fill_missing_months(), load_demand(), _long_to_tidy(), _month_number(), _normalize_columns(), normalize_product(), _normalize_year() (+24 more)

### Community 7 - "Plotting Helpers"
Cohesion: 0.12
Nodes (28): Axes, annotate_equation(), _existing_records(), _figure_title(), _least_dense_corner(), _metadata_for(), Shared plotting style and deterministic figure export helpers., Return the least dense corner, preferring lower-right on ties. (+20 more)

### Community 8 - "CLI Interface"
Cohesion: 0.15
Nodes (24): ArgumentParser, _build_parser(), _config_from_args(), main(), _parse_int_list(), _print_summary(), Command-line entry point for the BebiBem forecasting pipeline., Run the CLI and return the documented process exit code. (+16 more)

### Community 9 - "Feature Engineering"
Cohesion: 0.17
Nodes (25): build_features(), _cluster_columns(), _cluster_dummies(), _cluster_values(), _empty_feature_frame(), _month_cluster(), _month_dummies(), next_row() (+17 more)

### Community 10 - "Regime Classification"
Cohesion: 0.16
Nodes (21): build_regime_labels(), ClassificationResult, evaluate_classifier(), fit_regime_classifier(), Logistic classification of high-demand seasonal regimes., Evaluate with a fixed ``[[vn, fp], [fn, vp]]`` confusion layout., Mark months in the ``alta`` seasonal cluster as one., Select only features allowed for regime classification. (+13 more)

### Community 11 - "Time Series Clustering"
Cohesion: 0.19
Nodes (21): _choose_k(), cluster_months(), cluster_series(), ClusterResult, Deterministic seasonal and product-year clustering., Cluster product-year seasonal profiles after row-wise z-score normalization., Return monthly mean demand divided by each product's annual mean., Cluster monthly seasonal-index vectors with stable regime names. (+13 more)

### Community 12 - "Demand Forecasting"
Cohesion: 0.18
Nodes (21): fit_final(), _forecast_frame(), forecast_recursive(), forecast_tables(), _metric_lookup(), Future-only recursive demand forecasts and answer tables., Return monthly and integer annual forecast tables with holdout metrics., Fit the selected estimator on the complete available feature history. (+13 more)

### Community 13 - "LaTeX Formulas"
Cohesion: 0.15
Nodes (12): Single source of LaTeX formulas shared by figures and reports., Return selected time series formulas as mathtext lines for figure footnotes., timeseries_footnote(), _markdown_source(), _notebook(), test_notebook_documents_required_formulas_and_symbols(), test_notebook_execution_uses_isolated_output(), test_notebook_has_no_calculation_function_definitions() (+4 more)

### Community 14 - "Factory Capacity"
Cohesion: 0.23
Nodes (12): capacity_frame(), demand_in_cases(), Capacity scenario constants and explicit unit-to-case conversion., Return documented monthly capacity before/after expansion., Convert forecast units to whole cases only when an explicit factor is given., validate_units_per_case(), DataFrame, test_capacity_figure_aligns_peak_monthly_demand_and_shows_factor() (+4 more)

### Community 15 - "Documentation & Spec"
Cohesion: 0.31
Nodes (10): BebiBem Demand Forecasting Project, Case BebiBem - MBM - Acting 2026, Questão 5 - Demand Forecast for Own Store, Implementation Code Review, Feature Context and Implementation Decisions, Previsão de Demanda BebiBem Design, Previsão de Demanda BebiBem Specification, Project State and Architectural Decisions (AD-001..AD-013) (+2 more)

### Community 16 - "Determinism & Conventions"
Cohesion: 0.33
Nodes (6): Deterministic Output (random_state=42, metadata suppression, hash-stable), Single-Source LaTeX Formulas (formulas.py, 28 keys), Month Index T = 12*(year-2022)+(month-1) as X-axis, figures.py - 32-Figure Catalog Builder, formulas.py - LaTeX Formula Single Source (28 keys), plotting.py - Deterministic Multi-format Export

## Knowledge Gaps
- **14 isolated node(s):** `Index`, `ndarray`, `Timestamp`, `Series`, `Path` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InputError` connect `Data Interpolation` to `Visualizations & Plotting`, `ML Models & Validation`, `Data I/O & Preprocessing`, `Plotting Helpers`, `CLI Interface`, `Time Series Clustering`, `Demand Forecasting`, `LaTeX Formulas`, `Factory Capacity`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._
- **Why does `run()` connect `ML Models & Validation` to `Project Config & Utilities`, `Data Interpolation`, `Data I/O & Preprocessing`, `Plotting Helpers`, `CLI Interface`, `Feature Engineering`, `Time Series Clustering`, `Demand Forecasting`, `Factory Capacity`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `load_demand()` connect `Data I/O & Preprocessing` to `ML Models & Validation`, `Project Config & Utilities`, `Data Interpolation`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `InputError` (e.g. with `ArgumentParser` and `Axes`) actually correct?**
  _`InputError` has 26 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Ferramentas de previsão de demanda da BebiBem.`, `Capacity scenario constants and explicit unit-to-case conversion.`, `Return documented monthly capacity before/after expansion.` to the rest of the system?**
  _151 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Visualizations & Plotting` be split into smaller, more focused modules?**
  _Cohesion score 0.08645690834473324 - nodes in this community are weakly interconnected._
- **Should `ML Models & Validation` be split into smaller, more focused modules?**
  _Cohesion score 0.0710085933966531 - nodes in this community are weakly interconnected._