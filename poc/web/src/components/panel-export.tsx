"use client";

import { FileDownIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { type PlanRead, useRun } from "@/lib/api";
import { exportPlan } from "@/lib/spreadsheet";

/** Exporta exatamente o que o painel mostra (POC-37). */
export function PanelExport({ plan }: { plan: PlanRead }) {
  const run = useRun(plan.run_id);
  const result = run.data?.resultado ?? null;
  return (
    <Button
      variant="outline"
      disabled={result == null}
      onClick={() => result != null && exportPlan(plan, result)}
    >
      <FileDownIcon data-icon="inline-start" />
      Exportar para Excel
    </Button>
  );
}
