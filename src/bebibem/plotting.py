"""Shared plotting style and deterministic figure export helpers."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.text import Text

from .config import FIGURE_FORMATS, PNG_DPI, SEED
from .io_data import InputError

LOGGER = logging.getLogger(__name__)
INDEX_COLUMNS = ["nome", "titulo", "formatos", "caminho_relativo"]


def apply_style() -> None:
    """Apply the common, non-interactive style used by generated figures."""
    matplotlib.use("Agg", force=True)
    plt.rcParams.update(
        {
            "figure.dpi": 100,
            "savefig.dpi": PNG_DPI,
            "figure.figsize": (10, 6),
            "font.family": "DejaVu Sans",
            "axes.grid": True,
            "grid.alpha": 0.25,
            "axes.axisbelow": True,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.edgecolor": "white",
            "axes.edgecolor": "black",
            "axes.linewidth": 1.4,
            "svg.hashsalt": str(SEED),
        }
    )


def validate_formats(formats: Iterable[str]) -> tuple[str, ...]:
    """Validate and normalize requested output formats."""
    requested = tuple(formats)
    invalid = [format_name for format_name in requested if format_name not in FIGURE_FORMATS]
    if invalid:
        raise InputError(
            f"formato(s) inválido(s): {invalid}; formatos válidos: {', '.join(FIGURE_FORMATS)}"
        )
    if len(set(requested)) != len(requested):
        raise InputError(f"formatos duplicados: {requested}")
    if len(requested) == 0:
        raise InputError(f"é necessário informar ao menos um formato: {FIGURE_FORMATS}")
    return requested


def _figure_title(figure: Figure, title: str) -> str:
    if title != "":
        return title
    if len(figure.axes) == 0:
        return ""
    return figure.axes[0].get_title()


def _metadata_for(format_name: str) -> dict[str, None]:
    if format_name == "pdf":
        return {"CreationDate": None, "ModDate": None}
    return {"Date": None}


def _existing_records(index_path: Path) -> list[dict[str, str]]:
    if index_path.exists() is False:
        return []
    current = pd.read_csv(index_path, dtype=str).fillna("")
    return current[INDEX_COLUMNS].to_dict("records")


def write_figure_index(records: Sequence[dict[str, str]], outdir: Path) -> Path:
    """Write the deterministic figure catalog and return its path."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.csv"
    frame = pd.DataFrame(list(records), columns=INDEX_COLUMNS)
    frame.to_csv(index_path, index=False, lineterminator="\n")
    return index_path


def _is_dark(rgba: tuple[float, float, float, float]) -> bool:
    """Return True for a facecolor dark enough that only white text stays readable on it."""
    red, green, blue = rgba[:3]
    luminance = 0.299 * red + 0.587 * green + 0.114 * blue
    return luminance < 0.5


def _force_readable_text(figure: Figure) -> None:
    """Force black text everywhere, except cells whose own facecolor is dark enough to need white.

    Defends against ambient rcParams pollution (e.g. an IDE's dark-theme matplotlib patcher)
    baking white text into titles/labels/ticks/legends/tables at object-creation time; rcParams
    resets after creation do not reach already-built Text objects, so each one is fixed directly.
    """
    for axis in figure.axes:
        axis.title.set_color("black")
        axis.xaxis.label.set_color("black")
        axis.yaxis.label.set_color("black")
        for tick_label in axis.get_xticklabels() + axis.get_yticklabels():
            tick_label.set_color("black")
        legend = axis.get_legend()
        if legend is not None:
            for text in legend.get_texts():
                text.set_color("black")
            if legend.get_title() is not None:
                legend.get_title().set_color("black")
        for text in axis.texts:
            text.set_color("black")
        for table in axis.tables:
            for cell in table.get_celld().values():
                if _is_dark(cell.get_facecolor()):
                    continue
                cell.get_text().set_color("black")
    for text in figure.texts:
        text.set_color("black")
    if figure._suptitle is not None:
        figure._suptitle.set_color("black")


