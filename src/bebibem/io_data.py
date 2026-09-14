"""CSV ingestion, normalization, and validation for demand histories."""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import pandas as pd

LOGGER = logging.getLogger(__name__)


class InputError(ValueError):
    """Raised when an input file or option violates the public contract."""


MONTHS = {
    "jan": 1,
    "janeiro": 1,
    "fev": 2,
    "fevereiro": 2,
    "mar": 3,
    "marco": 3,
    "março": 3,
    "abr": 4,
    "abril": 4,
    "mai": 5,
    "maio": 5,
    "jun": 6,
    "junho": 6,
    "jul": 7,
    "julho": 7,
    "ago": 8,
    "agosto": 8,
    "set": 9,
    "setembro": 9,
    "out": 10,
    "outubro": 10,
    "nov": 11,
    "novembro": 11,
    "dez": 12,
    "dezembro": 12,
}

TIDY_COLUMNS = ["produto", "produto_label", "ano", "mes", "data", "unidades"]
REQUIRED_LONG = ["produto", "ano", "mes", "unidades"]
REQUIRED_WIDE = ["produto", "ano", *MONTHS.keys()]


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def normalize_product(name: object) -> str:
    """Return a stable ASCII slug while retaining the source label separately."""
    text = str(name).strip()
    ascii_text = _strip_accents(text).lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_text).strip("_")
    if slug == "":
        raise InputError(f"produto inválido: {name!r}")
    return slug


def _normalize_columns(columns: Sequence[object]) -> list[str]:
    return [str(column).strip().lower() for column in columns]


def detect_layout(columns: Sequence[str]) -> Literal["wide", "long"]:
    """Detect wide or long layout from normalized column names."""
    names = set(_normalize_columns(columns))
    long_markers = {"mes", "unidades"}
    wide_markers = set(MONTHS)
    if names.intersection(long_markers):
        return "long"
    if names.intersection(wide_markers):
        return "wide"
    raise InputError(
        "layout irreconhecível: esperadas colunas long "
        f"{REQUIRED_LONG} ou wide {REQUIRED_WIDE}; encontradas {sorted(names)}"
    )


def _offender(product: object, year: object, month: object) -> str:
    return f"{normalize_product(product)}/{year}/{month}"


def _month_number(value: object, product: object, year: object) -> int:
    numeric = value
    if isinstance(value, str):
        text = _strip_accents(value.strip().lower())
        if text in MONTHS:
            return MONTHS[text]
        try:
            numeric = float(text)
        except ValueError as error:
            raise InputError(f"mês inválido em {_offender(product, year, value)}") from error
    if pd.isna(numeric):
        raise InputError(f"mês nulo em {_offender(product, year, value)}")
    try:
        month = int(numeric)
    except (TypeError, ValueError) as error:
        raise InputError(f"mês inválido em {_offender(product, year, value)}") from error
    if float(numeric) != month or month < 1 or month > 12:
        raise InputError(f"mês inválido em {_offender(product, year, value)}")
    return month


def _normalize_year(value: object, product: object, month: object) -> int:
    if pd.isna(value):
        raise InputError(f"ano nulo em {_offender(product, value, month)}")
    try:
        year = int(value)
    except (TypeError, ValueError) as error:
        raise InputError(f"ano inválido em {_offender(product, value, month)}") from error
    if float(value) != year or year < 1900:
        raise InputError(f"ano inválido em {_offender(product, value, month)}")
    return year


def _validate_units(frame: pd.DataFrame, allow_missing: bool) -> pd.Series:
    values = pd.to_numeric(frame["unidades"], errors="coerce")
    for index, (raw, numeric) in enumerate(zip(frame["unidades"], values)):
        product = frame.iloc[index]["produto"]
        year = frame.iloc[index]["ano"]
        month = frame.iloc[index]["mes"]
        location = _offender(product, year, month)
        if pd.isna(raw) and allow_missing:
            continue
        if pd.isna(raw):
            raise InputError(f"valor nulo em {location}")
        if pd.isna(numeric):
            raise InputError(f"valor não numérico em {location}: {raw!r}")
        if numeric < 0:
            raise InputError(f"valor negativo em {location}: {raw!r}")
    return values.astype(float)


