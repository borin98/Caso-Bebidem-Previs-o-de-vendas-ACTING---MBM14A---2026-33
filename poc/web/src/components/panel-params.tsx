"use client";

import { useState } from "react";
import { toast } from "sonner";

import { LeadTimeLabel } from "@/components/lead-time-help";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  type Parameters,
  type PlanRead,
  type ServiceLevel,
  errorMessage,
  useSaveSettings,
} from "@/lib/api";
import { SERVICE_LEVEL_LABEL } from "@/lib/format";
import { type NumberRule, numberText, parseNumberInput } from "@/lib/number-input";

function NumberParam({
  id,
  label,
  value,
  rule,
  onCommit,
}: {
  id: string;
  label: React.ReactNode;
  value: number;
  rule: NumberRule;
  onCommit: (value: number) => void;
}) {
  const [text, setText] = useState(numberText(value));
  const parsed = parseNumberInput(text, rule);
  const change = (next: string) => {
    setText(next);
    const result = parseNumberInput(next, rule);
    if (result.error != null || result.value == null || result.value === value) return;
    onCommit(result.value);
  };
  return (
    <Field data-invalid={parsed.error != null}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Input
        id={id}
        inputMode="decimal"
        value={text}
        aria-invalid={parsed.error != null}
        onChange={(event) => change(event.target.value)}
      />
      {parsed.error != null && <FieldError>{parsed.error} · mantido o último valor válido</FieldError>}
    </Field>
  );
}

/** Parâmetros de reposição (POC-26): recalculam o plano sem novo treino e viram padrão. */
export function PanelParams({ plan }: { plan: PlanRead }) {
  const save = useSaveSettings();
  const params = plan.parametros;
  const commit = (patch: Partial<Parameters>) =>
    save.mutate(
      { parametros: { ...params, ...patch } },
      { onError: (error) => toast.error(errorMessage(error)) },
    );
  return (
    <Card>
      <CardHeader>
        <CardTitle>Parâmetros de reposição</CardTitle>
        <CardDescription>
          Alterações recalculam o plano na hora, sem novo treino, e ficam salvas como padrão.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <FieldGroup className="grid gap-4 md:grid-cols-4">
          <NumberParam
            id="horizonte"
            label={`Horizonte de cobertura (1–${plan.horizonte_max} meses)`}
            value={params.horizonte_meses}
            rule={{ min: 1, max: plan.horizonte_max, integer: true }}
            onCommit={(value) => commit({ horizonte_meses: value })}
          />
          <NumberParam
            id="lead-time"
            label={<LeadTimeLabel suffix=" padrão (meses)" />}
            value={params.lead_time_padrao}
            rule={{ min: 0, max: 12, step: 0.5 }}
            onCommit={(value) => commit({ lead_time_padrao: value })}
          />
          <Field>
            <FieldLabel htmlFor="nivel-servico">Nível de serviço</FieldLabel>
            <Select
              value={params.nivel_servico}
              onValueChange={(value) => commit({ nivel_servico: value as ServiceLevel })}
            >
              <SelectTrigger id="nivel-servico" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {Object.entries(SERVICE_LEVEL_LABEL).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </Field>
          <NumberParam
            id="multiplo"
            label="Múltiplo de compra padrão"
            value={params.multiplo_padrao}
            rule={{ min: 1, integer: true }}
            onCommit={(value) => commit({ multiplo_padrao: value })}
          />
        </FieldGroup>
      </CardContent>
    </Card>
  );
}
