"use client";

import { Area, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from "recharts";

import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import type { ProductPlan } from "@/lib/api";
import { fmtNumber, monthLabel } from "@/lib/format";
import { BAND_LEGEND } from "@/lib/help";

interface Row {
  periodo: string;
  vendido?: number;
  teste?: number;
  previsao?: number;
  faixa?: [number, number];
  estoque?: number;
  ss?: number;
  capacidade?: number;
}

const CONFIG = {
  vendido: { label: "Vendido", color: "var(--foreground)" },
  teste: { label: "Previsão no período de teste", color: "var(--chart-5)" },
  previsao: { label: "Previsão", color: "var(--chart-1)" },
  faixa: { label: BAND_LEGEND, color: "var(--chart-1)" },
  estoque: { label: "Estoque projetado", color: "var(--chart-3)" },
  ss: { label: "Estoque de segurança", color: "var(--chart-4)" },
  capacidade: { label: "Capacidade", color: "var(--chart-2)" },
} satisfies ChartConfig;

function buildRows(product: ProductPlan, horizon: number): Row[] {
  const rows = new Map<string, Row>();
  const at = (periodo: string): Row => {
    const existing = rows.get(periodo);
    if (existing != null) return existing;
    const created: Row = { periodo };
    rows.set(periodo, created);
    return created;
  };
  for (const point of product.observado) at(point.periodo).vendido = point.valor;
  for (const point of product.holdout_previsto) at(point.periodo).teste = point.valor;
  const last = product.observado.at(-1);
  if (last != null) {
    // Liga a previsão e o estoque ao último mês observado, sem lacuna visual.
    at(last.periodo).previsao = last.valor;
    at(last.periodo).estoque = product.disponivel;
  }
  const futureCount = Math.min(product.previsao.length, Math.max(12, horizon));
  for (const point of product.previsao.slice(0, futureCount)) {
    const row = at(point.periodo);
    row.previsao = point.valor;
    row.faixa = [point.faixa_min, point.faixa_max];
  }
  for (const point of product.projecao) {
    const row = at(point.periodo);
    row.estoque = point.final;
    row.ss = product.estoque_seguranca;
    if (product.capacidade != null) row.capacidade = product.capacidade;
  }
  return [...rows.values()];
}

/** Vendido, teste, previsão com faixa ±MAD, estoque projetado, SS e capacidade (POC-28). */
export function ForecastChart({ product, horizon }: { product: ProductPlan; horizon: number }) {
  const data = buildRows(product, horizon);
  return (
    <ChartContainer config={CONFIG} className="aspect-auto h-80 w-full">
      <ComposedChart data={data} margin={{ left: 4, right: 12 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="periodo" tickFormatter={monthLabel} minTickGap={24} tickLine={false} />
        <YAxis width={44} tickLine={false} axisLine={false} />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(_, payload) => monthLabel(String(payload?.[0]?.payload?.periodo))}
              formatter={(value, name) => (
                <div className="flex w-full justify-between gap-4">
                  <span className="text-muted-foreground">
                    {CONFIG[name as keyof typeof CONFIG]?.label ?? name}
                  </span>
                  <span className="font-mono tabular-nums">
                    {Array.isArray(value)
                      ? `${fmtNumber(Number(value[0]))}–${fmtNumber(Number(value[1]))}`
                      : fmtNumber(Number(value))}
                  </span>
                </div>
              )}
            />
          }
        />
        <ChartLegend content={<ChartLegendContent className="flex-wrap" />} />
        <Area
          dataKey="faixa"
          type="monotone"
          fill="var(--color-faixa)"
          fillOpacity={0.15}
          stroke="none"
          isAnimationActive={false}
        />
        <Line dataKey="vendido" stroke="var(--color-vendido)" dot={false} strokeWidth={1.5} isAnimationActive={false} />
        <Line
          dataKey="teste"
          stroke="var(--color-teste)"
          strokeDasharray="5 4"
          dot={false}
          isAnimationActive={false}
        />
        <Line dataKey="previsao" stroke="var(--color-previsao)" dot={false} strokeWidth={2.5} isAnimationActive={false} />
        <Line dataKey="estoque" stroke="var(--color-estoque)" dot={false} strokeWidth={2} isAnimationActive={false} />
        <Line
          dataKey="ss"
          stroke="var(--color-ss)"
          strokeDasharray="2 3"
          dot={false}
          isAnimationActive={false}
        />
        {product.capacidade != null && (
          <Line
            dataKey="capacidade"
            stroke="var(--color-capacidade)"
            strokeDasharray="6 3"
            dot={false}
            isAnimationActive={false}
          />
        )}
      </ComposedChart>
    </ChartContainer>
  );
}
