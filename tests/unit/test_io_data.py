from pathlib import Path

import pandas as pd
import pytest

from bebibem.io_data import InputError, load_demand

WIDE_COLUMNS = [
    "produto",
    "ano",
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
]


def wide_row(**overrides):
    row = {"produto": "Suco Premium", "ano": 2022}
    row.update(dict.fromkeys(WIDE_COLUMNS[2:], 100))
    row.update(overrides)
    return row


def test_load_demand_normalizes_wide_layout_and_preserves_label(tmp_path: Path):
    path = tmp_path / "wide.csv"
    pd.DataFrame([wide_row()]).to_csv(path, index=False)

    result = load_demand(path)

    assert list(result.columns) == ["produto", "produto_label", "ano", "mes", "data", "unidades"]
    assert len(result) == 12
    assert result["produto"].unique().tolist() == ["suco_premium"]
    assert result["produto_label"].unique().tolist() == ["Suco Premium"]
    assert result["mes"].tolist() == list(range(1, 13))
    assert result.loc[result["mes"] == 1, "data"].iloc[0] == pd.Timestamp("2022-01-01")


def test_load_demand_accepts_long_layout_and_portuguese_month_names(tmp_path: Path):
    path = tmp_path / "long.csv"
    pd.DataFrame(
        {
            "produto": ["Geleia de frutas", "Geleia de frutas", "Geleia de frutas"],
            "ano": [2022, 2022, 2022],
            "mes": ["jan", "janeiro", "Jan"],
            "unidades": [10, 20, 30],
        }
    ).to_csv(path, index=False)

    with pytest.raises(InputError, match="duplicad"):
        load_demand(path)

    unique_path = tmp_path / "long_unique.csv"
    pd.DataFrame(
        {
            "produto": ["Geleia de frutas", "Geleia de frutas", "Geleia de frutas"],
            "ano": [2022, 2022, 2022],
            "mes": ["jan", "fevereiro", "Mar"],
            "unidades": [10, 20, 30],
        }
    ).to_csv(unique_path, index=False)

    result = load_demand(unique_path)

    assert result["mes"].tolist() == [1, 2, 3]
    assert result["unidades"].tolist() == [10.0, 20.0, 30.0]


def test_load_demand_reports_missing_required_columns(tmp_path: Path):
    path = tmp_path / "missing.csv"
    pd.DataFrame({"produto": ["Suco Premium"], "ano": [2022]}).to_csv(path, index=False)

    with pytest.raises(InputError) as error:
        load_demand(path)

    message = str(error.value)
    assert "esperadas" in message
    assert "encontradas" in message
    assert "jan" in message


def test_load_demand_reports_duplicate_product_year_month(tmp_path: Path):
    path = tmp_path / "duplicate.csv"
    pd.DataFrame(
        {
            "produto": ["Suco Premium", "Suco Premium"],
            "ano": [2022, 2022],
            "mes": [1, 1],
            "unidades": [10, 11],
        }
    ).to_csv(path, index=False)

    with pytest.raises(InputError, match=r"suco_premium.*2022.*1"):
        load_demand(path)


@pytest.mark.parametrize(
    ("column", "values", "offender"),
    [
        ("unidades", ["abc"], "suco_premium/2022/1"),
        ("unidades", [-1], "suco_premium/2022/1"),
        ("unidades", [None], "suco_premium/2022/1"),
    ],
)
def test_load_demand_rejects_invalid_units_with_offender(tmp_path: Path, column, values, offender):
    path = tmp_path / f"invalid_{column}_{values[0]}.csv"
    pd.DataFrame({"produto": ["Suco Premium"], "ano": [2022], "mes": [1], column: values}).to_csv(
        path, index=False
    )

    with pytest.raises(InputError, match=offender):
        load_demand(path)


def test_load_demand_rejects_explicit_wide_null_with_offender(tmp_path: Path):
    path = tmp_path / "wide_null.csv"
    pd.DataFrame([wide_row(jun=None)]).to_csv(path, index=False)

    with pytest.raises(InputError, match=r"suco_premium/2022/6"):
        load_demand(path)


def test_load_demand_fills_missing_middle_month_with_nan_and_warning(tmp_path: Path, caplog):
    path = tmp_path / "gap.csv"
    pd.DataFrame(
        {
            "produto": ["Suco Premium", "Suco Premium"],
            "ano": [2022, 2022],
            "mes": [1, 3],
            "unidades": [10, 30],
        }
    ).to_csv(path, index=False)

    with caplog.at_level("WARNING"):
        result = load_demand(path)

    missing = result.loc[result["mes"] == 2].iloc[0]
    assert pd.isna(missing["unidades"])
    assert "mês ausente" in caplog.text


def test_load_demand_reports_missing_file_path(tmp_path: Path):
    path = tmp_path / "does-not-exist.csv"

    with pytest.raises(InputError, match=str(path)):
        load_demand(path)
