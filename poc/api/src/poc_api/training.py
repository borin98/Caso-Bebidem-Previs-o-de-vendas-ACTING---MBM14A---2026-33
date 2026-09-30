"""Treinos: processo ``spawn`` com limite de tempo, ciclo de vida, ativação e comparativo."""

from __future__ import annotations

import json
import logging
import multiprocessing
import os
import signal
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from bebibem.config import SEED
from bebibem.io_data import InputError

from . import datasets, store
from .engine import CATALOG_BY_MODEL, evaluate_and_forecast, tidy_frame
from .schemas import ApiError

LOGGER = logging.getLogger("poc_api.training")
CONTEXT = multiprocessing.get_context("spawn")
OPEN_STATUSES = ("na_fila", "executando")
BUSY_MESSAGE = "Já existe um treinamento em andamento"
RESTART_MESSAGE = "Interrompido pelo reinício do serviço"
_LOCK = threading.Lock()
_STOPPING = threading.Event()
_RUNNING: set[multiprocessing.process.BaseProcess] = set()


def stop() -> None:
    """Service shutdown: kill the training child and leave its run open, so the restart
    recovery marks it ``falhou`` with the restart message (POC-20)."""
    _STOPPING.set()
    for process in list(_RUNNING):
        process.kill()


def timeout_seconds() -> int:
    return int(os.environ.get("POC_TRAINING_TIMEOUT_S", "60"))


def default_horizon_years() -> int:
    return int(os.environ.get("POC_HORIZON_YEARS", "2"))


def _log(meta: dict) -> None:
    record = {
        "evento": "treino",
        "run_id": meta["id"],
        "dataset_id": meta["dataset_id"],
        "status": meta["status"],
        "duracao_s": meta["duracao_s"],
    }
    if meta["erro"] is not None:
        record["erro"] = meta["erro"]
    LOGGER.info(json.dumps(record, ensure_ascii=False))


def _save(meta: dict) -> None:
    store.save_run(meta)
    _log(meta)


def open_run() -> dict | None:
    return next((run for run in store.list_runs() if run["status"] in OPEN_STATUSES), None)


@contextmanager
def exclusive() -> Iterator[None]:
    """Serialize 'check idle → create version → start' so two requests cannot both pass."""
    with _LOCK:
        yield


def ensure_idle() -> None:
    if open_run() is not None:
        raise ApiError(409, "treino_em_andamento", BUSY_MESSAGE)


def run_job(
    rows_csv: str, result_file: str, error_file: str, horizon_years: int, seed: int
) -> None:
    """Child-process entry point: run the engine and write ``result.json`` or ``error.json``."""
    # Ctrl+C / SIGTERM sent to the whole process group must stop the service first; the child
    # is killed (SIGKILL) by the watcher timeout or by `stop()`, never by the group signal.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    try:
        frame = tidy_frame(store.read_rows(Path(rows_csv)))
        result = evaluate_and_forecast(frame, horizon_years=horizon_years, seed=seed)
    except InputError as error:
        store.write_json(Path(error_file), {"mensagem": str(error)})
        return
    except Exception as error:  # noqa: BLE001 — any engine failure must surface as run `falhou`
        store.write_json(Path(error_file), {"mensagem": f"Erro no motor de previsão: {error}"})
        return
    store.write_json(Path(result_file), result)


def _finish(meta: dict, status: str, elapsed: float, error: str | None) -> dict:
    finished = {
        **meta,
        "status": status,
        "finalizado_em": store.now_iso(),
        "duracao_s": elapsed,
        "erro": error,
    }
    _save(finished)
    return finished


def _failure_message(meta: dict, exit_code: int | None) -> str:
    error_file = store.error_path(meta["id"])
    if error_file.exists():
        return str(store.read_json(error_file)["mensagem"])
    return f"Processo de treino encerrou sem resultado (código {exit_code})"


def _watch(meta: dict) -> None:
    limit = timeout_seconds()
    process = CONTEXT.Process(
        target=run_job,
        args=(
            str(store.rows_path(meta["dataset_id"])),
            str(store.result_path(meta["id"])),
            str(store.error_path(meta["id"])),
            meta["horizon_years"],
            meta["seed"],
        ),
        daemon=True,
    )
    running = {**meta, "status": "executando", "iniciado_em": store.now_iso()}
    _save(running)
    started = time.monotonic()
    process.start()
    _RUNNING.add(process)
    process.join(limit)
    elapsed = round(time.monotonic() - started, 1)
    if _STOPPING.is_set():
        return
    if process.is_alive():
        process.kill()
        process.join(5)
        _RUNNING.discard(process)
        _finish(running, "falhou", elapsed, f"Tempo limite de {limit} s excedido")
        return
    _RUNNING.discard(process)
    if store.result_path(meta["id"]).exists():
        store.set_active(meta["id"])
        _finish(running, "concluido", elapsed, None)
        return
    _finish(running, "falhou", elapsed, _failure_message(meta, process.exitcode))


