"use client";

import {
  type QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

// ---------- Tipos (espelham poc/api/src/poc_api/schemas.py) ----------

export type Origin = "caso" | "importacao" | "fechamento" | "edicao";
export type RunStatus = "na_fila" | "executando" | "concluido" | "falhou";
export type ServiceLevel = "0.90" | "0.95" | "0.975" | "0.99";
export type Family = "ml" | "classica" | "series_temporais";
export type Situation = "ruptura" | "comprar" | "adequado" | "excesso";

export interface Point {
  periodo: string;
  valor: number;
}

export interface DatasetMeta {
  id: string;
  criado_em: string;
  origem: Origin;
  pai_id: string | null;
  nome_arquivo: string | null;
  produtos: { produto: string; label: string }[];
  periodo_inicio: string;
  periodo_fim: string;
  n_meses: number;
}

export interface DatasetRow {
  produto: string;
  produto_label: string;
  periodo: string;
  unidades: number;
}

export interface DatasetRead extends DatasetMeta {
  linhas: DatasetRow[];
}

export interface RunMeta {
  id: string;
  dataset_id: string;
  status: RunStatus;
  horizon_years: number;
  seed: number;
  criado_em: string;
  iniciado_em: string | null;
  finalizado_em: string | null;
  duracao_s: number | null;
  erro: string | null;
}

export interface ModelResult {
  modelo: string;
  label: string;
  familia: Family;
  aplicavel: boolean;
  motivo: string | null;
  mad: number | null;
  mse: number | null;
  rmse: number | null;
  mape: number | null;
  mpe: number | null;
  n_zeros: number;
  rank: number | null;
  vencedor: boolean;
  holdout_previsto: Point[];
  previsao: Point[];
}

export interface ProductResult {
  produto: string;
  label: string;
  janela: { treino_fim: string; holdout_inicio: string; holdout_fim: string };
  observado: Point[];
  vencedor: string;
  modelos: ModelResult[];
}

export interface RunResult {
  ultimo_observado: string;
  horizon_years: number;
  avisos: string[];
  produtos: ProductResult[];
}

export interface RunRead extends RunMeta {
  ativo: boolean;
  dataset: DatasetMeta;
  vencedores: Record<string, string>;
  resultado: RunResult | null;
}

export interface ImportResult {
  dataset: DatasetMeta;
  run: RunMeta | null;
  avisos: string[];
}

export interface Parameters {
  horizonte_meses: number;
  lead_time_padrao: number;
  nivel_servico: ServiceLevel;
  multiplo_padrao: number;
}

export interface Position {
  estoque: number | null;
  a_receber: number | null;
  lead_time: number | null;
  multiplo: number | null;
  capacidade: number | null;
}

export interface WorkspaceSettings {
  parametros: Parameters;
  posicoes: Record<string, Position>;
  posicoes_demo: boolean;
  escolhas_manuais: Record<string, Record<string, string>>;
}

export interface ForecastPoint extends Point {
  faixa_min: number;
  faixa_max: number;
}

export interface ProjectionRow {
  periodo: string;
  inicial: number;
  venda_prevista: number;
  final: number;
}

export interface ProductPlan {
  produto: string;
  label: string;
  modelo_em_uso: string;
  modelo_label: string;
  escolha_manual: boolean;
  mape: number | null;
  mad: number | null;
  rmse: number;
  acuracia: number | null;
  observado: Point[];
  holdout_previsto: Point[];
  previsao: ForecastPoint[];
  lead_time: number;
  multiplo: number;
  estoque: number | null;
  a_receber: number | null;
  disponivel: number;
  estoque_informado: boolean;
  demanda_horizonte: number;
  estoque_seguranca: number;
  necessidade: number;
  projecao: ProjectionRow[];
  cobertura_meses: number;
  cobertura_texto: string;
  comprar_ate_texto: string;
  situacao: Situation;
  capacidade: number | null;
  excede_capacidade: boolean | null;
}

export interface PlanRead {
  run_id: string;
  ultimo_observado: string;
  horizon_years: number;
  horizonte_max: number;
  parametros: Parameters;
  avisos: string[];
  posicoes_demo: boolean;
  kpis: {
    produtos: number;
    unidades_previstas_horizonte: number;
    produtos_ruptura: number;
    unidades_comprar: number;
    produtos_comprar: number;
    acuracia_media: number | null;
  };
  produtos: ProductPlan[];
}

export interface OverviewRead {
  ativo: null | {
    run_id: string;
    concluido_em: string;
    periodo_inicio: string;
    periodo_fim: string;
    meses_historico: number;
    n_produtos: number;
    n_modelos: number;
    acuracia_media: number | null;
    holdout_inicio: string;
    holdout_fim: string;
  };
  treino_em_andamento: RunMeta | null;
}

export interface CompareRead {
  base: RunMeta;
  alvo: RunMeta;
  produtos: {
    produto: string;
    label: string;
    vencedor_base: string;
    vencedor_alvo: string;
    mape_base: number | null;
    mape_alvo: number | null;
    delta_mape_pp: number | null;
    soma12_base: number;
    soma12_alvo: number;
    delta_soma12_pct: number | null;
    periodo12_base: [string, string];
    periodo12_alvo: [string, string];
    holdout_base: [string, string];
    holdout_alvo: [string, string];
  }[];
  dados: { meses_adicionados: string[]; celulas_alteradas: number };
}

export interface ImportRow {
  produto: string;
  periodo: string;
  quantidade: number | null;
  estoque?: number | null;
  a_receber?: number | null;
  lead_time?: number | null;
  multiplo?: number | null;
}

// ---------- Erros e fetch ----------

export class ApiError extends Error {
  constructor(
    public status: number,
    public codigo: string,
    message: string,
    public detalhes: string[],
  ) {
    super(message);
  }
}

/** API fora do ar, sem resposta ou com 5xx (POC-32). */
export class ApiUnavailable extends Error {
  constructor() {
    super("Serviço de previsão indisponível");
  }
}

interface ErrorEnvelope {
  erro?: { codigo?: string; mensagem?: string; detalhes?: string[] };
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      ...init,
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiUnavailable();
  }
  if (response.status >= 500) throw new ApiUnavailable();
  if (response.ok === false) {
    const body = (await response.json().catch(() => ({}))) as ErrorEnvelope;
    throw new ApiError(
      response.status,
      body.erro?.codigo ?? "erro",
      body.erro?.mensagem ?? `Erro ${response.status}`,
      body.erro?.detalhes ?? [],
    );
  }
  return (await response.json()) as T;
}

