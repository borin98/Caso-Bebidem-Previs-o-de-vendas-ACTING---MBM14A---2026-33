"""Plano de reposição do treino ativo, overview da landing, configurações e escolha manual."""

from __future__ import annotations

from . import datasets, store, training
from .engine import CATALOG_BY_MODEL, MODEL_CATALOG
from .replenishment import STATUS_ORDER, accuracy, plan_product
from .schemas import ApiError, ModelChoice, SettingsUpdate

NO_ACTIVE_MESSAGE = "Treinamento inicial em andamento"
MAX_COVERAGE_HORIZON = 24


def _mean(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if len(present) == 0:
        return None
    return sum(present) / len(present)


def _active() -> tuple[str, dict]:
    run_id = store.active_run_id()
    if run_id is None:
        raise ApiError(404, "sem_treino_ativo", NO_ACTIVE_MESSAGE)
    return run_id, store.load_result(run_id)


def _model_in_use(product: dict, choice: str | None) -> tuple[dict, bool]:
    """Manual choice when it names an applicable model other than the winner (POC-36)."""
    by_model = {model["modelo"]: model for model in product["modelos"]}
    winner = by_model[product["vencedor"]]
    if choice is None:
        return winner, False
    chosen = by_model.get(choice)
    if chosen is None or chosen["aplicavel"] is False:
        return winner, False
    return chosen, choice != product["vencedor"]


def _with_band(points: list[dict], mad: float) -> list[dict]:
    return [
        {**point, "faixa_min": max(0.0, point["valor"] - mad), "faixa_max": point["valor"] + mad}
        for point in points
    ]


def _product_plan(product: dict, choice: str | None, position: dict, params: dict) -> dict:
    model, manual = _model_in_use(product, choice)
    plan = plan_product(model["previsao"], model["rmse"], position, params)
    return {
        "produto": product["produto"],
        "label": product["label"],
        "modelo_em_uso": model["modelo"],
        "modelo_label": model["label"],
        "escolha_manual": manual,
        "mape": model["mape"],
        "mad": model["mad"],
        "rmse": model["rmse"],
        "acuracia": accuracy(model["mape"]),
        "observado": product["observado"],
        "holdout_previsto": model["holdout_previsto"],
        "previsao": _with_band(model["previsao"], model["mad"]),
        "estoque": position.get("estoque"),
        "a_receber": position.get("a_receber"),
        **plan,
    }


def horizon_limit(horizon_years: int) -> int:
    """Coverage horizon is capped at ``min(24, 12 × h)`` (POC-39)."""
    return min(MAX_COVERAGE_HORIZON, 12 * horizon_years)


def plan() -> dict:
    """Replenishment plan, KPIs and ordering for the active run (POC-12/13, 25–27)."""
    run_id, result = _active()
    settings = datasets.read_settings()
    limit = horizon_limit(result["horizon_years"])
    params = {
        **settings["parametros"],
        "horizonte_meses": min(settings["parametros"]["horizonte_meses"], limit),
    }
    choices = settings["escolhas_manuais"].get(run_id, {})
    products = [
        _product_plan(
            product,
            choices.get(product["produto"]),
            settings["posicoes"].get(product["produto"], datasets.EMPTY_POSITION),
            params,
        )
        for product in result["produtos"]
    ]
    products.sort(key=lambda row: (STATUS_ORDER.index(row["situacao"]), -row["necessidade"]))
    missing_stock = [
        f"{row['label']}: sem estoque informado, considerado zero"
        for row in products
        if row["estoque_informado"] is False
    ]
    return {
        "run_id": run_id,
        "ultimo_observado": result["ultimo_observado"],
        "horizon_years": result["horizon_years"],
        "horizonte_max": limit,
        "parametros": params,
        "avisos": [*result["avisos"], *missing_stock],
        "posicoes_demo": settings["posicoes_demo"],
        "kpis": {
            "produtos": len(products),
            "unidades_previstas_horizonte": sum(row["demanda_horizonte"] for row in products),
            "produtos_ruptura": sum(row["situacao"] == "ruptura" for row in products),
            "unidades_comprar": sum(row["necessidade"] for row in products),
            "produtos_comprar": sum(row["necessidade"] > 0 for row in products),
            "acuracia_media": _mean([row["acuracia"] for row in products]),
        },
        "produtos": products,
    }


def overview() -> dict:
    """Landing numbers, all read from the active run (POC-23)."""
    in_progress = training.open_run()
    run_id = store.active_run_id()
    if run_id is None:
        return {"ativo": None, "treino_em_andamento": in_progress}
    run = store.load_run(run_id)
    result = store.load_result(run_id)
    dataset = store.load_dataset_meta(run["dataset_id"])
    winners = [
        next(model for model in product["modelos"] if model["vencedor"])
        for product in result["produtos"]
    ]
    window = result["produtos"][0]["janela"]
    return {
        "ativo": {
            "run_id": run_id,
            "concluido_em": run["finalizado_em"],
            "periodo_inicio": dataset["periodo_inicio"],
            "periodo_fim": dataset["periodo_fim"],
            "meses_historico": dataset["n_meses"],
            "n_produtos": len(result["produtos"]),
            "n_modelos": len(MODEL_CATALOG),
            "acuracia_media": _mean([accuracy(model["mape"]) for model in winners]),
            "holdout_inicio": window["holdout_inicio"],
            "holdout_fim": window["holdout_fim"],
        },
        "treino_em_andamento": in_progress,
    }


def _horizon_problem(update: SettingsUpdate) -> str | None:
    """Coverage horizon above ``min(24, 12 × h)`` of the active run is refused (POC-39)."""
    if update.parametros is None:
        return None
    run_id = store.active_run_id()
    if run_id is None:
        return None
    limit = horizon_limit(store.load_result(run_id)["horizon_years"])
    if update.parametros.horizonte_meses <= limit:
        return None
    return f"parametros.horizonte_meses: deve ser menor ou igual a {limit}"


def save_settings(update: SettingsUpdate) -> dict:
    """Persist panel parameters and/or stock positions (POC-26, POC-30, POC-39)."""
    problem = _horizon_problem(update)
    if problem is not None:
        raise ApiError(422, "validacao_invalida", "Dados inválidos", [problem])
    settings = datasets.read_settings()
    if update.parametros is not None:
        settings["parametros"] = update.parametros.model_dump()
    if update.posicoes is not None:
        positions = {product: value.model_dump() for product, value in update.posicoes.items()}
        settings["posicoes"] = {**settings["posicoes"], **positions}
        settings["posicoes_demo"] = False
    store.save_settings(settings)
    return settings


def set_model_choice(run_id: str, choice: ModelChoice) -> dict:
    """Manual model per product, valid only for the active run it was made on (POC-36)."""
    if store.active_run_id() != run_id:
        raise ApiError(409, "treino_nao_ativo", "A escolha manual vale só para o treino ativo")
    result = store.load_result(run_id)
    products = {product["produto"]: product for product in result["produtos"]}
    product = products.get(choice.produto)
    if product is None:
        raise ApiError(404, "nao_encontrado", f"Produto não encontrado: {choice.produto}")
    settings = datasets.read_settings()
    run_choices = settings["escolhas_manuais"].setdefault(run_id, {})
    if choice.modelo is None:
        run_choices.pop(choice.produto, None)
        store.save_settings(settings)
        return plan()
    model = next((item for item in product["modelos"] if item["modelo"] == choice.modelo), None)
    if model is None:
        raise ApiError(422, "modelo_invalido", f"Modelo desconhecido: {choice.modelo}")
    if model["aplicavel"] is False:
        label = CATALOG_BY_MODEL[choice.modelo]["label"]
        raise ApiError(422, "modelo_nao_aplicavel", f"{label} não é aplicável a este produto")
    run_choices[choice.produto] = choice.modelo
    store.save_settings(settings)
    return plan()
