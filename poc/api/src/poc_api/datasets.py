"""Versões de dados: caso, importação, fechamento de mês, edição da grade e diferença."""

from __future__ import annotations

import re
from pathlib import Path

import bebibem
import pandas as pd
from bebibem.config import DEFAULT_INPUT
from bebibem.io_data import InputError, load_demand, normalize_product

from . import store
from .engine import period, tidy_frame, validate_history
from .replenishment import demo_positions
from .schemas import (
    ApiError,
    CloseMonth,
    DatasetEdits,
    DatasetImport,
    Parameters,
)

CASE_CSV = Path(bebibem.__file__).resolve().parents[2] / DEFAULT_INPUT
PERIOD_PATTERN = re.compile(r"^(19|20|21)\d{2}-(0[1-9]|1[0-2])$")
MAX_PRODUCTS = 50
MAX_MONTHS = 240
MAX_UNITS = 1_000_000_000
POSITION_FIELDS = ("estoque", "a_receber", "lead_time", "multiplo")
EMPTY_POSITION = {
    "estoque": None,
    "a_receber": None,
    "lead_time": None,
    "multiplo": None,
    "capacidade": None,
}


def _rejected(problems: list[str]) -> ApiError:
    return ApiError(
        422,
        "validacao_invalida",
        f"Dados recusados: {len(problems)} problema(s) encontrado(s)",
        problems,
    )


def _quantity_problem(where: str, value: float | None) -> str | None:
    """PT-BR problem for a sales value, or ``None`` when it is an integer in [0; 1e9]."""
    if value is None:
        return f"{where}: quantidade vazia ou não numérica"
    if value < 0:
        return f"{where}: quantidade negativa ({value:g})"
    if float(value).is_integer() is False:
        return f"{where}: quantidade não inteira ({value:g})"
    if value > MAX_UNITS:
        return f"{where}: quantidade acima de 1 000 000 000"
    return None


def _limit_problems(rows: pd.DataFrame) -> list[str]:
    problems: list[str] = []
    products = rows["produto"].drop_duplicates()
    if len(products) > MAX_PRODUCTS:
        problems.append(f"{len(products)} produtos; máximo {MAX_PRODUCTS}")
    months = rows.groupby("produto", sort=False)["periodo"].nunique()
    for product, count in months.items():
        if count > MAX_MONTHS:
            problems.append(f"{product}: {count} meses; máximo {MAX_MONTHS}")
    return problems


def _check_history(rows: pd.DataFrame) -> None:
    problems = _limit_problems(rows) + validate_history(tidy_frame(rows))
    if len(problems) > 0:
        raise _rejected(problems)


def _meta(rows: pd.DataFrame, origem: str, pai_id: str | None, nome_arquivo: str | None) -> dict:
    products = rows[["produto", "produto_label"]].drop_duplicates("produto")
    periods = sorted(rows["periodo"].unique())
    return {
        "id": store.new_id("ds"),
        "criado_em": store.now_iso(),
        "origem": origem,
        "pai_id": pai_id,
        "nome_arquivo": nome_arquivo,
        "produtos": [
            {"produto": row.produto, "label": row.produto_label} for row in products.itertuples()
        ],
        "periodo_inicio": periods[0],
        "periodo_fim": periods[-1],
        "n_meses": len(periods),
    }


def _create(
    rows: pd.DataFrame, origem: str, pai_id: str | None = None, nome_arquivo: str | None = None
) -> dict:
    meta = _meta(rows, origem, pai_id, nome_arquivo)
    store.save_dataset(meta, rows)
    return meta


# ---------- Configurações do workspace (posições) ----------


def read_settings() -> dict:
    """Workspace settings with defaults when nothing was saved yet."""
    saved = store.load_settings()
    if saved is None:
        return {
            "parametros": Parameters().model_dump(),
            "posicoes": {},
            "posicoes_demo": False,
            "escolhas_manuais": {},
        }
    return saved


def _write_positions(positions: dict[str, dict], demo: bool) -> None:
    settings = read_settings()
    merged = {**settings["posicoes"]}
    for product, position in positions.items():
        merged[product] = {**EMPTY_POSITION, **merged.get(product, {}), **position}
    settings["posicoes"] = merged
    settings["posicoes_demo"] = demo
    store.save_settings(settings)


