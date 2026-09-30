"use client";

import { RefreshCwIcon, SaveIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { ApiErrorList } from "@/components/api-error-list";
import { HorizonSelect } from "@/components/horizon-select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  type DatasetMeta,
  type DatasetRead,
  type RunMeta,
  errorMessage,
  useDataset,
  useEdits,
  useStartRun,
} from "@/lib/api";
import { parseNumberInput } from "@/lib/number-input";
import { cn } from "@/lib/utils";

const MONTH_HEADERS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const CELL_RULE = { min: 0, max: 1_000_000_000, integer: true };

const cellKey = (produto: string, periodo: string) => `${produto}|${periodo}`;

function ProductGrid({
  dataset,
  produto,
  draft,
  onChange,
}: {
  dataset: DatasetRead;
  produto: string;
  draft: Record<string, string>;
  onChange: (key: string, value: string) => void;
}) {
  const rows = dataset.linhas.filter((row) => row.produto === produto);
  const years = [...new Set(rows.map((row) => row.periodo.slice(0, 4)))];
  const byPeriod = new Map(rows.map((row) => [row.periodo, row]));
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Ano</TableHead>
            {MONTH_HEADERS.map((month) => (
              <TableHead key={month} className="text-center">
                {month}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {years.map((year) => (
            <TableRow key={year}>
              <TableCell className="font-medium">{year}</TableCell>
              {MONTH_HEADERS.map((month, index) => {
                const periodo = `${year}-${String(index + 1).padStart(2, "0")}`;
                const original = byPeriod.get(periodo);
                if (original == null) return <TableCell key={month} />;
                const key = cellKey(produto, periodo);
                const text = draft[key] ?? String(original.unidades);
                const invalid = parseNumberInput(text, CELL_RULE).error != null;
                const changed = draft[key] != null && Number(text) !== original.unidades;
                return (
                  <TableCell key={month} className="p-1">
                    <Input
                      aria-label={`${original.produto_label} ${periodo}`}
                      aria-invalid={invalid}
                      title={invalid ? "Use um inteiro maior ou igual a zero" : undefined}
                      inputMode="numeric"
                      value={text}
                      onChange={(event) => onChange(key, event.target.value)}
                      className={cn("h-8 w-16 text-right tabular-nums", changed && "bg-primary/10")}
                    />
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** Aba "Grade" (POC-35): edita a versão ativa e cria uma versão `edicao`. */
export function EditGrid({
  datasetId,
  disabled,
  onRunStarted,
}: {
  datasetId: string | null;
  disabled: boolean;
  onRunStarted: (run: RunMeta | null) => void;
}) {
  const dataset = useDataset(datasetId);
  const edits = useEdits();
  const startRun = useStartRun();
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [created, setCreated] = useState<DatasetMeta | null>(null);
  const [horizon, setHorizon] = useState(2);
  if (dataset.data == null) return <Skeleton className="h-64 w-full" />;
  const data = dataset.data;
  const originals = new Map(data.linhas.map((row) => [cellKey(row.produto, row.periodo), row]));
  const entries = Object.entries(draft);
  const invalidCount = entries.filter(([, text]) => parseNumberInput(text, CELL_RULE).error != null).length;
  const changes = entries
    .filter(([, text]) => parseNumberInput(text, CELL_RULE).error == null)
    .map(([key, text]) => ({ original: originals.get(key), unidades: Number(text) }))
    .filter((item) => item.original != null && item.original.unidades !== item.unidades);

  const save = () => {
    if (changes.length === 0) {
      toast.info("Nenhuma alteração");
      return;
    }
    edits.mutate(
      {
        datasetId: data.id,
        celulas: changes.map((item) => ({
          produto: item.original?.produto ?? "",
          periodo: item.original?.periodo ?? "",
          unidades: item.unidades,
        })),
      },
      {
        onSuccess: (result) => {
          setCreated(result.dataset);
          setDraft({});
          toast.success(`Versão de edição criada (${result.avisos.join(", ")})`);
        },
      },
    );
  };
  const retrain = () => {
    if (created == null) return;
    startRun.mutate(
      { dataset_id: created.id, horizon_years: horizon },
      {
        onSuccess: (run) => {
          setCreated(null);
          onRunStarted(run);
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Grade produto × mês</CardTitle>
        <CardDescription>
          Corrija valores da versão ativa ({data.id}). Salvar cria uma nova versão de edição; o
          treino só roda ao clicar em &quot;Re-treinar agora&quot;.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {data.produtos.map((product) => (
          <div key={product.produto} className="flex flex-col gap-2">
            <h3 className="text-sm font-medium">{product.label}</h3>
            <ProductGrid
              dataset={data}
              produto={product.produto}
              draft={draft}
              onChange={(key, value) => setDraft((current) => ({ ...current, [key]: value }))}
            />
          </div>
        ))}
        {invalidCount > 0 && (
          <Alert variant="destructive">
            <AlertTitle>{invalidCount} célula(s) inválida(s)</AlertTitle>
            <AlertDescription>Use números inteiros maiores ou iguais a zero.</AlertDescription>
          </Alert>
        )}
        <ApiErrorList error={edits.error} />
        <div className="flex flex-wrap items-end gap-3">
          <Button onClick={save} disabled={invalidCount > 0 || edits.isPending}>
            <SaveIcon data-icon="inline-start" />
            Salvar alterações ({changes.length})
          </Button>
        </div>
        {created != null && (
          <Alert>
            <AlertTitle>Nova versão {created.id} criada</AlertTitle>
            <AlertDescription className="flex flex-wrap items-end gap-3">
              <HorizonSelect id="horizonte-grade" value={horizon} onChange={setHorizon} />
              <Button onClick={retrain} disabled={disabled || startRun.isPending}>
                <RefreshCwIcon data-icon="inline-start" />
                Re-treinar agora
              </Button>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
