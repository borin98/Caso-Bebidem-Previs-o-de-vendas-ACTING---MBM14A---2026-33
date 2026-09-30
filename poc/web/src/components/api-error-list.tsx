"use client";

import { CircleAlertIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ApiError } from "@/lib/api";

/** Mensagem e detalhes (até 20 + "… e mais N") de um erro 409/422 da API. */
export function ApiErrorList({ error }: { error: unknown }) {
  if (error == null) return null;
  const title = error instanceof Error ? error.message : "Erro inesperado";
  const details = error instanceof ApiError ? error.detalhes : [];
  return (
    <Alert variant="destructive">
      <CircleAlertIcon />
      <AlertTitle>{title}</AlertTitle>
      {details.length > 0 && (
        <AlertDescription>
          <ul className="list-disc pl-4">
            {details.map((detail) => (
              <li key={detail}>{detail}</li>
            ))}
          </ul>
        </AlertDescription>
      )}
    </Alert>
  );
}