def start(dataset_id: str, horizon_years: int) -> dict:
    """Queue a run (``na_fila``) and hand it to a watcher thread with the hard time limit."""
    store.load_dataset_meta(dataset_id)
    meta = {
        "id": store.new_id("run"),
        "dataset_id": dataset_id,
        "status": "na_fila",
        "horizon_years": horizon_years,
        "seed": SEED,
        "criado_em": store.now_iso(),
        "iniciado_em": None,
        "finalizado_em": None,
        "duracao_s": None,
        "erro": None,
    }
    _save(meta)
    threading.Thread(target=_watch, args=(meta,), daemon=True).start()
    return meta


def recover_interrupted() -> None:
    """Runs left open by a restart become ``falhou`` (POC-20); the active run is kept."""
    for run in store.list_runs():
        if run["status"] not in OPEN_STATUSES:
            continue
        _finish(run, "falhou", run["duracao_s"], RESTART_MESSAGE)


def winners(run: dict) -> dict[str, str]:
    """Winner model label per product label, ready for the versions list (POC-21)."""
    if run["status"] != "concluido":
        return {}
    result = store.load_result(run["id"])
    return {
        product["label"]: CATALOG_BY_MODEL[product["vencedor"]]["label"]
        for product in result["produtos"]
    }


def run_read(run: dict, with_result: bool = False) -> dict:
    read = {
        **run,
        "ativo": store.active_run_id() == run["id"],
        "dataset": store.load_dataset_meta(run["dataset_id"]),
        "vencedores": winners(run),
    }
    if with_result and run["status"] == "concluido":
        read["resultado"] = store.load_result(run["id"])
    return read


def activate(run_id: str) -> dict:
    run = store.load_run(run_id)
    if run["status"] != "concluido":
        raise ApiError(409, "treino_nao_concluido", "Só treinos concluídos podem ser ativados")
    store.set_active(run_id)
    return run


def _completed_result(run_id: str) -> tuple[dict, dict]:
    run = store.load_run(run_id)
    if run["status"] != "concluido":
        raise ApiError(409, "treino_nao_concluido", f"Treino {run_id} não está concluído")
    return run, store.load_result(run_id)


def _winner_summary(product: dict) -> dict:
    winner = next(model for model in product["modelos"] if model["vencedor"])
    first12 = winner["previsao"][:12]
    return {
        "modelo": CATALOG_BY_MODEL[winner["modelo"]]["label"],
        "mape": winner["mape"],
        "soma12": sum(point["valor"] for point in first12),
        "periodo12": (first12[0]["periodo"], first12[-1]["periodo"]),
        "holdout": (product["janela"]["holdout_inicio"], product["janela"]["holdout_fim"]),
    }


def _delta(target: float | None, base: float | None) -> float | None:
    if target is None or base is None:
        return None
    return target - base


def _delta_pct(target: float, base: float) -> float | None:
    if base == 0:
        return None
    return (target - base) / base * 100


def compare(base_id: str, target_id: str) -> dict:
    """Before × after comparison of two completed runs (POC-22)."""
    if base_id == target_id:
        raise ApiError(422, "comparacao_invalida", "Escolha dois treinos diferentes para comparar")
    base_run, base_result = _completed_result(base_id)
    target_run, target_result = _completed_result(target_id)
    base_products = {product["produto"]: product for product in base_result["produtos"]}
    products = []
    for product in target_result["produtos"]:
        if product["produto"] not in base_products:
            continue
        before = _winner_summary(base_products[product["produto"]])
        after = _winner_summary(product)
        products.append(
            {
                "produto": product["produto"],
                "label": product["label"],
                "vencedor_base": before["modelo"],
                "vencedor_alvo": after["modelo"],
                "mape_base": before["mape"],
                "mape_alvo": after["mape"],
                "delta_mape_pp": _delta(after["mape"], before["mape"]),
                "soma12_base": before["soma12"],
                "soma12_alvo": after["soma12"],
                "delta_soma12_pct": _delta_pct(after["soma12"], before["soma12"]),
                "periodo12_base": before["periodo12"],
                "periodo12_alvo": after["periodo12"],
                "holdout_base": before["holdout"],
                "holdout_alvo": after["holdout"],
            }
        )
    return {
        "base": base_run,
        "alvo": target_run,
        "produtos": products,
        "dados": datasets.diff(base_run["dataset_id"], target_run["dataset_id"]),
    }
