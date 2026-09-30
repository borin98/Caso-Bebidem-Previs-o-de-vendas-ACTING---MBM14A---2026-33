"""Armazenamento em arquivos: única camada que toca o disco (escrita atômica)."""

from __future__ import annotations

import json
import os
import secrets
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from .schemas import ApiError

ROW_COLUMNS = ["produto", "produto_label", "periodo", "unidades"]


def data_dir() -> Path:
    return Path(os.environ.get("POC_DATA_DIR", "./var"))


def datasets_dir() -> Path:
    return data_dir() / "datasets"


def runs_dir() -> Path:
    return data_dir() / "runs"


def init() -> None:
    datasets_dir().mkdir(parents=True, exist_ok=True)
    runs_dir().mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    return f"{prefix}-{stamp}-{secrets.token_hex(2)}"


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(content)
    os.replace(temporary, path)


def write_json(path: Path, data: object) -> None:
    _atomic_write(path, json.dumps(data, ensure_ascii=False, indent=1))


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ApiError(
            500,
            "armazenamento_invalido",
            f"Arquivo de armazenamento ausente ou corrompido: {path.name}",
        ) from error


def _read_optional(path: Path) -> dict | None:
    if path.exists() is False:
        return None
    return read_json(path)


def _not_found(message: str) -> ApiError:
    return ApiError(404, "nao_encontrado", message)


# ---------- Versões de dados ----------


def has_datasets() -> bool:
    return any(datasets_dir().glob("*/meta.json"))


def save_dataset(meta: dict, rows: pd.DataFrame) -> None:
    folder = datasets_dir() / meta["id"]
    _atomic_write(folder / "rows.csv", rows[ROW_COLUMNS].to_csv(index=False, lineterminator="\n"))
    write_json(folder / "meta.json", meta)


def load_dataset_meta(dataset_id: str) -> dict:
    path = datasets_dir() / dataset_id / "meta.json"
    if path.exists() is False:
        raise _not_found(f"Versão de dados não encontrada: {dataset_id}")
    return read_json(path)


def load_rows(dataset_id: str) -> pd.DataFrame:
    load_dataset_meta(dataset_id)
    return read_rows(rows_path(dataset_id))


def rows_path(dataset_id: str) -> Path:
    return datasets_dir() / dataset_id / "rows.csv"


def read_rows(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, dtype={"produto": str, "produto_label": str, "periodo": str})
    except (OSError, ValueError) as error:
        raise ApiError(
            500, "armazenamento_invalido", f"Linhas da versão ausentes ou corrompidas: {path}"
        ) from error


def list_datasets() -> list[dict]:
    metas = [read_json(path) for path in datasets_dir().glob("*/meta.json")]
    return sorted(metas, key=lambda meta: meta["id"], reverse=True)


# ---------- Treinos ----------


def run_folder(run_id: str) -> Path:
    return runs_dir() / run_id


def save_run(meta: dict) -> None:
    write_json(run_folder(meta["id"]) / "run.json", meta)


def load_run(run_id: str) -> dict:
    path = run_folder(run_id) / "run.json"
    if path.exists() is False:
        raise _not_found(f"Treino não encontrado: {run_id}")
    return read_json(path)


def list_runs() -> list[dict]:
    metas = [read_json(path) for path in runs_dir().glob("*/run.json")]
    return sorted(metas, key=lambda meta: meta["id"], reverse=True)


def result_path(run_id: str) -> Path:
    return run_folder(run_id) / "result.json"


def error_path(run_id: str) -> Path:
    return run_folder(run_id) / "error.json"


def load_result(run_id: str) -> dict:
    return read_json(result_path(run_id))


# ---------- Estado do workspace ----------


def active_run_id() -> str | None:
    state = _read_optional(data_dir() / "active.json")
    if state is None:
        return None
    return state.get("run_id")


def set_active(run_id: str) -> None:
    write_json(data_dir() / "active.json", {"run_id": run_id, "ativado_em": now_iso()})


def load_settings() -> dict | None:
    return _read_optional(data_dir() / "settings.json")


def save_settings(settings: dict) -> None:
    write_json(data_dir() / "settings.json", settings)
