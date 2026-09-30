"use client";

import { WarehouseIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { DemoPositionsBadge } from "@/components/demo-positions-badge";
import { LeadTimeLabel } from "@/components/lead-time-help";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { type PlanRead, type Position, errorMessage, useSaveSettings, useSettings } from "@/lib/api";
import { LEAD_TIME_HELP } from "@/lib/help";
import { type NumberRule, numberText, parseNumberInput } from "@/lib/number-input";

type PositionField = keyof Position;
type Draft = Record<string, Record<PositionField, string>>;

const FIELDS: { key: PositionField; label: React.ReactNode; hint: string; rule: NumberRule }[] = [
  { key: "estoque", label: "Estoque atual", hint: "vazio = zero", rule: { min: 0, optional: true } },
  { key: "a_receber", label: "A receber", hint: "vazio = zero", rule: { min: 0, optional: true } },
  {
    key: "lead_time",
    label: <LeadTimeLabel suffix=" (meses)" />,
    hint: LEAD_TIME_HELP,
    rule: { min: 0, max: 12, optional: true },
  },
  {
    key: "multiplo",
    label: "Múltiplo de compra",
    hint: "vazio = padrão do painel",
    rule: { min: 1, optional: true },
  },
  {
    key: "capacidade",
    label: "Capacidade de armazenagem",
    hint: "unidades; vazio = sem limite",
    rule: { min: 0, optional: true },
  },
];

/** "Estoque e capacidade" (POC-30): edita posições por produto e recalcula sem re-treino. */
export function StockDialog({ plan }: { plan: PlanRead }) {
  const settings = useSettings();
  const save = useSaveSettings();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Draft>({});
  const start = (next: boolean) => {
    setOpen(next);
    if (next === false) return;
    const positions = settings.data?.posicoes ?? {};
    const initial: Draft = {};
    for (const product of plan.produtos) {
      const position = positions[product.produto];
      initial[product.produto] = {
        estoque: numberText(position?.estoque),
        a_receber: numberText(position?.a_receber),
        lead_time: numberText(position?.lead_time),
        multiplo: numberText(position?.multiplo),
        capacidade: numberText(position?.capacidade),
      };
    }
    setDraft(initial);
  };
  const parsed = (product: string, field: (typeof FIELDS)[number]) =>
    parseNumberInput(draft[product]?.[field.key] ?? "", field.rule);
  const hasErrors = plan.produtos.some((product) =>
    FIELDS.some((field) => parsed(product.produto, field).error != null),
  );
  const submit = () => {
    const posicoes: Record<string, Position> = {};
    for (const product of plan.produtos) {
      const values = Object.fromEntries(
        FIELDS.map((field) => [field.key, parsed(product.produto, field).value]),
      ) as unknown as Position;
      posicoes[product.produto] = values;
    }
    save.mutate(
      { posicoes },
      {
        onSuccess: () => {
          toast.success("Posições salvas; plano recalculado sem novo treino.");
          setOpen(false);
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    );
  };
  return (
    <Dialog open={open} onOpenChange={start}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <WarehouseIcon data-icon="inline-start" />
          Estoque e capacidade
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>Estoque e capacidade</DialogTitle>
          <DialogDescription>
            Posição de estoque por produto. Salvar recalcula o plano sem novo treino.
          </DialogDescription>
          {plan.posicoes_demo && <DemoPositionsBadge />}
        </DialogHeader>
        <div className="flex flex-col gap-6">
          {plan.produtos.map((product) => (
            <FieldSet key={product.produto}>
              <FieldLegend>{product.label}</FieldLegend>
              <div className="grid gap-4 md:grid-cols-5">
                {FIELDS.map((field) => {
                  const id = `${product.produto}-${field.key}`;
                  const result = parsed(product.produto, field);
                  return (
                    <Field key={field.key} data-invalid={result.error != null}>
                      <FieldLabel htmlFor={id}>{field.label}</FieldLabel>
                      <Input
                        id={id}
                        inputMode="decimal"
                        aria-invalid={result.error != null}
                        value={draft[product.produto]?.[field.key] ?? ""}
                        onChange={(event) =>
                          setDraft((current) => ({
                            ...current,
                            [product.produto]: {
                              ...current[product.produto],
                              [field.key]: event.target.value,
                            },
                          }))
                        }
                      />
                      {result.error != null && <FieldError>{result.error}</FieldError>}
                      <FieldDescription>{field.hint}</FieldDescription>
                    </Field>
                  );
                })}
              </div>
            </FieldSet>
          ))}
        </div>
        <DialogFooter>
          <Button onClick={submit} disabled={hasErrors || save.isPending}>
            Salvar posições
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
