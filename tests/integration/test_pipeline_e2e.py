from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from bebibem.pipeline import PipelineConfig, resolve_steps, run

EXAMPLE = Path("data/example/demanda_exemplo.csv").resolve()
EXPECTED_FIGURES = 32
EXPECTED_TABLES = 13


def test_complete_pipeline_writes_catalog_and_tables(tmp_path: Path) -> None:
    result = run(
        PipelineConfig(
            input=EXAMPLE,
            outdir=tmp_path,
            formats=("png",),
            seed=42,
        )
    )

    assert len(result.figures) == EXPECTED_FIGURES
    assert len(result.tables) == EXPECTED_TABLES
    assert len(result.annual_forecast) == 3
    assert (tmp_path / "figures" / "index.csv").is_file()
    assert len(pd.read_csv(tmp_path / "figures" / "index.csv")) == EXPECTED_FIGURES
    assert len(list((tmp_path / "figures" / "png").rglob("*.png"))) == EXPECTED_FIGURES
    assert len(list((tmp_path / "tables").glob("*.csv"))) == EXPECTED_TABLES
    assert set(result.annual_forecast["ano"]) == {2025}


def test_resolve_steps_adds_dependencies_in_canonical_order(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="bebibem.pipeline"):
        steps = resolve_steps(("plots", "interp"))

    assert steps == ["load", "interp", "plots"]
    assert "incluída" in caplog.text


def test_pipeline_rerun_preserves_unrelated_output(tmp_path: Path) -> None:
    config = PipelineConfig(input=EXAMPLE, outdir=tmp_path, formats=("png",), seed=42)
    run(config)
    sentinel = tmp_path / "tables" / "unrelated.csv"
    sentinel.write_text("keep\n", encoding="utf-8")

    run(config)

    assert sentinel.read_text(encoding="utf-8") == "keep\n"
    assert len(list((tmp_path / "figures" / "png").rglob("*.png"))) == EXPECTED_FIGURES


def test_partial_steps_write_only_dependencies_and_requested_artifacts(tmp_path: Path) -> None:
    result = run(
        PipelineConfig(
            input=EXAMPLE,
            outdir=tmp_path,
            formats=("png",),
            steps=("plots", "interp"),
            seed=42,
        )
    )

    table_names = {path.name for path in result.tables}
    figure_names = {path.stem for path in result.figures}
    assert table_names == {"demand_tidy.csv", "interpolation_fit.csv"}
    assert figure_names == {
        "01_pontos_suco_premium",
        "02_pontos_geleia_de_frutas",
        "03_pontos_doce_de_frutas",
        "04_pontos_todos",
        "05_interpolacao_suco_premium",
        "06_interpolacao_geleia_de_frutas",
        "07_interpolacao_doce_de_frutas",
    }
    assert not (tmp_path / "tables" / "error_metrics.csv").exists()


def test_pipeline_metrics_are_deterministic_across_runs(tmp_path: Path) -> None:
    output_dirs = [tmp_path / "first", tmp_path / "second"]
    for output_dir in output_dirs:
        run(
            PipelineConfig(
                input=EXAMPLE,
                outdir=output_dir,
                formats=("png",),
                steps=("ml",),
                seed=42,
            )
        )

    first = pd.read_csv(output_dirs[0] / "tables" / "error_metrics.csv")
    second = pd.read_csv(output_dirs[1] / "tables" / "error_metrics.csv")
    pd.testing.assert_frame_equal(first, second, check_exact=False, rtol=0, atol=1e-10)


def test_one_year_input_skips_clustering_and_ml_with_stable_status(tmp_path: Path) -> None:
    one_year = tmp_path / "one_year.csv"
    pd.read_csv(EXAMPLE).query("ano == 2022").to_csv(one_year, index=False)

    result = run(
        PipelineConfig(
            input=one_year,
            outdir=tmp_path / "reports",
            formats=("png",),
            steps=("ml",),
            seed=42,
        )
    )

    month_table = pd.read_csv(tmp_path / "reports" / "tables" / "clustering_months.csv")
    series_table = pd.read_csv(tmp_path / "reports" / "tables" / "clustering_series.csv")
    error_metrics = pd.read_csv(tmp_path / "reports" / "tables" / "error_metrics.csv")
    assert month_table["status"].eq("insufficient_data").any()
    assert series_table["status"].eq("insufficient_data").any()
    assert error_metrics["metric_note"].eq("insufficient_data").all()
    assert result.annual_forecast.empty