def _reinforce_spines(figure: Figure) -> None:
    """Force a visible black axis frame (all four spines) at a bumped linewidth.

    Same defense-in-depth as `_force_readable_text`: spine color/width is baked into the
    Axes at creation time, so a later `rcParams` reset alone would miss already-built figures.
    """
    for axis in figure.axes:
        for spine in axis.spines.values():
            spine.set_color("black")
            spine.set_linewidth(1.4)
            spine.set_visible(True)


def save_figure(
    figure: Figure,
    name: str,
    outdir: Path,
    formats: Sequence[str] = FIGURE_FORMATS,
    title: str = "",
) -> list[Path]:
    """Save one figure in requested formats and update the figure catalog."""
    requested = validate_formats(formats)
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for format_name in FIGURE_FORMATS:
        if format_name in requested:
            continue
        stale_path = output_dir / format_name / f"{name}.{format_name}"
        if stale_path.exists():
            stale_path.unlink()
    apply_style()
    figure.set_facecolor("white")
    for axis in figure.axes:
        axis.set_facecolor("white")
    _force_readable_text(figure)
    _reinforce_spines(figure)
    paths: list[Path] = []
    for format_name in requested:
        format_dir = output_dir / format_name
        path = format_dir / f"{name}.{format_name}"
        path.parent.mkdir(parents=True, exist_ok=True)
        save_kwargs = {
            "metadata": _metadata_for(format_name),
            "facecolor": "white",
            "edgecolor": "white",
            "transparent": False,
        }
        if format_name == "png":
            save_kwargs["dpi"] = PNG_DPI
        figure.savefig(path, format=format_name, **save_kwargs)
        paths.append(path)
    records = _existing_records(output_dir / "index.csv")
    record = {
        "nome": name,
        "titulo": _figure_title(figure, title),
        "formatos": ",".join(requested),
        "caminho_relativo": ";".join(str(path.relative_to(output_dir)) for path in paths),
    }
    records = [current for current in records if current["nome"] != name]
    records.append(record)
    records.sort(key=lambda current: current["nome"])
    write_figure_index(records, output_dir)
    return paths


def _least_dense_corner(axis: Axes) -> tuple[float, float, str, str]:
    """Return the least dense corner, preferring lower-right on ties."""
    densities = {
        "right_bottom": 0,
        "left_bottom": 0,
        "right_top": 0,
        "left_top": 0,
    }
    x_limits = axis.get_xlim()
    y_limits = axis.get_ylim()
    x_span = x_limits[1] - x_limits[0]
    y_span = y_limits[1] - y_limits[0]
    for collection in axis.collections:
        offsets = np.asarray(collection.get_offsets(), dtype=float)
        valid = np.isfinite(offsets).all(axis=1)
        if np.count_nonzero(valid) == 0:
            continue
        normalized_x = (offsets[valid, 0] - x_limits[0]) / x_span
        normalized_y = (offsets[valid, 1] - y_limits[0]) / y_span
        densities["left_bottom"] += int(
            np.count_nonzero((normalized_x < 0.5) & (normalized_y < 0.5))
        )
        densities["right_bottom"] += int(
            np.count_nonzero((normalized_x >= 0.5) & (normalized_y < 0.5))
        )
        densities["left_top"] += int(np.count_nonzero((normalized_x < 0.5) & (normalized_y >= 0.5)))
        densities["right_top"] += int(
            np.count_nonzero((normalized_x >= 0.5) & (normalized_y >= 0.5))
        )
    priority = ["right_bottom", "left_bottom", "right_top", "left_top"]
    corner = min(priority, key=lambda value: (densities[value], priority.index(value)))
    anchors = {
        "right_bottom": (0.98, 0.02, "right", "bottom"),
        "left_bottom": (0.02, 0.02, "left", "bottom"),
        "right_top": (0.98, 0.98, "right", "top"),
        "left_top": (0.02, 0.98, "left", "top"),
    }
    return anchors[corner]


def annotate_equation(axis: Axes, label: str) -> Text:
    """Add a mathtext equation in the least dense corner."""
    x, y, horizontal_alignment, vertical_alignment = _least_dense_corner(axis)
    return axis.text(
        x,
        y,
        label,
        transform=axis.transAxes,
        ha=horizontal_alignment,
        va=vertical_alignment,
        bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
    )
