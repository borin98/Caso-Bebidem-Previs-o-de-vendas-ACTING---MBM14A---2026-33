"use client";

import { DownloadIcon, FileSpreadsheetIcon, SparklesIcon, UploadIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import type { WorkBook } from "xlsx";

import { ApiErrorList } from "@/components/api-error-list";
import { HorizonSelect } from "@/components/horizon-select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldLabel } from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  type DatasetRead,
  type RunMeta,
  apiFetch,
  errorMessage,
  useDatasets,
  useImport,
  useLoadCase,
} from "@/lib/api";
import { monthNumeric } from "@/lib/format";
import {
  ACCEPTED_EXTENSIONS,
  FIELDS,
  type FieldKey,
  type Mapping,
  PERIOD_FORMATS,
  type SheetData,
  SpreadsheetError,
  autoMap,
  downloadTemplate,
  normalizeRows,
  readWorkbook,
  sheetData,
} from "@/lib/spreadsheet";

const NONE = "__nenhuma__";

interface Loaded {
  fileName: string;
  book: WorkBook;
  sheet: string;
  data: SheetData | null;
  mapping: Mapping;
}

function loadSheet(fileName: string, book: WorkBook, sheet: string): Loaded {
  const data = sheetData(book, sheet);
  return { fileName, book, sheet, data, mapping: autoMap(data.headers) };
}

