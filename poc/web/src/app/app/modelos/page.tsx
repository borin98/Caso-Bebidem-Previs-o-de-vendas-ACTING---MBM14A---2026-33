"use client";

import { TrophyIcon } from "lucide-react";
import { BlockMath } from "react-katex";

import { useState } from "react";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import { PageHeader } from "@/components/page-header";
import { QueryState } from "@/components/query-state";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
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
import { ApiError, type ModelResult, type ProductResult, useOverview, useRun } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  FAMILY_LABEL,
  fmtNumber,
  fmtPct,
  monthLabel,
  monthNumeric,
  periodRange,
} from "@/lib/format";
import { CRITERION_TEXT } from "@/lib/help";
import { MODEL_FORMULAS } from "@/lib/model-formulas";


const SERIES_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "oklch(0.7 0.15 90)",
  "oklch(0.6 0.12 200)",
  "oklch(0.5 0.1 330)",
  "oklch(0.55 0.05 60)",
];

/** Applicable models by rank, then non-applicable ones (POC-29). */
function rankedModels(product: ProductResult): ModelResult[] {
  return [...product.modelos].sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99));
}

function ModelsTable({ product }: { product: ProductResult }) {
  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10 text-right">#</TableHead>
            <TableHead>Modelo</TableHead>
            <TableHead>Família</TableHead>
            <TableHead className="text-right">MAPE</TableHead>
            <TableHead className="text-right">MAD</TableHead>
            <TableHead className="text-right">RMSE</TableHead>
            <TableHead className="text-right">MSE</TableHead>
            <TableHead className="text-right">MPE</TableHead>
            <TableHead className="text-right">Acurácia</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rankedModels(product).map((model) => (
            <TableRow key={model.modelo} className={cn(model.vencedor && "bg-primary/5 font-medium")}>
              <TableCell className="text-right tabular-nums">{model.rank ?? "–"}</TableCell>
              <TableCell>
                <div className="flex flex-col gap-1">
                  <span className="flex items-center gap-2">
                    {model.label}
                    {model.vencedor && (
                      <Badge>
                        <TrophyIcon data-icon="inline-start" />
                        Vencedor
                      </Badge>
                    )}
                  </span>
                  {model.aplicavel === false && (
                    <span className="text-xs font-normal text-muted-foreground">
                      Não aplicável: {model.motivo}
                    </span>
                  )}
                  {model.n_zeros > 0 && (
                    <span className="text-xs font-normal text-muted-foreground">
                      {model.n_zeros} {model.n_zeros === 1 ? "mês" : "meses"} com venda zero
                      ignorado(s) no MAPE e no MPE
                    </span>
                  )}
                </div>
              </TableCell>
              <TableCell>{FAMILY_LABEL[model.familia]}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtPct(model.mape)}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtNumber(model.mad, 2)}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtNumber(model.rmse, 2)}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtNumber(model.mse, 1)}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtPct(model.mpe)}</TableCell>
              <TableCell className="text-right tabular-nums">
                {fmtPct(model.mape == null ? null : Math.max(0, 100 - model.mape))}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
