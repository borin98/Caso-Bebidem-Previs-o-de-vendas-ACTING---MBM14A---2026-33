"use client";

import { ApiUnavailable } from "@/components/api-unavailable";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiUnavailable as ApiUnavailableError, type OverviewRead, useOverview } from "@/lib/api";
import { fmtDateTime, fmtNumber, fmtPct, periodRange } from "@/lib/format";

type Active = NonNullable<OverviewRead["ativo"]>;

const NUMBERS: { label: string; value: (active: Active) => string }[] = [
  { label: "modelos avaliados por produto", value: (active) => fmtNumber(active.n_modelos) },
  { label: "acurácia média dos vencedores", value: (active) => fmtPct(active.acuracia_media) },
  {
    label: "meses de histórico",
    value: (active) => fmtNumber(active.meses_historico),
  },
  { label: "produtos planejados", value: (active) => fmtNumber(active.n_produtos) },
  { label: "último treino", value: (active) => fmtDateTime(active.concluido_em) },
];

/** Faixa de números da landing: todo valor vem de GET /api/v1/overview (POC-23). */
export function LandingNumbers() {
  const overview = useOverview();
  if (overview.error instanceof ApiUnavailableError) {
    return <ApiUnavailable onRetry={() => void overview.refetch()} />;
  }
  const active = overview.data?.ativo ?? null;
  return (
    <div className="flex flex-col gap-3">
      <dl className="grid grid-cols-2 gap-4 md:grid-cols-5">
        {NUMBERS.map((item) => (
          <div key={item.label} className="flex flex-col gap-1 rounded-lg border bg-card p-4">
            <dt className="order-2 text-sm text-muted-foreground">{item.label}</dt>
            <dd className="order-1 text-2xl font-semibold tabular-nums">
              {active == null && <Skeleton className="h-8 w-20" />}
              {active != null && item.value(active)}
            </dd>
          </div>
        ))}
      </dl>
      {active == null && (
        <p className="text-sm text-muted-foreground">Treinamento inicial em andamento</p>
      )}
      {active != null && (
        <p className="text-xs text-muted-foreground">
          Histórico {periodRange(active.periodo_inicio, active.periodo_fim)} · acurácia medida no
          teste {periodRange(active.holdout_inicio, active.holdout_fim)}.
        </p>
      )}
    </div>
  );
}
