"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { type RunMeta, keys, useOverview } from "@/lib/api";
import { STATUS_LABEL } from "@/lib/format";

export const TRAINING_LIMIT_S = 60;

/** Seconds since the run started (or was queued), refreshed every second (POC-31). */
export function useElapsedSeconds(run: RunMeta | null | undefined): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (run == null) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [run]);
  if (run == null) return 0;
  const start = Date.parse(run.iniciado_em ?? run.criado_em);
  return Math.max(0, Math.round((now - start) / 1000));
}

export function TrainingProgress({ run }: { run: RunMeta }) {
  const elapsed = useElapsedSeconds(run);
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2 text-sm">
        <Spinner />
        <span className="font-medium">Treinamento: {STATUS_LABEL[run.status]}</span>
      </div>
      <Progress value={Math.min(100, (elapsed / TRAINING_LIMIT_S) * 100)} />
      <span className="text-xs text-muted-foreground">
        {elapsed} s decorridos · máx. {TRAINING_LIMIT_S} s
      </span>
    </div>
  );
}

/** Sidebar indicator; refreshes every query when a run starts, ends or the active run changes. */
export function TrainingStatus() {
  const overview = useOverview();
  const client = useQueryClient();
  const running = overview.data?.treino_em_andamento ?? null;
  const signature = `${overview.data?.ativo?.run_id ?? ""}|${running?.id ?? ""}`;
  const previous = useRef(signature);
  useEffect(() => {
    if (previous.current === signature) return;
    previous.current = signature;
    void client.invalidateQueries({ predicate: (query) => query.queryKey[0] !== keys.overview[0] });
  }, [signature, client]);
  if (running == null) return null;
  return (
    <div className="rounded-md border bg-background p-3">
      <TrainingProgress run={running} />
    </div>
  );
}
