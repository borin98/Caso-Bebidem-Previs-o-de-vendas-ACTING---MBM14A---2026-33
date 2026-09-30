"""Contratos da API: modelos Pydantic de entrada e saída e o erro de negócio."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

Origin = Literal["caso", "importacao", "fechamento", "edicao"]
RunStatus = Literal["na_fila", "executando", "concluido", "falhou"]
ServiceLevel = Literal["0.90", "0.95", "0.975", "0.99"]
Family = Literal["ml", "classica", "series_temporais"]
Situation = Literal["ruptura", "comprar", "adequado", "excesso"]
Period = Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
HorizonYears = Annotated[int, Field(ge=1, le=3)]
NonNegative = Annotated[float, Field(ge=0, le=1_000_000_000)]

MAX_IMPORT_ROWS = 50_000


class ApiError(Exception):
    """Erro de negócio convertido no envelope ``{"erro": {...}}`` pelo handler da API."""

    def __init__(
        self, status: int, codigo: str, mensagem: str, detalhes: list[str] | None = None
    ) -> None:
        super().__init__(mensagem)
        self.status = status
        self.codigo = codigo
        self.mensagem = mensagem
        self.detalhes = detalhes or []


# ---------- Saída ----------


class ErrorBody(BaseModel):
    codigo: str
    mensagem: str
    detalhes: list[str]


class ErrorRead(BaseModel):
    erro: ErrorBody


class Health(BaseModel):
    status: Literal["ok"]


class Point(BaseModel):
    periodo: str
    valor: float


class ProductRef(BaseModel):
    produto: str
    label: str


class DatasetMeta(BaseModel):
    id: str
    criado_em: str
    origem: Origin
    pai_id: str | None
    nome_arquivo: str | None
    produtos: list[ProductRef]
    periodo_inicio: str
    periodo_fim: str
    n_meses: int


class DatasetRow(BaseModel):
    produto: str
    produto_label: str
    periodo: str
    unidades: float


class DatasetRead(DatasetMeta):
    linhas: list[DatasetRow]


class RunMeta(BaseModel):
    id: str
    dataset_id: str
    status: RunStatus
    horizon_years: int
    seed: int
    criado_em: str
    iniciado_em: str | None
    finalizado_em: str | None
    duracao_s: float | None
    erro: str | None


class Window(BaseModel):
    treino_fim: str
    holdout_inicio: str
    holdout_fim: str


class ModelResult(BaseModel):
    modelo: str
    label: str
    familia: Family
    aplicavel: bool
    motivo: str | None
    mad: float | None
    mse: float | None
    rmse: float | None
    mape: float | None
    mpe: float | None
    n_zeros: int
    rank: int | None
    vencedor: bool
    holdout_previsto: list[Point]
    previsao: list[Point]


class ProductResult(BaseModel):
    produto: str
    label: str
    janela: Window
    observado: list[Point]
    vencedor: str
    modelos: list[ModelResult]


class RunResult(BaseModel):
    ultimo_observado: str
    horizon_years: int
    avisos: list[str]
    produtos: list[ProductResult]


class RunRead(RunMeta):
    ativo: bool
    dataset: DatasetMeta
    vencedores: dict[str, str]
    resultado: RunResult | None = None


class ImportResult(BaseModel):
    dataset: DatasetMeta
    run: RunMeta | None
    avisos: list[str]


class Parameters(BaseModel):
    horizonte_meses: Annotated[int, Field(ge=1, le=24)] = 3
    lead_time_padrao: Annotated[float, Field(ge=0, le=12)] = 1.0
    nivel_servico: ServiceLevel = "0.95"
    multiplo_padrao: Annotated[int, Field(ge=1, le=1_000_000_000)] = 1

    @field_validator("lead_time_padrao")
    @classmethod
    def lead_time_step(cls, value: float) -> float:
        if (value * 2) % 1 != 0:
            raise ValueError("lead time padrão deve variar em passos de 0,5")
        return value


class Position(BaseModel):
    estoque: NonNegative | None = None
    a_receber: NonNegative | None = None
    lead_time: Annotated[float, Field(ge=0, le=12)] | None = None
    multiplo: Annotated[float, Field(ge=1, le=1_000_000_000)] | None = None
    capacidade: NonNegative | None = None


class WorkspaceSettings(BaseModel):
    parametros: Parameters
    posicoes: dict[str, Position]
    posicoes_demo: bool
    escolhas_manuais: dict[str, dict[str, str]]


class KPIs(BaseModel):
    produtos: int
    unidades_previstas_horizonte: float
    produtos_ruptura: int
    unidades_comprar: float
    produtos_comprar: int
    acuracia_media: float | None


class ForecastPoint(Point):
    faixa_min: float
    faixa_max: float


class ProjectionRow(BaseModel):
    periodo: str
    inicial: float
    venda_prevista: float
    final: float


class ProductPlan(BaseModel):
    produto: str
    label: str
    modelo_em_uso: str
    modelo_label: str
    escolha_manual: bool
    mape: float | None
    mad: float | None
    rmse: float
    acuracia: float | None
    observado: list[Point]
    holdout_previsto: list[Point]
    previsao: list[ForecastPoint]
    lead_time: float
    multiplo: float
    estoque: float | None
    a_receber: float | None
    disponivel: float
    estoque_informado: bool
    demanda_horizonte: float
    estoque_seguranca: float
    necessidade: float
    projecao: list[ProjectionRow]
    cobertura_meses: float
    cobertura_texto: str
    comprar_ate_texto: str
    situacao: Situation
    capacidade: float | None
    excede_capacidade: bool | None


class PlanRead(BaseModel):
    run_id: str
    ultimo_observado: str
    horizon_years: int
    horizonte_max: int
    parametros: Parameters
    avisos: list[str]
    posicoes_demo: bool
    kpis: KPIs
    produtos: list[ProductPlan]


class ActiveOverview(BaseModel):
    run_id: str
    concluido_em: str
    periodo_inicio: str
    periodo_fim: str
    meses_historico: int
    n_produtos: int
    n_modelos: int
    acuracia_media: float | None
    holdout_inicio: str
    holdout_fim: str


class OverviewRead(BaseModel):
    ativo: ActiveOverview | None
    treino_em_andamento: RunMeta | None


class CompareProduct(BaseModel):
    produto: str
    label: str
    vencedor_base: str
    vencedor_alvo: str
    mape_base: float | None
    mape_alvo: float | None
    delta_mape_pp: float | None
    soma12_base: float
    soma12_alvo: float
    delta_soma12_pct: float | None
    periodo12_base: tuple[str, str]
    periodo12_alvo: tuple[str, str]
    holdout_base: tuple[str, str]
    holdout_alvo: tuple[str, str]


class CompareData(BaseModel):
    meses_adicionados: list[str]
    celulas_alteradas: int


class CompareRead(BaseModel):
    base: RunMeta
    alvo: RunMeta
    produtos: list[CompareProduct]
    dados: CompareData


# ---------- Entrada ----------


class ImportRow(BaseModel):
    produto: Annotated[str, Field(max_length=200)]
    periodo: str
    quantidade: float | None
    estoque: float | None = None
    a_receber: float | None = None
    lead_time: float | None = None
    multiplo: float | None = None


class DatasetImport(BaseModel):
    nome_arquivo: Annotated[str, Field(max_length=255)] | None = None
    linhas: Annotated[list[ImportRow], Field(min_length=1, max_length=MAX_IMPORT_ROWS)]
    iniciar_treino: bool = True
    horizon_years: HorizonYears = 2


class CaseLoad(BaseModel):
    iniciar_treino: bool = True
    horizon_years: HorizonYears = 2


class CloseMonthItem(BaseModel):
    produto: str
    vendas: float | None
    estoque: float | None = None
    a_receber: float | None = None


class CloseMonth(BaseModel):
    itens: Annotated[list[CloseMonthItem], Field(min_length=1)]
    iniciar_treino: bool = True
    horizon_years: HorizonYears = 2


class CellEdit(BaseModel):
    produto: str
    periodo: Period
    unidades: float | None


class DatasetEdits(BaseModel):
    celulas: list[CellEdit]


class RunCreate(BaseModel):
    dataset_id: str
    horizon_years: HorizonYears = 2


class ModelChoice(BaseModel):
    produto: str
    modelo: str | None


class SettingsUpdate(BaseModel):
    parametros: Parameters | None = None
    posicoes: dict[str, Position] | None = None