function ModelFormulas({ product }: { product: ProductResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Equações dos modelos</CardTitle>
        <CardDescription>
          Fórmulas LaTeX renderizadas localmente para cada ajuste. Os coeficientes são estimados com
          os dados do produto selecionado.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {rankedModels(product).map((model) => {
            const formula = MODEL_FORMULAS[model.modelo];
            return (
              <section key={model.modelo} className="flex flex-col gap-2 rounded-lg border p-3">
                <div className="flex items-center gap-2">
                  <h2 className="font-medium">{model.label}</h2>
                  {model.vencedor && <Badge variant="secondary">Vencedor</Badge>}
                </div>
                <div className="overflow-x-auto rounded-md bg-muted px-2 py-1.5 text-foreground">
                  <BlockMath math={formula.equation} />
                </div>
                <p className="text-xs leading-relaxed text-muted-foreground">{formula.note}</p>
              </section>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}


function HoldoutChart({ product }: { product: ProductResult }) {
  const models = rankedModels(product).filter((model) => model.aplicavel);
  const [visible, setVisible] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(models.map((model) => [model.modelo, (model.rank ?? 99) <= 3])),
  );
  const holdoutStart = product.janela.holdout_inicio;
  const data = product.observado
    .filter((point) => point.periodo >= holdoutStart)
    .map((point) => {
      const row: Record<string, number | string> = { periodo: point.periodo, real: point.valor };
      for (const model of models) {
        const predicted = model.holdout_previsto.find((item) => item.periodo === point.periodo);
        if (predicted != null) row[model.modelo] = predicted.valor;
      }
      return row;
    });
  const config: ChartConfig = { real: { label: "Real (vendido)", color: "var(--foreground)" } };
  models.forEach((model, index) => {
    config[model.modelo] = { label: model.label, color: SERIES_COLORS[index % SERIES_COLORS.length] };
  });
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Legenda: ligar ou desligar modelos">
        {models.map((model) => (
          <button
            key={model.modelo}
            type="button"
            aria-pressed={visible[model.modelo] === true}
            onClick={() =>
              setVisible((current) => ({ ...current, [model.modelo]: current[model.modelo] !== true }))
            }
            className={cn(
              "flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs",
              visible[model.modelo] !== true && "opacity-40",
            )}
          >
            <span
              className="size-2.5 rounded-sm"
              style={{ backgroundColor: config[model.modelo].color }}
            />
            {model.label}
          </button>
        ))}
      </div>
      <ChartContainer config={config} className="aspect-auto h-72 w-full">
        <LineChart data={data} margin={{ left: 4, right: 12 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="periodo" tickFormatter={monthLabel} tickLine={false} />
          <YAxis width={44} tickLine={false} axisLine={false} />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(_, payload) => monthLabel(String(payload?.[0]?.payload?.periodo))}
              />
            }
          />
          <Line
            dataKey="real"
            stroke="var(--color-real)"
            strokeWidth={2.5}
            dot
            isAnimationActive={false}
          />
          {models
            .filter((model) => visible[model.modelo] === true)
            .map((model) => (
              <Line
                key={model.modelo}
                dataKey={model.modelo}
                stroke={`var(--color-${model.modelo})`}
                strokeDasharray={model.vencedor ? undefined : "5 4"}
                strokeWidth={model.vencedor ? 2.5 : 1.5}
                dot={false}
                isAnimationActive={false}
              />
            ))}
        </LineChart>
      </ChartContainer>
    </div>
  );
}

export default function ModelsPage() {
  const overview = useOverview();
  const runId = overview.data?.ativo?.run_id ?? null;
  const run = useRun(runId);
  const [selected, setSelected] = useState<string | null>(null);
  const result = run.data?.resultado ?? null;
  if (result == null) {
    const noActiveRun = overview.data != null && overview.data.ativo == null;
    const error = noActiveRun
      ? new ApiError(404, "sem_treino_ativo", "Treinamento inicial em andamento", [])
      : (overview.error ?? run.error);
    return <QueryState error={error} onRetry={() => void overview.refetch()} />;
  }
  const product = result.produtos.find((item) => item.produto === selected) ?? result.produtos[0];
  const janela = product.janela;
  return (
    <>
      <PageHeader
        title="Comparativo de modelos"
        description={`${product.modelos.length} modelos competem por produto no mesmo período de teste; vence o menor erro.`}
      >
        <Field className="w-64">
          <FieldLabel htmlFor="produto">Produto</FieldLabel>
          <Select value={product.produto} onValueChange={setSelected}>
            <SelectTrigger id="produto" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {result.produtos.map((item) => (
                  <SelectItem key={item.produto} value={item.produto}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </Field>
      </PageHeader>
      <Card>
        <CardHeader>
          <CardTitle>{product.label}</CardTitle>
          <CardDescription>
            Treino até {monthNumeric(janela.treino_fim)} · Teste{" "}
            {periodRange(janela.holdout_inicio, janela.holdout_fim)}
          </CardDescription>
          <CardDescription>Critério: {CRITERION_TEXT}</CardDescription>
        </CardHeader>
        <CardContent>
          <ModelsTable product={product} />
        </CardContent>
      </Card>
      <ModelFormulas product={product} />
      <Card>
        <CardHeader>
          <CardTitle>Real × previsto no período de teste</CardTitle>
          <CardDescription>Clique na legenda para ligar ou desligar modelos.</CardDescription>
        </CardHeader>
        <CardContent>
          <HoldoutChart key={product.produto} product={product} />
        </CardContent>
      </Card>
    </>
  );
}
