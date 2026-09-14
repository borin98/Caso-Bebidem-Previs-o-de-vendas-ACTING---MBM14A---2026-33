from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

from bebibem.formulas import FORMULAS

NOTEBOOK = Path("notebooks/01_analise_demanda_bebibem.ipynb")


def _notebook() -> dict:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def _markdown_source(notebook: dict) -> str:
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell["cell_type"] == "markdown"
    )


def test_notebook_has_required_sections_in_narrative_order() -> None:
    notebook = _notebook()
    markdown = _markdown_source(notebook)
    headings = [
        "## Dados e notação",
        "## Pontos observados",
        "## Interpolações linear e polinomial",
        "## Médias móveis",
        "## Clusters sazonais",
        "## Comparação dos modelos",
        "## Backtest de 2024",
        "## Previsão dos próximos anos",
    ]
    positions = [markdown.index(heading) for heading in headings]
    assert positions == sorted(positions)


def test_notebook_documents_required_formulas_and_symbols() -> None:
    notebook = _notebook()
    markdown = _markdown_source(notebook)
    required_formula_keys = (
        "linear_interp",
        "poly_fit",
        "ma_simple",
        "seasonal_index",
        "kmeans",
        "silhouette",
        "ridge",
        "recursive_forecast",
        "mad",
        "mse",
        "rmse",
        "mape",
        "mpe",
    )
    for key in required_formula_keys:
        formula = FORMULAS[key]
        assert formula in markdown or key in markdown
    for symbol in ("$y_t$", "$\\hat{y}_t$", "$n$", "$w$", "$d$", "$k$"):
        assert symbol in markdown


def test_notebook_has_no_calculation_function_definitions() -> None:
    notebook = _notebook()
    code = [
        "".join(cell.get("source", [])) for cell in notebook["cells"] if cell["cell_type"] == "code"
    ]
    nodes = [node for source in code for node in ast.walk(ast.parse(source))]
    assert all(not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in nodes)
    joined = "\n".join(code)
    assert "bebibem" in joined
    assert "data/example/demanda_exemplo.csv" in joined


def test_notebook_is_saved_without_execution_outputs() -> None:
    notebook = _notebook()
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    assert len(code_cells) >= 8
    assert all(cell["execution_count"] is None for cell in code_cells)
    assert all(cell["outputs"] == [] for cell in code_cells)


def test_notebook_execution_uses_isolated_output(tmp_path: Path) -> None:
    sentinel = Path("reports/tables/notebook-isolation-sentinel.txt")
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_bytes(b"real-report")
    before = sentinel.read_bytes()
    environment = os.environ.copy()
    environment["BEBIBEM_NOTEBOOK_OUTDIR"] = str(tmp_path / "notebook-output")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            str(NOTEBOOK),
            "--output",
            "executed.ipynb",
            "--output-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=180,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert sentinel.read_bytes() == before
    assert (tmp_path / "notebook-output" / "tables" / "error_metrics.csv").is_file()
    sentinel.unlink()