def _missing_stock_warnings(meta: dict) -> list[str]:
    positions = read_settings()["posicoes"]
    warnings: list[str] = []
    for product in meta["produtos"]:
        position = positions.get(product["produto"], EMPTY_POSITION)
        if position.get("estoque") is None and position.get("a_receber") is None:
            warnings.append(f"{product['label']}: sem estoque informado, considerado zero")
    return warnings


# ---------- Caso ----------


def load_case() -> tuple[dict, list[str]]:
    """Create the ``caso`` version from ``data/raw`` with the seeded demo positions (A14)."""
    frame = load_demand(CASE_CSV)
    rows = pd.DataFrame(
        {
            "produto": frame["produto"],
            "produto_label": frame["produto_label"],
            "periodo": frame["data"].dt.strftime("%Y-%m"),
            "unidades": frame["unidades"],
        }
    )
    meta = _create(rows, "caso", nome_arquivo=CASE_CSV.name)
    _write_positions(demo_positions(frame), demo=True)
    return meta, []


def seed() -> dict | None:
    """Create the case version when the data directory is empty (POC-14)."""
    if store.has_datasets():
        return None
    meta, _ = load_case()
    return meta


# ---------- Importação ----------


def _slug(label: str) -> str | None:
    try:
        return normalize_product(label)
    except InputError:
        return None


def _import_frame(payload: DatasetImport) -> tuple[pd.DataFrame, list[str]]:
    problems: list[str] = []
    records: list[dict] = []
    for number, row in enumerate(payload.linhas, start=1):
        label = row.produto.strip()
        slug = _slug(label)
        if slug is None:
            problems.append(f"linha {number}: produto vazio ou inválido")
            continue
        if PERIOD_PATTERN.match(row.periodo) is None:
            problems.append(f"linha {number} ({label}): período não reconhecido '{row.periodo}'")
            continue
        problem = _quantity_problem(f"{label} {row.periodo}", row.quantidade)
        if problem is not None:
            problems.append(problem)
            continue
        records.append(
            {**row.model_dump(), "produto": slug, "produto_label": label, "linha": number}
        )
    return pd.DataFrame(records), problems


def _import_positions(frame: pd.DataFrame) -> dict[str, dict]:
    """Latest informed value of each optional column per product (as in the reference HTML)."""
    positions: dict[str, dict] = {}
    for product, group in frame.sort_values(["periodo", "linha"]).groupby("produto", sort=False):
        position: dict[str, float] = {}
        for field in POSITION_FIELDS:
            informed = group[field].dropna()
            if len(informed) == 0:
                continue
            position[field] = float(informed.iloc[-1])
        if len(position) == 0:
            continue
        positions[str(product)] = position
    return positions


def _position_problems(positions: dict[str, dict]) -> list[str]:
    problems: list[str] = []
    for product, position in positions.items():
        for field, value in position.items():
            if value < 0:
                problems.append(f"{product}: {field} negativo ({value:g})")
        if position.get("lead_time", 0) > 12:
            problems.append(f"{product}: lead time acima de 12 meses")
        if position.get("multiplo", 1) < 1:
            problems.append(f"{product}: múltiplo de compra menor que 1")
    return problems


def import_rows(payload: DatasetImport) -> tuple[dict, list[str]]:
    """Validate normalized spreadsheet rows and create an ``importacao`` version (POC-15/16)."""
    frame, problems = _import_frame(payload)
    if len(problems) > 0:
        raise _rejected(problems)
    rows = (
        frame.groupby(["produto", "periodo"], sort=False)
        .agg(produto_label=("produto_label", "first"), unidades=("quantidade", "sum"))
        .reset_index()
    )
    order = frame["produto"].drop_duplicates().tolist()
    rows["ordem"] = rows["produto"].map(order.index)
    rows = rows.sort_values(["ordem", "periodo"]).drop(columns="ordem")
    _check_history(rows)
    positions = _import_positions(frame)
    problems = _position_problems(positions)
    if len(problems) > 0:
        raise _rejected(problems)
    meta = _create(rows, "importacao", nome_arquivo=payload.nome_arquivo)
    settings = read_settings()
    has_stock = any("estoque" in item or "a_receber" in item for item in positions.values())
    known = all(product in settings["posicoes"] for product in order)
    _write_positions(positions, demo=settings["posicoes_demo"] and known and has_stock is False)
    return meta, _missing_stock_warnings(meta)


# ---------- Fechar mês ----------


def next_period(value: str) -> str:
    return period(pd.Timestamp(f"{value}-01") + pd.DateOffset(months=1))