def validate_frame(frame: pd.DataFrame, allow_missing: bool = False) -> None:
    """Validate a normalized frame and raise actionable ``InputError`` messages."""
    missing = [column for column in ["produto", "ano", "mes", "unidades"] if column not in frame]
    if missing:
        raise InputError(
            f"colunas esperadas {['produto', 'ano', 'mes', 'unidades']}; "
            f"faltantes {missing}; encontradas {list(frame.columns)}"
        )
    duplicate_mask = frame.duplicated(["produto", "ano", "mes"], keep=False)
    if duplicate_mask.any():
        pairs = frame.loc[duplicate_mask, ["produto", "ano", "mes"]].drop_duplicates()
        values = ", ".join(_offender(row.produto, row.ano, row.mes) for row in pairs.itertuples())
        raise InputError(f"pares duplicados: {values}")
    _validate_units(frame, allow_missing=allow_missing)


def _wide_to_tidy(raw: pd.DataFrame) -> pd.DataFrame:
    required = [
        "produto",
        "ano",
        *[
            name
            for name in MONTHS
            if name
            in {"jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"}
        ],
    ]
    missing = [month for month in required[2:] if month not in raw.columns]
    if missing:
        raise InputError(
            f"colunas esperadas wide {required}; faltantes {missing}; "
            f"encontradas {list(raw.columns)}"
        )
    rows = raw.melt(
        id_vars=["produto", "ano"], value_vars=required[2:], var_name="mes", value_name="unidades"
    )
    rows["produto_label"] = rows["produto"].astype(str).str.strip()
    rows["produto"] = rows["produto_label"].map(normalize_product)
    rows["mes"] = rows["mes"].map(MONTHS)
    rows["ano"] = [
        _normalize_year(year, product, month)
        for product, year, month in zip(rows["produto"], rows["ano"], rows["mes"])
    ]
    rows["unidades"] = _validate_units(rows, allow_missing=False)
    validate_frame(rows, allow_missing=False)
    rows["data"] = pd.to_datetime({"year": rows["ano"], "month": rows["mes"], "day": 1})
    return rows[TIDY_COLUMNS]


def _long_to_tidy(raw: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_LONG if column not in raw.columns]
    if missing:
        raise InputError(
            f"colunas esperadas long {REQUIRED_LONG}; faltantes {missing}; "
            f"encontradas {list(raw.columns)}"
        )
    rows = raw.copy()
    rows["produto_label"] = rows["produto"].astype(str).str.strip()
    rows["produto"] = rows["produto_label"].map(normalize_product)
    rows["mes"] = [
        _month_number(month, product, year)
        for product, year, month in zip(rows["produto"], rows["ano"], rows["mes"])
    ]
    rows["ano"] = [
        _normalize_year(year, product, month)
        for product, year, month in zip(rows["produto"], rows["ano"], rows["mes"])
    ]
    validate_frame(rows, allow_missing=False)
    rows["unidades"] = pd.to_numeric(rows["unidades"], errors="raise").astype(float)
    rows["data"] = pd.to_datetime({"year": rows["ano"], "month": rows["mes"], "day": 1})
    return rows[TIDY_COLUMNS]


def fill_missing_months(frame: pd.DataFrame) -> pd.DataFrame:
    """Insert absent dates between each product's first and last observation."""
    complete: list[pd.DataFrame] = []
    for product, group in frame.groupby("produto", sort=False):
        group = group.sort_values("data")
        dates = pd.date_range(group["data"].min(), group["data"].max(), freq="MS")
        known = group.set_index("data")["unidades"]
        values = known.reindex(dates)
        label = group["produto_label"].iloc[0]
        product_frame = pd.DataFrame(
            {
                "produto": product,
                "produto_label": label,
                "ano": dates.year,
                "mes": dates.month,
                "data": dates,
                "unidades": values.to_numpy(dtype=float),
            }
        )
        inserted = len(dates) - len(group)
        if inserted > 0:
            LOGGER.warning("mês ausente: produto=%s, %d linha(s) inserida(s)", label, inserted)
        complete.append(product_frame)
    if len(complete) == 0:
        return frame[TIDY_COLUMNS].copy()
    return pd.concat(complete, ignore_index=True)[TIDY_COLUMNS]


def load_demand(path: Path) -> pd.DataFrame:
    """Load wide or long demand CSV into the tidy internal contract."""
    input_path = Path(path)
    if input_path.exists() is False:
        raise InputError(f"arquivo de entrada não existe: {input_path}")
    try:
        raw = pd.read_csv(input_path)
    except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise InputError(f"não foi possível ler o arquivo {input_path}: {error}") from error
    layout = detect_layout(raw.columns)
    if "produto" not in raw.columns or "ano" not in raw.columns:
        raise InputError(
            f"colunas esperadas incluem produto e ano; encontradas {list(raw.columns)}"
        )
    if layout == "long":
        tidy = _long_to_tidy(raw)
    if layout == "wide":
        tidy = _wide_to_tidy(raw)
    return fill_missing_months(tidy).sort_values(["produto", "data"]).reset_index(drop=True)
