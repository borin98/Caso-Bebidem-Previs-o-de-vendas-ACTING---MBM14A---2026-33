"use client";

import { CalendarCheckIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { ApiErrorList } from "@/components/api-error-list";
import { HorizonSelect } from "@/components/horizon-select";
import { LeadTimeLabel } from "@/components/lead-time-help";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldError, FieldLabel, FieldLegend, FieldSet } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { type RunMeta, useCloseMonth, useDataset, useSettings } from "@/lib/api";
import { fmtNumber, monthLabel } from "@/lib/format";
import { type NumberRule, parseNumberInput } from "@/lib/number-input";

type Column = "vendas" | "estoque" | "a_receber";

const COLUMNS: { key: Column; label: string; rule: NumberRule }[] = [
  { key: "vendas", label: "Vendas do mês *", rule: { min: 0, max: 1_000_000_000, integer: true } },
  { key: "estoque", label: "Estoque ao fim do mês", rule: { min: 0, optional: true } },
  { key: "a_receber", label: "A receber", rule: { min: 0, optional: true } },
];

function nextPeriod(period: string): string {
  const [year, month] = period.split("-").map(Number);
  if (month === 12) return `${year + 1}-01`;
  return `${year}-${String(month + 1).padStart(2, "0")}`;
}

/** Aba "Fechar mês" (POC-18): mês U+1 fixo, vendas obrigatórias, cria versão e re-treina. */
export function CloseMonth({
  datasetId,
  disabled,
  onRunStarted,
}: {
  datasetId: string | null;
  disabled: boolean;
  onRunStarted: (run: RunMeta | null) => void;
}) {
  const dataset = useDataset(datasetId);
  const settings = useSettings();
  const close = useCloseMonth();
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [horizon, setHorizon] = useState(2);
  if (dataset.data == null) return <Skeleton className="h-64 w-full" />;
  const data = dataset.data;
  const target = nextPeriod(data.periodo_fim);
  const parsed = (produto: string, column: (typeof COLUMNS)[number]) =>
    parseNumberInput(draft[`${produto}|${column.key}`] ?? "", column.rule);
  const hasErrors = data.produtos.some((product) =>
    COLUMNS.some((column) => parsed(product.produto, column).error != null),
  );
  const leadTime = (produto: string) =>
    settings.data?.posicoes[produto]?.lead_time ?? settings.data?.parametros.lead_time_padrao ?? null;

  const submit = () => {
    const itens = data.produtos.map((product) => {
      const [vendas, estoque, aReceber] = COLUMNS.map((column) => parsed(product.produto, column).value);
      return { produto: product.produto, vendas: vendas ?? 0, estoque, a_receber: aReceber };
    });
    close.mutate(
      { datasetId: data.id, itens, horizon_years: horizon },
      {
        onSuccess: (result) => {
          toast.success(`Mês ${monthLabel(target)} fechado; re-treino iniciado`);
          setDraft({});
          onRunStarted(result.run);
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Fechar {monthLabel(target)}</CardTitle>
        <CardDescription>
          Informe as vendas do mês que fechou. Isso cria uma nova versão de dados a partir da versão
          ativa e re-treina todos os modelos (máx. 60 s).
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <Field className="w-56">
          <FieldLabel htmlFor="mes-fechamento">Mês</FieldLabel>
          <Input id="mes-fechamento" value={monthLabel(target)} readOnly disabled />
        </Field>
        {data.produtos.map((product) => (
          <FieldSet key={product.produto}>
            <FieldLegend>{product.label}</FieldLegend>
            <div className="grid gap-4 md:grid-cols-4">
              {COLUMNS.map((column) => {
                const id = `${product.produto}-${column.key}`;
                const touched = draft[`${product.produto}|${column.key}`] !== undefined;
                // Required-but-empty only blocks the button until the user types in the field.
                const error = touched ? parsed(product.produto, column).error : null;
                return (
                  <Field key={column.key} data-invalid={error != null}>
                    <FieldLabel htmlFor={id}>{column.label}</FieldLabel>
                    <Input
                      id={id}
                      inputMode="numeric"
                      aria-invalid={error != null}
                      value={draft[`${product.produto}|${column.key}`] ?? ""}
                      onChange={(event) =>
                        setDraft((current) => ({
                          ...current,
                          [`${product.produto}|${column.key}`]: event.target.value,
                        }))
                      }
                    />
                    {error != null && <FieldError>{error}</FieldError>}
                  </Field>
                );
              })}
              <Field>
                <FieldLabel>
                  <LeadTimeLabel suffix=" em uso" />
                </FieldLabel>
                <span className="flex h-9 items-center text-sm tabular-nums">
                  {fmtNumber(leadTime(product.produto), 1)} m
                </span>
              </Field>
            </div>
          </FieldSet>
        ))}
        <ApiErrorList error={close.error} />
        <div className="flex flex-wrap items-end gap-3">
          <HorizonSelect id="horizonte-fechamento" value={horizon} onChange={setHorizon} />
          <Button onClick={submit} disabled={hasErrors || disabled || close.isPending}>
            <CalendarCheckIcon data-icon="inline-start" />
            Fechar mês e re-treinar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