/** Aba "Importar" (POC-15/16/17): arquivo → aba → mapeamento → prévia → nova versão + treino. */
export function DataImport({
  disabled,
  onRunStarted,
}: {
  disabled: boolean;
  onRunStarted: (run: RunMeta | null) => void;
}) {
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [horizon, setHorizon] = useState(2);
  const [dragging, setDragging] = useState(false);
  const importRows = useImport();
  const loadCase = useLoadCase();
  const datasets = useDatasets();

  const openFile = async (file: File | undefined) => {
    if (file == null) return;
    setFileError(null);
    setLoaded(null);
    importRows.reset();
    try {
      const book = await readWorkbook(file);
      setLoaded(loadSheet(file.name, book, book.SheetNames[0]));
    } catch (error) {
      if (error instanceof SpreadsheetError) {
        setFileError(error.message);
        return;
      }
      throw error;
    }
  };
  const selectSheet = (sheet: string) => {
    if (loaded == null) return;
    setFileError(null);
    try {
      setLoaded(loadSheet(loaded.fileName, loaded.book, sheet));
    } catch (error) {
      if (error instanceof SpreadsheetError) {
        setLoaded({ ...loaded, sheet, data: null, mapping: {} });
        setFileError(error.message);
        return;
      }
      throw error;
    }
  };
  const setField = (key: FieldKey, header: string) => {
    if (loaded == null) return;
    setLoaded({ ...loaded, mapping: { ...loaded.mapping, [key]: header === NONE ? undefined : header } });
  };

  const data = loaded?.data ?? null;
  const missingRequired = FIELDS.filter((field) => field.required && loaded?.mapping[field.key] == null);
  const normalized = data != null && missingRequired.length === 0 ? normalizeRows(data.rows, loaded?.mapping ?? {}) : null;
  const allIgnored = normalized != null && normalized.linhas.length === 0;
  const canImport = normalized != null && allIgnored === false && disabled === false && importRows.isPending === false;

  const submit = () => {
    if (normalized == null || loaded == null) return;
    importRows.mutate(
      { nome_arquivo: loaded.fileName, linhas: normalized.linhas, horizon_years: horizon },
      {
        onSuccess: (result) => {
          toast.success(
            `Versão ${result.dataset.id} criada: ${result.dataset.produtos.length} produto(s), ${monthNumeric(result.dataset.periodo_inicio)}–${monthNumeric(result.dataset.periodo_fim)}`,
          );
          for (const aviso of result.avisos) toast.warning(aviso);
          onRunStarted(result.run);
        },
      },
    );
  };
  const loadCaseData = () =>
    loadCase.mutate(
      { horizon_years: horizon },
      {
        onSuccess: (result) => {
          toast.success("Dados do caso carregados com posições de demonstração");
          onRunStarted(result.run);
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    );
  const template = async () => {
    const caseMeta = datasets.data?.find((item) => item.origem === "caso");
    if (caseMeta == null) {
      toast.error("Versão do caso não encontrada");
      return;
    }
    try {
      const caseData = await apiFetch<DatasetRead>(`/datasets/${caseMeta.id}`);
      downloadTemplate(caseData.linhas);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Carregar vendas</CardTitle>
          <CardDescription>
            Planilha .xlsx, .xls, .csv ou .txt de até 5 MB. Uma linha por produto e mês, ou o formato
            largo com colunas de jan a dez.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <label
            htmlFor="arquivo"
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              void openFile(event.dataTransfer.files[0]);
            }}
            data-dragging={dragging}
            className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground data-[dragging=true]:border-primary data-[dragging=true]:bg-primary/5"
          >
            <UploadIcon className="size-6" />
            <span>
              Solte o arquivo aqui ou <span className="font-medium text-foreground">escolha um arquivo</span>
            </span>
            {loaded != null && (
              <span className="flex items-center gap-1 text-foreground">
                <FileSpreadsheetIcon className="size-4" />
                {loaded.fileName}
              </span>
            )}
            <input
              id="arquivo"
              type="file"
              accept={ACCEPTED_EXTENSIONS}
              className="sr-only"
              onChange={(event) => {
                void openFile(event.target.files?.[0]);
                event.target.value = "";
              }}
            />
          </label>
          {fileError != null && (
            <Alert variant="destructive">
              <AlertTitle>{fileError}</AlertTitle>
            </Alert>
          )}
          <div className="flex flex-wrap items-end gap-3">
            <HorizonSelect id="horizonte-importacao" value={horizon} onChange={setHorizon} />
            <Button variant="outline" onClick={() => void template()}>
              <DownloadIcon data-icon="inline-start" />
              Baixar planilha modelo
            </Button>
            <Button variant="outline" onClick={loadCaseData} disabled={disabled || loadCase.isPending}>
              <SparklesIcon data-icon="inline-start" />
              Usar dados do caso
            </Button>
          </div>
        </CardContent>
      </Card>

      {loaded != null && (
        <Card>
          <CardHeader>
            <CardTitle>Mapeamento de colunas</CardTitle>
            <CardDescription>
              Colunas identificadas pelo nome; ajuste se necessário. Campos com * são obrigatórios.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {loaded.book.SheetNames.length > 1 && (
              <Field className="w-64">
                <FieldLabel htmlFor="aba">Aba</FieldLabel>
                <Select value={loaded.sheet} onValueChange={selectSheet}>
                  <SelectTrigger id="aba" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {loaded.book.SheetNames.map((name) => (
                        <SelectItem key={name} value={name}>
                          {name}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>
            )}
            {data?.wide === true && (
              <p className="text-sm text-muted-foreground">
                Formato largo detectado (ano + meses): convertido para uma linha por produto e mês.
              </p>
            )}
            {data != null && (
              <div className="grid gap-4 md:grid-cols-4">
                {FIELDS.map((field) => (
                  <Field key={field.key} data-invalid={field.required && loaded.mapping[field.key] == null}>
                    <FieldLabel htmlFor={`map-${field.key}`}>
                      {field.label}
                      {field.required && " *"}
                    </FieldLabel>
                    <Select
                      value={loaded.mapping[field.key] ?? NONE}
                      onValueChange={(value) => setField(field.key, value)}
                    >
                      <SelectTrigger id={`map-${field.key}`} className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectItem value={NONE}>— não usar —</SelectItem>
                          {data.headers.map((header) => (
                            <SelectItem key={header} value={header}>
                              {header}
                            </SelectItem>
                          ))}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </Field>
                ))}
              </div>
            )}
            {data != null && (
              <div className="flex flex-col gap-2">
                <h3 className="text-sm font-medium">Prévia (5 primeiras linhas)</h3>
                <div className="overflow-x-auto rounded-lg border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {data.headers.slice(0, 8).map((header) => (
                          <TableHead key={header}>{header}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.rows.slice(0, 5).map((row, index) => (
                        <TableRow key={index}>
                          {data.headers.slice(0, 8).map((header) => (
                            <TableCell key={header}>
                              {row[header] instanceof Date
                                ? (row[header] as Date).toLocaleDateString("pt-BR")
                                : String(row[header] ?? "")}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
            {normalized != null && allIgnored === false && (
              <p className="text-sm text-muted-foreground">
                {normalized.linhas.length} linha(s) de {normalized.products} produto(s),{" "}
                {monthNumeric(normalized.firstPeriod ?? "")}–{monthNumeric(normalized.lastPeriod ?? "")}.
                {normalized.aggregated > 0 && ` ${normalized.aggregated} linha(s) agregada(s) (mesmo produto e mês).`}
                {normalized.ignored > 0 &&
                  ` ${normalized.ignored} linhas ignoradas por período não reconhecido.`}
              </p>
            )}
            {allIgnored && (
              <Alert variant="destructive">
                <AlertTitle>Nenhum período reconhecido</AlertTitle>
                <AlertDescription>Formatos aceitos: {PERIOD_FORMATS}.</AlertDescription>
              </Alert>
            )}
            <ApiErrorList error={importRows.error} />
            <div>
              <Button onClick={submit} disabled={canImport === false}>
                <UploadIcon data-icon="inline-start" />
                Importar e treinar
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
