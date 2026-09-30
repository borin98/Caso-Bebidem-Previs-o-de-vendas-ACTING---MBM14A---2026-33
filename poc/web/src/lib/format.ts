import type { Family, Origin, RunStatus, Situation } from "@/lib/api";

const MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

export function fmtNumber(value: number | null | undefined, digits = 0): string {
  if (value == null) return "–";
  return value.toLocaleString("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value == null) return "n/d";
  return `${fmtNumber(value, digits)}%`;
}

export function fmtSigned(value: number | null | undefined, digits = 1, suffix = ""): string {
  if (value == null) return "n/d";
  const sign = value > 0 ? "+" : "";
  return `${sign}${fmtNumber(value, digits)}${suffix}`;
}

/** "2025-03" → "mar/2025" */
export function monthLabel(period: string): string {
  const [year, month] = period.split("-");
  return `${MONTHS[Number(month) - 1]}/${year}`;
}

/** "2025-03" → "03/2025" */
export function monthNumeric(period: string): string {
  const [year, month] = period.split("-");
  return `${month}/${year}`;
}

export function periodRange(start: string, end: string): string {
  return `${monthNumeric(start)}–${monthNumeric(end)}`;
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (iso == null) return "–";
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function normalizeText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export const FAMILY_LABEL: Record<Family, string> = {
  ml: "Machine learning",
  classica: "Regressão clássica",
  series_temporais: "Séries temporais",
};

export const SITUATION_LABEL: Record<Situation, string> = {
  ruptura: "Ruptura prevista",
  comprar: "Comprar",
  adequado: "Adequado",
  excesso: "Excesso",
};

export const SITUATION_VARIANT: Record<Situation, "destructive" | "default" | "secondary" | "outline"> = {
  ruptura: "destructive",
  comprar: "default",
  adequado: "secondary",
  excesso: "outline",
};

export const ORIGIN_LABEL: Record<Origin, string> = {
  caso: "Caso",
  importacao: "Importação",
  fechamento: "Fechamento",
  edicao: "Edição",
};

export const STATUS_LABEL: Record<RunStatus, string> = {
  na_fila: "Na fila",
  executando: "Executando",
  concluido: "Concluído",
  falhou: "Falhou",
};

export const SERVICE_LEVEL_LABEL: Record<string, string> = {
  "0.90": "90%",
  "0.95": "95%",
  "0.975": "97,5%",
  "0.99": "99%",
};
