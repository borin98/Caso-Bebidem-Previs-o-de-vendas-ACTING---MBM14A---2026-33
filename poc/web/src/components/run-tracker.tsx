"use client";

import { CircleXIcon, RefreshCwIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { TrainingProgress } from "@/components/training-status";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRun } from "@/lib/api";
import { fmtNumber } from "@/lib/format";

export interface TrackedRun {
  runId: string;
  /** Active run when the training started: the "antes" of the comparison. */
  baseRunId: string | null;
  datasetId: string;
  horizonYears: number;
}

/** Progresso do treino (POC-31): ao concluir leva ao antes×depois; ao falhar, "Tentar novamente". */
export function RunTracker({
  tracked,
  onRetry,
  retryDisabled,
}: {
  tracked: TrackedRun;
  onRetry: () => void;
  retryDisabled: boolean;
}) {
  const run = useRun(tracked.runId);
  const router = useRouter();
  const status = run.data?.status;
  useEffect(() => {
    if (status !== "concluido") return;
    if (tracked.baseRunId == null) {
      router.push("/app");
      return;
    }
    router.push(`/app/versoes?base=${tracked.baseRunId}&alvo=${tracked.runId}`);
  }, [status, tracked, router]);
  if (run.data == null) return <Skeleton className="h-24 w-full" />;
  if (run.data.status === "falhou") {
    return (
      <Alert variant="destructive">
        <CircleXIcon />
        <AlertTitle>O treino falhou</AlertTitle>
        <AlertDescription className="flex flex-col items-start gap-3">
          <span>{run.data.erro}</span>
          <Button variant="outline" size="sm" onClick={onRetry} disabled={retryDisabled}>
            <RefreshCwIcon data-icon="inline-start" />
            Tentar novamente
          </Button>
        </AlertDescription>
      </Alert>
    );
  }
  if (run.data.status === "concluido") {
    return (
      <Alert>
        <AlertTitle>Treino concluído em {fmtNumber(run.data.duracao_s, 1)} s</AlertTitle>
        <AlertDescription>Abrindo o comparativo antes × depois…</AlertDescription>
      </Alert>
    );
  }
  return (
    <Card>
      <CardContent>
        <TrainingProgress run={run.data} />
      </CardContent>
    </Card>
  );
}
