import hashlib
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.text import Text

from bebibem.io_data import InputError
from bebibem.plotting import (
    annotate_equation,
    apply_style,
    save_figure,
    validate_formats,
    write_figure_index,
)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_figure():
    figure, axis = plt.subplots()
    axis.plot([0, 1], [1, 2])
    return figure, axis


def test_apply_style_uses_noninteractive_backend_and_fixed_axes_defaults():
    apply_style()

    assert matplotlib.get_backend().lower() == "agg"
    assert matplotlib.rcParams["axes.grid"] is True


def test_save_figure_writes_requested_png_svg_and_pdf(tmp_path: Path):
    figure, _ = make_figure()

    paths = save_figure(figure, "01_teste", tmp_path, formats=("png", "svg", "pdf"))

    assert {path.suffix for path in paths} == {".png", ".svg", ".pdf"}
    assert all(path.parent == tmp_path / path.suffix[1:] for path in paths)
    assert all(path.exists() and path.stat().st_size > 0 for path in paths)


def test_save_figure_is_deterministic_for_distinct_figures(tmp_path: Path):
    first_figure, _ = make_figure()
    second_figure, _ = make_figure()
    first = save_figure(first_figure, "stable", tmp_path / "first")
    second = save_figure(second_figure, "stable", tmp_path / "second")

    assert {path.suffix: file_hash(path) for path in first} == {
        path.suffix: file_hash(path) for path in second
    }
    plt.close(first_figure)
    plt.close(second_figure)


def test_save_figure_subset_removes_stale_siblings_and_preserves_unrelated(tmp_path: Path):
    figure, _ = make_figure()
    save_figure(figure, "subset", tmp_path, formats=("png", "svg", "pdf"))
    unrelated = tmp_path / "svg" / "other.svg"
    unrelated.write_text("keep", encoding="utf-8")

    paths = save_figure(figure, "subset", tmp_path, formats=("png",))

    assert [path.suffix for path in paths] == [".png"]
    assert (tmp_path / "png" / "subset.png").exists()
    assert (tmp_path / "svg" / "subset.svg").exists() is False
    assert (tmp_path / "pdf" / "subset.pdf").exists() is False
    assert unrelated.read_text(encoding="utf-8") == "keep"
    plt.close(figure)


def test_validate_formats_reports_supported_values():
    with pytest.raises(InputError, match=r"png.*svg.*pdf"):
        validate_formats(("jpg",))


def test_write_figure_index_contains_catalog_fields(tmp_path: Path):
    records = [
        {
            "nome": "01_teste",
            "titulo": "Título",
            "formatos": "png,svg",
            "caminho_relativo": "png/01_teste.png;svg/01_teste.svg",
        }
    ]

    index_path = write_figure_index(records, tmp_path)
    index = pd.read_csv(index_path)

    assert list(index.columns) == ["nome", "titulo", "formatos", "caminho_relativo"]
    assert index.iloc[0].to_dict() == records[0]


def test_annotate_equation_returns_text_with_transparent_white_bbox():
    figure, axis = make_figure()

    artist = annotate_equation(axis, "$y = 2,000 x + 1,000$")

    assert isinstance(artist, Text)
    assert artist.get_text() == "$y = 2,000 x + 1,000$"
    assert artist.get_bbox_patch().get_facecolor()[-1] == pytest.approx(0.75)
    assert artist.get_bbox_patch().get_facecolor()[:3] == pytest.approx((1, 1, 1))
    plt.close(figure)
