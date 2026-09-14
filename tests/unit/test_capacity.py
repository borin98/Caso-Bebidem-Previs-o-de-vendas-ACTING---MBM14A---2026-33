import matplotlib.pyplot as plt
import pandas as pd
import pytest

from bebibem.capacity import capacity_frame, demand_in_cases, validate_units_per_case
from bebibem.figures import fig_capacity
from bebibem.io_data import InputError


def test_capacity_frame_matches_case_constants_and_totals():
    result = capacity_frame().set_index("produto")
    assert result.loc["suco_premium", "antes"] == 12_000
    assert result.loc["suco_premium", "depois"] == 15_600
    assert result.loc["suco_premium", "delta"] == 3_600
    assert result.loc["geleia_de_frutas", "antes"] == 3_000
    assert result.loc["doce_de_frutas", "antes"] == 5_000
    assert result.loc["total", "antes"] == 20_000


def test_demand_in_cases_returns_none_without_explicit_conversion():
    forecast = pd.DataFrame({"unidades_previstas": [1, 13]})
    assert demand_in_cases(forecast, None) is None


def test_demand_in_cases_ceil_converts_units_to_cases():
    forecast = pd.DataFrame({"unidades_previstas": [1, 12, 13, 24]})
    result = demand_in_cases(forecast, 12)
    assert result["caixas"].tolist() == [1, 1, 2, 2]


def test_capacity_figure_aligns_peak_monthly_demand_and_shows_factor():
    forecast = pd.DataFrame(
        {
            "produto": ["suco_premium", "suco_premium", "geleia_de_frutas", "doce_de_frutas"],
            "ano": [2025, 2025, 2025, 2025],
            "mes": [1, 2, 1, 1],
            "unidades_previstas": [12, 24, 12, 12],
        }
    )

    figure = fig_capacity(capacity_frame(), forecast, units_per_case=12)

    assert "12 unidades/caixa" in figure.axes[0].get_title()
    assert len(figure.axes) == 2
    assert len(figure.axes[1].lines) == 1
    plt.close(figure)


def test_units_per_case_must_be_positive():
    with pytest.raises(InputError, match="maior que zero"):
        validate_units_per_case(0)
    with pytest.raises(InputError, match="maior que zero"):
        demand_in_cases(pd.DataFrame({"unidades": [1]}), -1)
