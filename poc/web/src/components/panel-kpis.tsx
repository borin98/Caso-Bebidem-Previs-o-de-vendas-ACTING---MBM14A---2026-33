import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { PlanRead } from "@/lib/api";
import { fmtNumber, fmtPct } from "@/lib/format";

/** Os 5 KPIs do painel (POC-25): somam todos os produtos, independentemente do filtro. */
export function PanelKpis({ plan }: { plan: PlanRead }) {
  const { kpis } = plan;
  const horizon = plan.parametros.horizonte_meses;
  const items = [
    { label: "produtos analisados", value: fmtNumber(kpis.produtos) },
    {
      label: `unidades previstas nos próximos ${horizon} ${horizon > 1 ? "meses" : "mês"}`,
      value: fmtNumber(kpis.unidades_previstas_horizonte),
    },
    { label: "produtos com ruptura prevista", value: fmtNumber(kpis.produtos_ruptura) },
    {
      label: `unidades a comprar (${kpis.produtos_comprar} ${kpis.produtos_comprar === 1 ? "produto" : "produtos"})`,
      value: fmtNumber(kpis.unidades_comprar),
    },
    { label: "acurácia média dos modelos em uso", value: fmtPct(kpis.acuracia_media) },
  ];
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
      {items.map((item) => (
        <Card key={item.label} size="sm">
          <CardHeader>
            <CardTitle className="text-2xl tabular-nums">{item.value}</CardTitle>
            <CardDescription>{item.label}</CardDescription>
          </CardHeader>
        </Card>
      ))}
    </div>
  );
}
