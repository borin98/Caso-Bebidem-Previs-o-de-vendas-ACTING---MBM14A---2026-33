"use client";

import { useState } from "react";
import { toast } from "sonner";

import { CloseMonth } from "@/components/close-month";
import { DataImport } from "@/components/data-import";
import { EditGrid } from "@/components/edit-grid";
import { PageHeader } from "@/components/page-header";
import { type TrackedRun, RunTracker } from "@/components/run-tracker";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  type RunMeta,
  errorMessage,
  isTraining,
  useOverview,
  useRun,
  useStartRun,
} from "@/lib/api";

export default function DataPage() {
  const overview = useOverview();
  const activeRun = useRun(overview.data?.ativo?.run_id ?? null);
  const startRun = useStartRun();
  const [tracked, setTracked] = useState<TrackedRun | null>(null);
  const training = isTraining(overview.data?.treino_em_andamento) || startRun.isPending;
  const activeDatasetId = activeRun.data?.dataset_id ?? null;

  const track = (run: RunMeta | null) => {
    if (run == null) return;
    setTracked({
      runId: run.id,
      baseRunId: overview.data?.ativo?.run_id ?? null,
      datasetId: run.dataset_id,
      horizonYears: run.horizon_years,
    });
  };
  const retry = () => {
    if (tracked == null) return;
    startRun.mutate(
      { dataset_id: tracked.datasetId, horizon_years: tracked.horizonYears },
      {
        onSuccess: (run) => setTracked({ ...tracked, runId: run.id }),
        onError: (error) => toast.error(errorMessage(error)),
      },
    );
  };

  return (
    <>
      <PageHeader
        title="Dados"
        description="Carregue vendas, feche o mês ou corrija a grade; cada mudança gera uma versão de dados."
      />
      {tracked != null && <RunTracker tracked={tracked} onRetry={retry} retryDisabled={training} />}
      <Tabs defaultValue="importar">
        <TabsList>
          <TabsTrigger value="importar">Importar</TabsTrigger>
          <TabsTrigger value="fechar">Fechar mês</TabsTrigger>
          <TabsTrigger value="grade">Grade</TabsTrigger>
        </TabsList>
        <TabsContent value="importar">
          <DataImport disabled={training} onRunStarted={track} />
        </TabsContent>
        <TabsContent value="fechar">
          <CloseMonth
            key={activeDatasetId ?? "sem-versao"}
            datasetId={activeDatasetId}
            disabled={training}
            onRunStarted={track}
          />
        </TabsContent>
        <TabsContent value="grade">
          <EditGrid
            key={activeDatasetId ?? "sem-versao"}
            datasetId={activeDatasetId}
            disabled={training}
            onRunStarted={track}
          />
        </TabsContent>
      </Tabs>
    </>
  );
}
