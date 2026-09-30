"use client";

import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const OPTIONS = [1, 2, 3];

/** Horizonte de treino em anos (POC-39): o treino prevê 12 × h meses. */
export function HorizonSelect({
  id,
  value,
  onChange,
}: {
  id: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <Field className="w-56">
      <FieldLabel htmlFor={id}>Horizonte do treino</FieldLabel>
      <Select value={String(value)} onValueChange={(next) => onChange(Number(next))}>
        <SelectTrigger id={id} className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            {OPTIONS.map((years) => (
              <SelectItem key={years} value={String(years)}>
                {years} {years === 1 ? "ano" : "anos"} ({years * 12} meses)
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
      <FieldDescription>Meses previstos a partir do mês seguinte ao último observado.</FieldDescription>
    </Field>
  );
}
