"use client";

import { InfoIcon } from "lucide-react";
import { useState } from "react";

import { DemoPositionsBadge } from "@/components/demo-positions-badge";
import { PageHeader } from "@/components/page-header";
import { PanelExport } from "@/components/panel-export";
import { PanelKpis } from "@/components/panel-kpis";
import { PanelParams } from "@/components/panel-params";
import { StockDialog } from "@/components/panel-stock-dialog";
import { ProductDetail } from "@/components/product-detail";
import { PanelTable } from "@/components/panel-table";
import { QueryState } from "@/components/query-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { usePlan } from "@/lib/api";
import { monthLabel } from "@/lib/format";

export default function PanelPage() {
  const plan = usePlan();
  const [selected, setSelected] = useState<string | null>(null);
  if (plan.data == null) return <QueryState error={plan.error} onRetry={() => void plan.refetch()} />;
  const data = plan.data;
  return (
    <>
      <PageHeader
        title="Painel de reposição"
        description={`Previsão a partir de ${monthLabel(data.produtos[0]?.previsao[0]?.periodo ?? data.ultimo_observado)} · último mês observado ${monthLabel(data.ultimo_observado)}`}
      >
        <div className="flex flex-wrap items-center gap-2">
          {data.posicoes_demo && <DemoPositionsBadge />}
          <StockDialog plan={data} />
          <PanelExport plan={data} />
        </div>
      </PageHeader>
      <PanelKpis plan={data} />
      <PanelParams plan={data} />
      {data.avisos.length > 0 && (
        <Alert>
          <InfoIcon />
          <AlertTitle>Avisos</AlertTitle>
          <AlertDescription>
            <ul className="list-disc pl-4">
              {data.avisos.map((aviso) => (
                <li key={aviso}>{aviso}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}
      <PanelTable plan={data} onSelect={setSelected} />
      <ProductDetail plan={data} produto={selected} onClose={() => setSelected(null)} />
    </>
  );
}
