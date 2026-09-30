"""App FastAPI do POC: ciclo de vida, rotas e envelope de erro."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import datasets, planning, store, training
from .schemas import (
    ApiError,
    CaseLoad,
    CloseMonth,
    CompareRead,
    DatasetEdits,
    DatasetImport,
    DatasetMeta,
    DatasetRead,
    Health,
    ImportResult,
    ModelChoice,
    OverviewRead,
    PlanRead,
    RunCreate,
    RunMeta,
    RunRead,
    SettingsUpdate,
    WorkspaceSettings,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")

MAX_DETAILS = 20
VALIDATION_MESSAGES = {
    "missing": "campo obrigatório",
    "less_than_equal": "deve ser menor ou igual a {le}",
    "greater_than_equal": "deve ser maior ou igual a {ge}",
    "int_parsing": "deve ser um número inteiro",
    "int_from_float": "deve ser um número inteiro",
    "float_parsing": "deve ser um número",
    "literal_error": "valor não permitido; use {expected}",
    "string_pattern_mismatch": "formato inválido",
    "too_long": "excede o limite de {max_length} itens",
    "too_short": "precisa de pelo menos {min_length} item(ns)",
    "value_error": "{error}",
}


def limit_details(details: list[str]) -> list[str]:
    """Keep at most 20 problems and summarize the rest as ``… e mais N``."""
    if len(details) <= MAX_DETAILS:
        return details
    return [*details[:MAX_DETAILS], f"… e mais {len(details) - MAX_DETAILS}"]


def _error_response(status: int, codigo: str, mensagem: str, detalhes: list[str]) -> JSONResponse:
    body = {"codigo": codigo, "mensagem": mensagem, "detalhes": limit_details(detalhes)}
    return JSONResponse(status_code=status, content={"erro": body})


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    store.init()
    training.recover_interrupted()
    seeded = datasets.seed()
    if seeded is not None:
        training.start(seeded["id"], training.default_horizon_years())
    yield
    training.stop()


app = FastAPI(title="POC Planejamento de Demanda", lifespan=lifespan)
router = APIRouter(prefix="/api/v1")


@app.exception_handler(ApiError)
async def handle_api_error(_: Request, error: ApiError) -> JSONResponse:
    return _error_response(error.status, error.codigo, error.mensagem, error.detalhes)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    details = [_validation_detail(item) for item in error.errors()]
    return _error_response(422, "validacao_invalida", "Dados inválidos", details)


def _validation_detail(item: dict) -> str:
    field = ".".join(str(part) for part in item["loc"] if part != "body")
    template = VALIDATION_MESSAGES.get(item["type"])
    if template is None:
        return f"{field}: {item['msg']}"
    return f"{field}: {template.format(**item.get('ctx', {}))}"


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(_: Request, error: StarletteHTTPException) -> JSONResponse:
    if error.status_code == 404:
        return _error_response(404, "nao_encontrado", "Recurso não encontrado", [])
    return _error_response(error.status_code, "erro_http", str(error.detail), [])


@router.get("/health")
def health() -> Health:
    return Health(status="ok")


@router.get("/datasets", response_model=list[DatasetMeta])
def list_datasets() -> list[dict]:
    return store.list_datasets()


@router.get("/datasets/{dataset_id}", response_model=DatasetRead)
def read_dataset(dataset_id: str) -> dict:
    return datasets.dataset_read(dataset_id)


def _create_version(
    create: Callable[[], tuple[dict, list[str]]], start_training: bool, horizon_years: int
) -> dict:
    """Create a data version; with training, check idle first and start it (POC-20)."""
    if start_training is False:
        meta, avisos = create()
        return {"dataset": meta, "run": None, "avisos": avisos}
    with training.exclusive():
        training.ensure_idle()
        meta, avisos = create()
        run = training.start(meta["id"], horizon_years)
    return {"dataset": meta, "run": run, "avisos": avisos}


@router.post("/datasets/import", status_code=201, response_model=ImportResult)
def import_dataset(payload: DatasetImport) -> dict:
    return _create_version(
        lambda: datasets.import_rows(payload), payload.iniciar_treino, payload.horizon_years
    )


@router.post("/datasets/case", status_code=201, response_model=ImportResult)
def load_case_dataset(payload: CaseLoad | None = None) -> dict:
    options = payload or CaseLoad()
    return _create_version(datasets.load_case, options.iniciar_treino, options.horizon_years)


@router.post("/datasets/{dataset_id}/close-month", status_code=201, response_model=ImportResult)
def close_month(dataset_id: str, payload: CloseMonth) -> dict:
    return _create_version(
        lambda: datasets.close_month(dataset_id, payload),
        payload.iniciar_treino,
        payload.horizon_years,
    )


@router.post("/datasets/{dataset_id}/edits", status_code=201, response_model=ImportResult)
def edit_dataset(dataset_id: str, payload: DatasetEdits) -> dict:
    return _create_version(lambda: datasets.apply_edits(dataset_id, payload), False, 0)


@router.post("/runs", status_code=202, response_model=RunMeta)
def create_run(payload: RunCreate) -> dict:
    with training.exclusive():
        training.ensure_idle()
        return training.start(payload.dataset_id, payload.horizon_years)


@router.get("/runs", response_model=list[RunRead])
def list_runs() -> list[dict]:
    return [training.run_read(run) for run in store.list_runs()]


@router.get("/runs/compare", response_model=CompareRead)
def compare_runs(base: Annotated[str, Query()], alvo: Annotated[str, Query()]) -> dict:
    return training.compare(base, alvo)


@router.get("/runs/{run_id}", response_model=RunRead)
def read_run(run_id: str) -> dict:
    return training.run_read(store.load_run(run_id), with_result=True)


@router.post("/runs/{run_id}/activate", response_model=RunRead)
def activate_run(run_id: str) -> dict:
    return training.run_read(training.activate(run_id))


@router.put("/runs/{run_id}/model-choice", response_model=PlanRead)
def choose_model(run_id: str, payload: ModelChoice) -> dict:
    return planning.set_model_choice(run_id, payload)


@router.get("/plan", response_model=PlanRead)
def read_plan() -> dict:
    return planning.plan()


@router.get("/overview", response_model=OverviewRead)
def read_overview() -> dict:
    return planning.overview()


@router.get("/settings", response_model=WorkspaceSettings)
def read_settings() -> dict:
    return datasets.read_settings()


@router.put("/settings", response_model=WorkspaceSettings)
def update_settings(payload: SettingsUpdate) -> dict:
    return planning.save_settings(payload)


app.include_router(router)
