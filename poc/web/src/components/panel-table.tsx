"use client";

import { SearchIcon } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { PlanRead, ProductPlan } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  SITUATION_LABEL,
  SITUATION_VARIANT,
  fmtNumber,
  fmtPct,
  normalizeText,
} from "@/lib/format";

/** Barra de cobertura: disponível ÷ (demanda + SS); marca onde a demanda do horizonte termina. */
function CoverageBar({ row }: { row: ProductPlan }) {
  const total = row.demanda_horizonte + row.estoque_seguranca;
  if (row.demanda_horizonte <= 0 || total <= 0) {
    return <div className="h-2 w-24 rounded-full bg-muted" />;
  }
  const filled = Math.min(100, (row.disponivel / total) * 100);
  const marker = Math.min(100, (row.demanda_horizonte / total) * 100);
  return (
    <div
      className="relative h-2 w-24 rounded-full bg-muted"
      title={`Estoque cobre ${fmtNumber(filled)}% da demanda + segurança`}
    >
      <div
        className={cn("h-2 rounded-full", filled < marker ? "bg-destructive" : "bg-primary")}
        style={{ width: `${filled}%` }}
      />
      <div className="absolute -top-0.5 h-3 w-0.5 bg-foreground" style={{ left: `${marker}%` }} />
    </div>
  );
}

export function PanelTable({
  plan,
  onSelect,
}: {
  plan: PlanRead;
  onSelect: (produto: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [onlyNeed, setOnlyNeed] = useState(false);
  const needle = normalizeText(query);
  const rows = plan.produtos
    .filter((row) => normalizeText(row.label).includes(needle))
    .filter((row) => onlyNeed === false || row.necessidade > 0);
  const horizon = plan.parametros.horizonte_meses;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative w-64">
          <SearchIcon className="absolute top-2.5 left-2.5 size-4 text-muted-foreground" />
          <Input
            aria-label="Filtrar produtos por nome"
            placeholder="Filtrar por nome"
            className="pl-8"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <Field orientation="horizontal" className="w-auto">
          <Checkbox
            id="so-necessidade"
            checked={onlyNeed}
            onCheckedChange={(value) => setOnlyNeed(value === true)}
          />
          <FieldLabel htmlFor="so-necessidade">Só com necessidade</FieldLabel>
        </Field>
      </div>
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Produto</TableHead>
              <TableHead>Modelo em uso</TableHead>
              <TableHead className="text-right">MAPE</TableHead>
              <TableHead className="text-right">Previsão {horizon}m</TableHead>
              <TableHead className="text-right">Estoque + a receber</TableHead>
              <TableHead>Cobertura</TableHead>
              <TableHead className="text-right">Meses cobertos</TableHead>
              <TableHead className="text-right">Est. segurança</TableHead>
              <TableHead className="text-right">Comprar</TableHead>
              <TableHead>Comprar até</TableHead>
              <TableHead>Situação</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={11} className="text-muted-foreground">
                  Nenhum produto corresponde ao filtro
                </TableCell>
              </TableRow>
            )}
            {rows.map((row) => (
              <TableRow
                key={row.produto}
                tabIndex={0}
                className="cursor-pointer"
                onClick={() => onSelect(row.produto)}
                onKeyDown={(event) => event.key === "Enter" && onSelect(row.produto)}
              >
                <TableCell className="font-medium">
                  <div className="flex flex-col gap-1">
                    {row.label}
                    {row.estoque_informado === false && (
                      <span className="text-xs font-normal text-muted-foreground">
                        sem estoque informado, considerado zero
                      </span>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap items-center gap-1">
                    {row.modelo_label}
                    {row.escolha_manual && <Badge variant="outline">Escolha manual</Badge>}
                  </div>
                </TableCell>
                <TableCell className="text-right tabular-nums">{fmtPct(row.mape)}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {fmtNumber(row.demanda_horizonte)}
                </TableCell>
                <TableCell className="text-right tabular-nums">{fmtNumber(row.disponivel)}</TableCell>
                <TableCell>
                  <CoverageBar row={row} />
                </TableCell>
                <TableCell className="text-right tabular-nums">{row.cobertura_texto}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {fmtNumber(row.estoque_seguranca)}
                </TableCell>
                <TableCell className="text-right font-semibold tabular-nums">
                  {row.necessidade > 0 ? fmtNumber(row.necessidade) : "–"}
                </TableCell>
                <TableCell>{row.comprar_ate_texto}</TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    <Badge variant={SITUATION_VARIANT[row.situacao]}>
                      {SITUATION_LABEL[row.situacao]}
                    </Badge>
                    {row.excede_capacidade === true && (
                      <Badge variant="destructive">Excede capacidade</Badge>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