def close_month(dataset_id: str, payload: CloseMonth) -> tuple[dict, list[str]]:
    """Append month ``U+1`` to a version, creating a ``fechamento`` version (POC-18)."""
    meta = store.load_dataset_meta(dataset_id)
    rows = store.load_rows(dataset_id)
    target = next_period(meta["periodo_fim"])
    labels = {item["produto"]: item["label"] for item in meta["produtos"]}
    items = {item.produto: item for item in payload.itens}
    problems = [f"produto desconhecido: {product}" for product in items if product not in labels]
    for product, label in labels.items():
        item = items.get(product)
        sales = None if item is None else item.vendas
        problem = _quantity_problem(f"{label} {target}", sales)
        if problem is not None:
            problems.append(problem)
    for item in payload.itens:
        for field in ("estoque", "a_receber"):
            value = getattr(item, field)
            if value is not None and value < 0:
                problems.append(f"{labels.get(item.produto, item.produto)}: {field} negativo")
    if len(problems) > 0:
        raise _rejected(problems)
    added = pd.DataFrame(
        [
            {
                "produto": product,
                "produto_label": label,
                "periodo": target,
                "unidades": items[product].vendas,
            }
            for product, label in labels.items()
        ]
    )
    combined = pd.concat([rows, added], ignore_index=True)
    combined["ordem"] = combined["produto"].map(list(labels).index)
    combined = combined.sort_values(["ordem", "periodo"]).drop(columns="ordem")
    _check_history(combined)
    new_meta = _create(combined, "fechamento", pai_id=dataset_id)
    positions = {
        item.produto: {
            field: getattr(item, field)
            for field in ("estoque", "a_receber")
            if getattr(item, field) is not None
        }
        for item in payload.itens
    }
    positions = {product: values for product, values in positions.items() if len(values) > 0}
    if len(positions) > 0:
        _write_positions(positions, demo=False)
    return new_meta, _missing_stock_warnings(new_meta)


# ---------- Edição da grade ----------


def apply_edits(dataset_id: str, payload: DatasetEdits) -> tuple[dict, list[str]]:
    """Create an ``edicao`` version with the changed cells (POC-35)."""
    meta = store.load_dataset_meta(dataset_id)
    rows = store.load_rows(dataset_id)
    labels = {item["produto"]: item["label"] for item in meta["produtos"]}
    index = {(row.produto, row.periodo): position for position, row in enumerate(rows.itertuples())}
    problems: list[str] = []
    changes: dict[int, float] = {}
    for cell in payload.celulas:
        key = (cell.produto, cell.periodo)
        where = f"{labels.get(cell.produto, cell.produto)} {cell.periodo}"
        if key not in index:
            problems.append(f"{where}: célula inexistente na versão")
            continue
        problem = _quantity_problem(where, cell.unidades)
        if problem is not None:
            problems.append(problem)
            continue
        if float(rows.iloc[index[key]]["unidades"]) == cell.unidades:
            continue
        changes[index[key]] = float(cell.unidades)
    if len(problems) > 0:
        raise _rejected(problems)
    if len(changes) == 0:
        raise ApiError(422, "sem_alteracoes", "Nenhuma alteração")
    edited = rows.copy()
    for position, value in changes.items():
        edited.iloc[position, edited.columns.get_loc("unidades")] = value
    new_meta = _create(edited, "edicao", pai_id=dataset_id)
    return new_meta, [f"{len(changes)} célula(s) alterada(s)"]


# ---------- Diferença entre versões ----------


def diff(base_id: str, target_id: str) -> dict:
    """Months added and cells changed from version ``base`` to version ``target`` (POC-22)."""
    base = store.load_rows(base_id).set_index(["produto", "periodo"])["unidades"]
    target = store.load_rows(target_id).set_index(["produto", "periodo"])["unidades"]
    base_periods = set(base.index.get_level_values("periodo"))
    added = sorted(set(target.index.get_level_values("periodo")) - base_periods)
    shared = base.index.intersection(target.index)
    changed = int((base.loc[shared] != target.loc[shared]).sum())
    return {"meses_adicionados": added, "celulas_alteradas": changed}


def dataset_read(dataset_id: str) -> dict:
    meta = store.load_dataset_meta(dataset_id)
    rows = store.load_rows(dataset_id)
    return {**meta, "linhas": rows.to_dict("records")}
