// Leitura, mapeamento e geração de planilhas no navegador (SheetJS CE 0.20.3, canal oficial
// cdn.sheetjs.com). Regras portadas de previsao-compras-local.html:222–309 e :585–614.
import * as XLSX from "xlsx";

import type { ImportRow, PlanRead, RunResult } from "@/lib/api";
import { SITUATION_LABEL, monthLabel, normalizeText } from "@/lib/format";
import { LEAD_TIME_HELP } from "@/lib/help";

export const MAX_FILE_BYTES = 5 * 1024 * 1024;
export const ACCEPTED_EXTENSIONS = ".xlsx,.xls,.csv,.txt";
export const PERIOD_FORMATS = "2024-01, 01/2024, jan/24, 202401 ou uma data do mês";

const MONTHS_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const MONTHS_EN = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

export type FieldKey = "prod" | "per" | "qty" | "est" | "rec" | "lt" | "lote";

export const FIELDS: { key: FieldKey; label: string; required: boolean; pattern: RegExp }[] = [
  { key: "prod", label: "Produto", required: true, pattern: /produto|item|sku|descri|material|codigo|cod/ },
  { key: "per", label: "Período", required: true, pattern: /periodo|data|mes|compet|date|month|ano/ },
  {
    key: "qty",
    label: "Quantidade vendida",
    required: true,
    pattern: /quant|qtd|qtde|vend|demanda|saida|consumo/,
  },
  { key: "est", label: "Estoque", required: false, pattern: /estoque|saldo|stock/ },
  { key: "rec", label: "A receber", required: false, pattern: /receber|transito|pedido|aberto/ },
  { key: "lt", label: "Lead time", required: false, pattern: /lead|prazo|reposi/ },
  { key: "lote", label: "Múltiplo de compra", required: false, pattern: /lote|multiplo|embalagem|caixa/ },
];

// Optional columns are matched first so "Estoque" is not taken by a broader required pattern.
const AUTO_MAP_ORDER: FieldKey[] = ["est", "rec", "lt", "lote", "prod", "per", "qty"];

export type Mapping = Partial<Record<FieldKey, string>>;
export type RawRow = Record<string, unknown>;

export interface SheetData {
  headers: string[];
  rows: RawRow[];
  wide: boolean;
}

export class SpreadsheetError extends Error {}

function monthFromName(value: string): number | null {
  const prefix = normalizeText(value).slice(0, 3);
  const pt = MONTHS_PT.indexOf(prefix);
  if (pt >= 0) return pt + 1;
  const en = MONTHS_EN.indexOf(prefix);
  if (en >= 0) return en + 1;
  return null;
}

/** Brazilian or international number text → number; NaN when not numeric. */
export function toNumber(value: unknown): number {
  if (typeof value === "number") return value;
  if (value == null) return Number.NaN;
  const text = String(value).trim().replace(/\s/g, "");
  if (text === "") return Number.NaN;
  const decimalComma = /,\d{1,3}$/.test(text);
  const normalized = decimalComma
    ? text.replace(/\./g, "").replace(",", ".")
    : text.replace(/,/g, "");
  return Number(normalized);
}

function pad(month: number): string {
  return String(month).padStart(2, "0");
}

