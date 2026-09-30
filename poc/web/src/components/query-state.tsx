"use client";

import { ApiUnavailable } from "@/components/api-unavailable";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { ApiError, ApiUnavailable as ApiUnavailableError } from "@/lib/api";

/**
 * Standard rendering for a query that has no data yet: API down (POC-32), no active run
 * ("Treinamento inicial em andamento"), other API error, or loading skeleton.
 */
export function QueryState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  if (error instanceof ApiUnavailableError) return <ApiUnavailable onRetry={onRetry} />;
  if (error instanceof ApiError && error.codigo === "sem_treino_ativo") {
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <Spinner />
          </EmptyMedia>
          <EmptyTitle>Treinamento inicial em andamento</EmptyTitle>
          <EmptyDescription>O painel aparece assim que o primeiro treino concluir.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  if (error != null) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Não foi possível carregar</AlertTitle>
        <AlertDescription>{error instanceof Error ? error.message : "Erro inesperado"}</AlertDescription>
      </Alert>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