function send<T>(method: string, path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Erro inesperado";
}

// ---------- Consultas ----------

export const keys = {
  overview: ["overview"] as const,
  plan: ["plan"] as const,
  settings: ["settings"] as const,
  runs: ["runs"] as const,
  run: (id: string) => ["run", id] as const,
  compare: (base: string, target: string) => ["compare", base, target] as const,
  datasets: ["datasets"] as const,
  dataset: (id: string) => ["dataset", id] as const,
};

const POLL_MS = 1500;

export function useOverview() {
  return useQuery({
    queryKey: keys.overview,
    queryFn: () => apiFetch<OverviewRead>("/overview"),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data == null) return POLL_MS;
      if (data.treino_em_andamento != null) return POLL_MS;
      if (data.ativo == null) return POLL_MS;
      return 5000;
    },
  });
}

export function usePlan() {
  return useQuery({ queryKey: keys.plan, queryFn: () => apiFetch<PlanRead>("/plan") });
}

export function useSettings() {
  return useQuery({
    queryKey: keys.settings,
    queryFn: () => apiFetch<WorkspaceSettings>("/settings"),
  });
}

export function useRuns() {
  return useQuery({
    queryKey: keys.runs,
    queryFn: () => apiFetch<RunRead[]>("/runs"),
    refetchInterval: (query) => {
      const open = query.state.data?.some((run) => run.status === "na_fila" || run.status === "executando");
      return open === true ? POLL_MS : false;
    },
  });
}