/** Period in any accepted format → "YYYY-MM", or null when not recognized. */
export function parsePeriod(value: unknown): string | null {
  if (value == null || value === "") return null;
  if (value instanceof Date) {
    const shifted = new Date(value.getTime() + 432e5);
    return `${shifted.getFullYear()}-${pad(shifted.getMonth() + 1)}`;
  }
  if (typeof value === "number") {
    if (value >= 190001 && value <= 210012 && value % 100 >= 1 && value % 100 <= 12) {
      return `${Math.floor(value / 100)}-${pad(value % 100)}`;
    }
    if (value > 20000 && value < 80000) {
      const date = XLSX.SSF.parse_date_code(value);
      return `${date.y}-${pad(date.m)}`;
    }
    return null;
  }
  const text = normalizeText(String(value));
  let match = text.match(/^(\d{4})[-/.](\d{1,2})(?:[-/.]\d{1,2})?/);
  if (match != null) return validPeriod(Number(match[1]), Number(match[2]));
  match = text.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})/);
  if (match != null) return validPeriod(Number(match[3]), Number(match[2]));
  match = text.match(/^(\d{1,2})[-/.](\d{4})$/);
  if (match != null) return validPeriod(Number(match[2]), Number(match[1]));
  match = text.match(/^([a-z]{3})[a-z]*\.?[\s\-/.]*(\d{4}|\d{2})$/);
  if (match != null) {
    const month = monthFromName(match[1]);
    const year = Number(match[2]) < 100 ? Number(match[2]) + 2000 : Number(match[2]);
    if (month != null) return validPeriod(year, month);
  }
  match = text.match(/^(\d{4})(\d{2})$/);
  if (match != null) return validPeriod(Number(match[1]), Number(match[2]));
  return null;
}

function validPeriod(year: number, month: number): string | null {
  if (month < 1 || month > 12) return null;
  if (year < 1900 || year > 2199) return null;
  return `${year}-${pad(month)}`;
}

function detectDelimiter(text: string): string {
  const firstLine = text.split(/\r?\n/, 1)[0] ?? "";
  const counts = ["\t", ";", ","].map((separator) => firstLine.split(separator).length - 1);
  const best = Math.max(...counts);
  return ["\t", ";", ","][counts.indexOf(best)];
}

/** Reads .xlsx/.xls/.csv/.txt up to 5 MB; throws SpreadsheetError with a PT-BR message. */
export async function readWorkbook(file: File): Promise<XLSX.WorkBook> {
  if (file.size > MAX_FILE_BYTES) throw new SpreadsheetError("Arquivo maior que 5 MB");
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (["xlsx", "xls", "csv", "txt"].includes(extension) === false) {
    throw new SpreadsheetError("Formato não aceito: use .xlsx, .xls, .csv ou .txt");
  }
  try {
    if (extension === "csv" || extension === "txt") {
      const text = await file.text();
      return XLSX.read(text, { type: "string", FS: detectDelimiter(text), raw: true });
    }
    return XLSX.read(await file.arrayBuffer(), { cellDates: true });
  } catch {
    throw new SpreadsheetError("Não foi possível ler o arquivo como planilha");
  }
}

interface WideLayout {
  months: (number | null)[];
  yearHeader: string;
}

function detectWide(headers: string[]): WideLayout | null {
  const months = headers.map((header) => {
    const name = normalizeText(header);
    return /^[a-z]{3,9}\.?$/.test(name) ? monthFromName(name) : null;
  });
  const yearHeader = headers.find((header) => /^ano/.test(normalizeText(header)) || normalizeText(header) === "year");
  if (yearHeader == null) return null;
  if (months.filter((month) => month != null).length < 6) return null;
  return { months, yearHeader };
}

function wideToLong(rows: RawRow[], headers: string[], wide: WideLayout): RawRow[] {
  const find = (pattern: RegExp) => headers.find((header) => pattern.test(normalizeText(header)));
  const productHeader = find(/produto|item|sku|descri/);
  const stockHeader = find(/estoque|saldo|stock/);
  const incomingHeader = find(/receber|transito|pedido/);
  const output: RawRow[] = [];
  for (const row of rows) {
    const year = Math.trunc(toNumber(row[wide.yearHeader]));
    if (Number.isFinite(year) === false || year === 0) continue;
    headers.forEach((header, index) => {
      const month = wide.months[index];
      if (month == null) return;
      if (row[header] === "" || row[header] == null) return;
      output.push({
        Produto: productHeader == null ? "Produto" : row[productHeader],
        Período: `${year}-${pad(month)}`,
        "Quantidade vendida": row[header],
        Estoque: stockHeader == null ? "" : row[stockHeader],
        "A receber": incomingHeader == null ? "" : row[incomingHeader],
      });
    });
  }
  return output;
}