def test_capacity_pipeline_keeps_monthly_peak_and_horizon_total_separate(tmp_path: Path) -> None:
    output_dir = tmp_path / "capacity"
    run(
        PipelineConfig(
            input=EXAMPLE,
            outdir=output_dir,
            formats=("png",),
            steps=("capacity", "plots"),
            units_per_case=12,
            seed=42,
        )
    )

    table = pd.read_csv(output_dir / "tables" / "capacity_vs_demand.csv")
    suco = table.loc[table["linha"] == "suco_premium"].iloc[0]
    assert suco["demanda_caixas_total"] > suco["demanda_caixas"]
    assert table["demanda_caixas"].notna().all()
    assert (output_dir / "figures" / "png" / "capacidade" / "28_capacidade_case.png").is_file()


def test_cli_read_only_output_returns_two(tmp_path: Path, monkeypatch, capsys) -> None:
    from bebibem.cli import main

    output_dir = tmp_path / "read-only"
    original_mkdir = Path.mkdir

    def refuse_output_directory(self, *args, **kwargs):
        if self == output_dir:
            raise PermissionError("read-only output")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", refuse_output_directory)

    code = main(
        [
            "--input",
            str(EXAMPLE),
            "--outdir",
            str(output_dir),
            "--steps",
            "load",
        ]
    )

    assert code == 2
    assert str(output_dir) in capsys.readouterr().out


def test_cli_help_lists_public_flags(capsys) -> None:
    from bebibem.cli import main

    assert main(["--help"]) == 0
    help_text = capsys.readouterr().out
    for flag in (
        "--input",
        "--outdir",
        "--formats",
        "--poly-degree",
        "--ma-windows",
        "--horizon-years",
        "--k-months",
        "--units-per-case",
        "--steps",
        "--seed",
        "--log-level",
    ):
        assert flag in help_text


def test_cli_defaults_use_raw_input_and_reports(tmp_path: Path, monkeypatch) -> None:
    import shutil

    from bebibem.cli import main

    monkeypatch.chdir(tmp_path)
    default_input = tmp_path / "data" / "raw" / "demanda_loja_propria.csv"
    default_input.parent.mkdir(parents=True)
    shutil.copy(EXAMPLE.resolve(), default_input)

    assert main(["--formats", "png"]) == 0
    assert (tmp_path / "reports" / "tables" / "forecast_annual.csv").is_file()


def test_cli_partial_steps_prints_counts_and_annual_summary(tmp_path: Path, capsys) -> None:
    from bebibem.cli import main

    code = main(
        [
            "--input",
            str(EXAMPLE),
            "--outdir",
            str(tmp_path),
            "--formats",
            "png",
            "--steps",
            "plots,interp",
        ]
    )

    assert code == 0
    output = capsys.readouterr().out
    assert "Figuras: 7" in output
    assert "Tabelas: 2" in output
    assert "Total anual" not in output
    assert not (tmp_path / "tables" / "forecast_annual.csv").exists()


def test_cli_input_error_returns_two(tmp_path: Path, capsys) -> None:
    from bebibem.cli import main

    code = main(["--input", str(tmp_path / "missing.csv"), "--steps", "load"])

    assert code == 2
    assert "Erro de validação" in capsys.readouterr().out


def test_cli_unexpected_error_returns_one_without_traceback(monkeypatch, capsys) -> None:
    from bebibem import cli

    def fail(_config):
        raise RuntimeError("falha inesperada")

    monkeypatch.setattr(cli, "run", fail)
    code = cli.main(["--log-level", "warning"])

    assert code == 1
    output = capsys.readouterr().out
    assert "Erro inesperado: falha inesperada" in output
    assert "Traceback" not in output


def test_cli_debug_unexpected_error_includes_traceback(monkeypatch, capsys) -> None:
    from bebibem import cli

    def fail(_config):
        raise RuntimeError("falha inesperada")

    monkeypatch.setattr(cli, "run", fail)
    code = cli.main(["--log-level", "debug"])

    assert code == 1
    captured = capsys.readouterr()
    assert "Traceback" in captured.err