export function useRun(id: string | null) {
  return useQuery({
    queryKey: keys.run(id ?? ""),
    queryFn: () => apiFetch<RunRead>(`/runs/${id}`),
    enabled: id != null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "na_fila" || status === "executando") return POLL_MS;
      return false;
    },
  });
}

export function useCompare(base: string | null, target: string | null) {
  return useQuery({
    queryKey: keys.compare(base ?? "", target ?? ""),
    queryFn: () => apiFetch<CompareRead>(`/runs/compare?base=${base}&alvo=${target}`),
    enabled: base != null && target != null && base !== target,
  });
}

export function useDatasets() {
  return useQuery({ queryKey: keys.datasets, queryFn: () => apiFetch<DatasetMeta[]>("/datasets") });
}

export function useDataset(id: string | null) {
  return useQuery({
    queryKey: keys.dataset(id ?? ""),
    queryFn: () => apiFetch<DatasetRead>(`/datasets/${id}`),
    enabled: id != null,
  });
}

// ---------- Mutações ----------

function refreshWorkspace(client: QueryClient) {
  for (const key of [keys.overview, keys.runs, keys.datasets, keys.plan, keys.settings]) {
    void client.invalidateQueries({ queryKey: key });
  }
}

function useWorkspaceMutation<Input, Output>(action: (input: Input) => Promise<Output>) {
  const client = useQueryClient();
  return useMutation({ mutationFn: action, onSuccess: () => refreshWorkspace(client) });
}

export function useSaveSettings() {
  return useWorkspaceMutation((body: { parametros?: Parameters; posicoes?: Record<string, Position> }) =>
    send<WorkspaceSettings>("PUT", "/settings", body),
  );
}

export function useModelChoice() {
  return useWorkspaceMutation((input: { runId: string; produto: string; modelo: string | null }) =>
    send<PlanRead>("PUT", `/runs/${input.runId}/model-choice`, {
      produto: input.produto,
      modelo: input.modelo,
    }),
  );
}

export function useImport() {
  return useWorkspaceMutation(
    (body: { nome_arquivo: string | null; linhas: ImportRow[]; horizon_years: number }) =>
      send<ImportResult>("POST", "/datasets/import", body),
  );
}

export function useLoadCase() {
  return useWorkspaceMutation((body: { horizon_years: number }) =>
    send<ImportResult>("POST", "/datasets/case", body),
  );
}

export function useCloseMonth() {
  return useWorkspaceMutation(
    (input: {
      datasetId: string;
      itens: { produto: string; vendas: number; estoque: number | null; a_receber: number | null }[];
      horizon_years: number;
    }) =>
      send<ImportResult>("POST", `/datasets/${input.datasetId}/close-month`, {
        itens: input.itens,
        horizon_years: input.horizon_years,
      }),
  );
}

export function useEdits() {
  return useWorkspaceMutation(
    (input: { datasetId: string; celulas: { produto: string; periodo: string; unidades: number }[] }) =>
      send<ImportResult>("POST", `/datasets/${input.datasetId}/edits`, { celulas: input.celulas }),
  );
}

export function useStartRun() {
  return useWorkspaceMutation((body: { dataset_id: string; horizon_years: number }) =>
    send<RunMeta>("POST", "/runs", body),
  );
}

export function useActivate() {
  return useWorkspaceMutation((runId: string) => send<RunRead>("POST", `/runs/${runId}/activate`));
}

export function isTraining(run: RunMeta | null | undefined): boolean {
  return run != null && (run.status === "na_fila" || run.status === "executando");
}