/** First-row headers and rows of one sheet; wide layout (ano + months) becomes one row per month. */
export function sheetData(book: XLSX.WorkBook, sheetName: string): SheetData {
  const sheet = book.Sheets[sheetName];
  const rows = XLSX.utils.sheet_to_json<RawRow>(sheet, { defval: "", raw: true });
  if (rows.length === 0) throw new SpreadsheetError("A aba selecionada está vazia");
  const headerRow = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, blankrows: false })[0] ?? [];
  const headers = headerRow.map((header) => String(header ?? "").trim()).filter((header) => header !== "");
  const wide = detectWide(headers);
  if (wide == null) return { headers, rows, wide: false };
  const converted = wideToLong(rows, headers, wide);
  return { headers: ["Produto", "Período", "Quantidade vendida", "Estoque", "A receber"], rows: converted, wide: true };
}

export function autoMap(headers: string[]): Mapping {
  const mapping: Mapping = {};
  const used = new Set<string>();
  for (const key of AUTO_MAP_ORDER) {
    const field = FIELDS.find((item) => item.key === key);
    const header = headers.find((item) => used.has(item) === false && field?.pattern.test(normalizeText(item)));
    if (header == null) continue;
    mapping[key] = header;
    used.add(header);
  }
  return mapping;
}

export interface NormalizedRows {
  linhas: ImportRow[];
  ignored: number;
  aggregated: number;
  products: number;
  firstPeriod: string | null;
  lastPeriod: string | null;
}

function optionalNumber(row: RawRow, header: string | undefined): number | null {
  if (header == null) return null;
  const value = toNumber(row[header]);
  return Number.isNaN(value) ? null : value;
}

/** Maps, parses periods and sums rows with the same product and month before sending. */
export function normalizeRows(rows: RawRow[], mapping: Mapping): NormalizedRows {
  const byKey = new Map<string, ImportRow>();
  let ignored = 0;
  let aggregated = 0;
  for (const row of rows) {
    const product = String(row[mapping.prod ?? ""] ?? "").trim();
    if (product === "") continue;
    const period = parsePeriod(row[mapping.per ?? ""]);
    if (period == null) {
      ignored += 1;
      continue;
    }
    const quantity = toNumber(row[mapping.qty ?? ""]);
    const current: ImportRow = {
      produto: product,
      periodo: period,
      quantidade: Number.isNaN(quantity) ? null : quantity,
      estoque: optionalNumber(row, mapping.est),
      a_receber: optionalNumber(row, mapping.rec),
      lead_time: optionalNumber(row, mapping.lt),
      multiplo: optionalNumber(row, mapping.lote),
    };
    const key = `${product}\u0000${period}`;
    const previous = byKey.get(key);
    if (previous == null) {
      byKey.set(key, current);
      continue;
    }
    aggregated += 1;
    byKey.set(key, {
      ...previous,
      // A null quantity stays null so the API rejects it with product and period.
      quantidade:
        previous.quantidade == null || current.quantidade == null
          ? null
          : previous.quantidade + current.quantidade,
      estoque: current.estoque ?? previous.estoque,
      a_receber: current.a_receber ?? previous.a_receber,
      lead_time: current.lead_time ?? previous.lead_time,
      multiplo: current.multiplo ?? previous.multiplo,
    });
  }
  const linhas = [...byKey.values()];
  const periods = linhas.map((row) => row.periodo).sort();
  return {
    linhas,
    ignored,
    aggregated,
    products: new Set(linhas.map((row) => row.produto)).size,
    firstPeriod: periods[0] ?? null,
    lastPeriod: periods.at(-1) ?? null,
  };
}

