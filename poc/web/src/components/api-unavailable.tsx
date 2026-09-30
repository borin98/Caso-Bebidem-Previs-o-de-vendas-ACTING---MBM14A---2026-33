"use client";

import { RefreshCwIcon, ServerOffIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

/** Aviso de POC-32: substitui o conteúdo para não exibir números antigos como atuais. */
export function ApiUnavailable({ onRetry }: { onRetry: () => void }) {
  return (
    <Alert variant="destructive" className="max-w-xl">
      <ServerOffIcon />
      <AlertTitle>Serviço de previsão indisponível</AlertTitle>
      <AlertDescription className="flex flex-col items-start gap-3">
        <span>Não foi possível falar com a API de previsão. Verifique se o serviço está no ar.</span>
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCwIcon data-icon="inline-start" />
          Tentar novamente
        </Button>
      </AlertDescription>
    </Alert>
  );
}
