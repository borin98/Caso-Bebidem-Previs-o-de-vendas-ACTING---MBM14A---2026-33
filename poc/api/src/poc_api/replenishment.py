"""Regras de reposição do POC (POC-06…13) e posições de demonstração (A14)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from bebibem.config import SEED

SERVICE_LEVEL_Z = {"0.90": 1.2816, "0.95": 1.6449, "0.975": 1.96, "0.99": 2.3263}
STATUS_ORDER = ("ruptura", "comprar", "adequado", "excesso")
MONTH_ABBR = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
DEMO_LEAD_TIME = 1.0


def accuracy(mape: float | None) -> float | None:
    """Commercial accuracy ``max(0, 100 − MAPE)``; ``None`` when MAPE is not applicable."""
    if mape is None:
        return None
    return max(0.0, 100.0 - mape)


def month_text(value: str) -> str:
    """``2025-03`` → ``mar/2025``."""
    year, month = value.split("-")
    return f"{MONTH_ABBR[int(month) - 1]}/{year}"


def _decimal_text(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def _coverage(available: float, values: list[float]) -> tuple[float, str]:
    """Months covered by ``available`` consuming the forecast in order (POC-09)."""
    covered = 0.0
    remaining = available
    for demand in values:
        if demand <= 0:
            covered += 1
            continue
        if remaining < demand:
            covered += remaining / demand
            return round(covered, 1), _decimal_text(covered)
        remaining -= demand
        covered += 1
    return float(len(values)), f"> {len(values)}"


def _buy_by(
    projection: list[dict[str, object]], available: float, safety: float, lead_time: float
) -> str:
    """First month whose final stock drops below SS, minus lead time (POC-10)."""
    below = [index for index, row in enumerate(projection) if row["final"] < safety]
    if available < safety:
        below = [0]
    if len(below) == 0:
        return "–"
    index = math.floor(below[0] - lead_time)
    if index <= 0:
        return "Imediato"
    return month_text(str(projection[index]["periodo"]))


def _status(need: float, has_rupture: bool, available: float, demand: float, safety: float) -> str:
    if need > 0 and has_rupture:
        return "ruptura"
    if need > 0:
        return "comprar"
    if demand > 0 and available > 2 * (demand + safety):
        return "excesso"
    return "adequado"


def _value_or_default(value: float | None, default: float) -> float:
    if value is None:
        return default
    return value


def plan_product(
    forecast: list[dict[str, object]],
    rmse: float,
    position: dict[str, float | None],
    params: dict[str, object],
) -> dict[str, object]:
    """Replenishment plan for one product from its forecast points (``periodo``, ``valor``)."""
    lead_time = float(_value_or_default(position.get("lead_time"), params["lead_time_padrao"]))
    multiple = float(_value_or_default(position.get("multiplo"), params["multiplo_padrao"]))
    horizon = int(params["horizonte_meses"])
    stock = position.get("estoque")
    incoming = position.get("a_receber")
    available = float(_value_or_default(stock, 0) + _value_or_default(incoming, 0))
    values = [float(point["valor"]) for point in forecast]
    demand = sum(values[:horizon])
    safety = SERVICE_LEVEL_Z[str(params["nivel_servico"])] * rmse * math.sqrt(max(lead_time, 1))
    need = max(0.0, demand + safety - available)
    if need > 0:
        need = math.ceil(need / multiple - 1e-9) * multiple
    projection: list[dict[str, object]] = []
    opening = available
    for point in forecast[:horizon]:
        closing = opening - float(point["valor"])
        projection.append(
            {
                "periodo": point["periodo"],
                "inicial": opening,
                "venda_prevista": float(point["valor"]),
                "final": closing,
            }
        )
        opening = closing
    covered, covered_text = _coverage(available, values)
    has_rupture = any(row["final"] < 0 for row in projection)
    capacity = position.get("capacidade")
    exceeds = None if capacity is None else available + need > capacity
    return {
        "lead_time": lead_time,
        "multiplo": multiple,
        "disponivel": available,
        "estoque_informado": stock is not None or incoming is not None,
        "demanda_horizonte": demand,
        "estoque_seguranca": safety,
        "necessidade": float(need),
        "projecao": projection,
        "cobertura_meses": covered,
        "cobertura_texto": covered_text,
        "comprar_ate_texto": _buy_by(projection, available, safety, lead_time),
        "situacao": _status(need, has_rupture, available, demand, safety),
        "capacidade": capacity,
        "excede_capacidade": exceeds,
    }


def demo_positions(frame: pd.DataFrame, seed: int = SEED) -> dict[str, dict[str, float | None]]:
    """Random demo positions (A14): stock in [0; 3m], incoming in [0; m], lead time 1."""
    rng = np.random.default_rng(seed)
    positions: dict[str, dict[str, float | None]] = {}
    for product in frame["produto"].drop_duplicates():
        history = frame.loc[frame["produto"].eq(product)].sort_values("data")
        monthly_mean = float(history["unidades"].tail(12).mean())
        stock = int(rng.integers(0, round(3 * monthly_mean), endpoint=True))
        incoming = int(rng.integers(0, round(monthly_mean), endpoint=True))
        positions[str(product)] = {
            "estoque": float(stock),
            "a_receber": float(incoming),
            "lead_time": DEMO_LEAD_TIME,
            "multiplo": None,
            "capacidade": None,
        }
    return positions