/** "Baixar planilha modelo" (POC-17): Vendas (case, long layout) + Instruções. */
export function downloadTemplate(rows: { produto_label: string; periodo: string; unidades: number }[]) {
  const book = XLSX.utils.book_new();
  const sales = rows.map((row) => ({
    Produto: row.produto_label,
    Período: row.periodo,
    "Quantidade vendida": row.unidades,
    Estoque: "",
    "A receber": "",
    "Lead time (meses)": "",
    "Múltiplo de compra": "",
  }));
  XLSX.utils.book_append_sheet(book, XLSX.utils.json_to_sheet(sales), "Vendas");
  XLSX.utils.book_append_sheet(
    book,
    XLSX.utils.aoa_to_sheet([
      ["Coluna", "Obrigatória", "Como preencher"],
      ["Produto", "Sim", "Nome ou código do produto. Repita em cada linha."],
      ["Período", "Sim", `Mês da venda: ${PERIOD_FORMATS}.`],
      ["Quantidade vendida", "Sim", "Unidades vendidas no mês. Várias linhas do mesmo mês são somadas."],
      ["Estoque", "Não", "Posição de estoque atual. Basta informar na linha do último mês."],
      ["A receber", "Não", "Pedidos de compra em aberto que ainda vão entrar."],
      ["Lead time (meses)", "Não", `${LEAD_TIME_HELP} Se vazio, usa o valor padrão do painel.`],
      ["Múltiplo de compra", "Não", "Tamanho da caixa ou lote mínimo do produto."],
    ]),
    "Instruções",
  );
  XLSX.writeFile(book, "modelo_previsao_compras.xlsx");
}

const round = (value: number | null, digits: number): number | string =>
  value == null ? "" : Number(value.toFixed(digits));

/** "Exportar para Excel" (POC-37): Resumo, Previsão mensal e Comparativo de modelos. */
export function exportPlan(plan: PlanRead, result: RunResult) {
  const horizon = plan.parametros.horizonte_meses;
  const book = XLSX.utils.book_new();
  const summary = plan.produtos.map((row) => ({
    Produto: row.label,
    Modelo: row.modelo_label,
    "MAPE (%)": round(row.mape, 1),
    [`Previsão ${horizon} meses`]: Math.round(row.demanda_horizonte),
    Estoque: row.estoque ?? 0,
    "A receber": row.a_receber ?? 0,
    "Meses cobertos": row.cobertura_texto,
    "Estoque de segurança": Math.round(row.estoque_seguranca),
    "Necessidade de compra": row.necessidade,
    "Comprar até": row.comprar_ate_texto,
    Situação: SITUATION_LABEL[row.situacao],
  }));
  XLSX.utils.book_append_sheet(book, XLSX.utils.json_to_sheet(summary), "Resumo");
  const months = Math.max(12, horizon);
  const monthly = plan.produtos.flatMap((row) =>
    row.previsao.slice(0, months).map((point, index) => ({
      Produto: row.label,
      Mês: monthLabel(point.periodo),
      "Venda prevista": Math.round(point.valor),
      "Estoque inicial": index < row.projecao.length ? Math.round(row.projecao[index].inicial) : "",
      "Estoque final": index < row.projecao.length ? Math.round(row.projecao[index].final) : "",
    })),
  );
  XLSX.utils.book_append_sheet(book, XLSX.utils.json_to_sheet(monthly), "Previsão mensal");
  const inUse = new Map(plan.produtos.map((row) => [row.produto, row.modelo_em_uso]));
  const models = result.produtos.flatMap((product) =>
    product.modelos.map((model) => ({
      Produto: product.label,
      Modelo: model.label,
      Escolhido: inUse.get(product.produto) === model.modelo ? "sim" : "",
      "MAPE (%)": round(model.mape, 1),
      MAD: round(model.mad, 2),
      RMSE: round(model.rmse, 2),
      "MPE (%)": round(model.mpe, 1),
    })),
  );
  XLSX.utils.book_append_sheet(book, XLSX.utils.json_to_sheet(models), "Comparativo de modelos");
  XLSX.writeFile(book, "previsao_necessidade_compra.xlsx");
}
