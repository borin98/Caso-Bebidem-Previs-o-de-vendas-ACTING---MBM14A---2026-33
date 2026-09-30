"use client";

import { CheckCircle2Icon } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { QueryState } from "@/components/query-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldLabel } from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { type RunRead, errorMessage, useActivate, useCompare, useRuns } from "@/lib/api";
import {
  ORIGIN_LABEL,
  STATUS_LABEL,
  fmtDateTime,
  fmtNumber,
  fmtPct,
  fmtSigned,
  monthLabel,
  periodRange,
} from "@/lib/format";

function RunsTable({ runs }: { runs: RunRead[] }) {
  const activate = useActivate();
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Data</TableHead>
            <TableHead>Origem dos dados</TableHead>
            <TableHead>Período dos dados</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Duração</TableHead>
            <TableHead>Vencedor por produto</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {runs.map((run) => (
            <TableRow key={run.id}>
              <TableCell className="whitespace-nowrap">{fmtDateTime(run.criado_em)}</TableCell>
              <TableCell>{ORIGIN_LABEL[run.dataset.origem]}</TableCell>
              <TableCell className="whitespace-nowrap">
                {periodRange(run.dataset.periodo_inicio, run.dataset.periodo_fim)}
              </TableCell>
              <TableCell>
                <div className="flex flex-col gap-1">
                  <Badge variant={run.status === "falhou" ? "destructive" : "secondary"}>
                    {STATUS_LABEL[run.status]}
                  </Badge>
                  {run.erro != null && <span className="text-xs text-destructive">{run.erro}</span>}
                </div>
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {run.duracao_s == null ? "–" : `${fmtNumber(run.duracao_s, 1)} s`}
              </TableCell>
              <TableCell>
                <ul className="text-xs">
                  {Object.entries(run.vencedores).map(([product, model]) => (
                    <li key={product}>
                      {product}: <span className="font-medium">{model}</span>
                    </li>
                  ))}
                </ul>
              </TableCell>
              <TableCell className="text-right">
                {run.ativo && (
                  <Badge>
                    <CheckCircle2Icon data-icon="inline-start" />
                    Ativa
                  </Badge>
                )}
                {run.ativo === false && run.status === "concluido" && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={activate.isPending}
                    onClick={() =>
                      activate.mutate(run.id, {
                        onSuccess: () => toast.success("Treino ativado: painel, modelos e landing atualizados"),
                        onError: (error) => toast.error(errorMessage(error)),
                      })
                    }
                  >
                    Ativar
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function RunSelect({
  id,
  label,
  value,
  runs,
  exclude,
  onChange,
}: {
  id: string;
  label: string;
  value: string | null;
  runs: RunRead[];
  exclude: string | null;
  onChange: (value: string) => void;
}) {
  return (
    <Field className="w-80">
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Select value={value ?? undefined} onValueChange={onChange}>
        <SelectTrigger id={id} className="w-full">
          <SelectValue placeholder="Escolha um treino concluído" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            {runs.map((run) => (
              <SelectItem key={run.id} value={run.id} disabled={run.id === exclude}>
                {fmtDateTime(run.criado_em)} · {ORIGIN_LABEL[run.dataset.origem]} ·{" "}
                {periodRange(run.dataset.periodo_inicio, run.dataset.periodo_fim)}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </Field>
  );
}

function Comparison({ base, target }: { base: string; target: string }) {
  const compare = useCompare(base, target);
  if (compare.error != null) {
    return <QueryState error={compare.error} onRetry={() => void compare.refetch()} />;
  }
  if (compare.data == null) return <Skeleton className="h-40 w-full" />;
  const data = compare.data;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-6 text-sm">
        <span>
          Meses adicionados:{" "}
          <span className="font-medium">
            {data.dados.meses_adicionados.length === 0
              ? "nenhum"
              : data.dados.meses_adicionados.map(monthLabel).join(", ")}
          </span>
        </span>
        <span>
          Células alteradas: <span className="font-medium">{data.dados.celulas_alteradas}</span>
        </span>
      </div>
      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Produto</TableHead>
              <TableHead>Vencedor antes</TableHead>
              <TableHead>Vencedor depois</TableHead>
              <TableHead className="text-right">MAPE antes</TableHead>
              <TableHead className="text-right">MAPE depois</TableHead>
              <TableHead className="text-right">Δ MAPE</TableHead>
              <TableHead className="text-right">12 meses antes</TableHead>
              <TableHead className="text-right">12 meses depois</TableHead>
              <TableHead className="text-right">Δ %</TableHead>
              <TableHead>Teste antes</TableHead>
              <TableHead>Teste depois</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.produtos.map((row) => (
              <TableRow key={row.produto}>
                <TableCell className="font-medium">{row.label}</TableCell>
                <TableCell>{row.vencedor_base}</TableCell>
                <TableCell>{row.vencedor_alvo}</TableCell>
                <TableCell className="text-right tabular-nums">{fmtPct(row.mape_base)}</TableCell>
                <TableCell className="text-right tabular-nums">{fmtPct(row.mape_alvo)}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {fmtSigned(row.delta_mape_pp, 1, " p.p.")}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {fmtNumber(row.soma12_base)}
                  <div className="text-xs text-muted-foreground">
                    {periodRange(row.periodo12_base[0], row.periodo12_base[1])}
                  </div>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {fmtNumber(row.soma12_alvo)}
                  <div className="text-xs text-muted-foreground">
                    {periodRange(row.periodo12_alvo[0], row.periodo12_alvo[1])}
                  </div>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {fmtSigned(row.delta_soma12_pct, 1, "%")}
                </TableCell>
                <TableCell className="whitespace-nowrap">
                  {periodRange(row.holdout_base[0], row.holdout_base[1])}
                </TableCell>
                <TableCell className="whitespace-nowrap">
                  {periodRange(row.holdout_alvo[0], row.holdout_alvo[1])}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

/** Versões (POC-21) e comparativo antes × depois (POC-22). */
export function VersionsView({ base, target }: { base: string | null; target: string | null }) {
  const runs = useRuns();
  const router = useRouter();
  if (runs.data == null) return <QueryState error={runs.error} onRetry={() => void runs.refetch()} />;
  const completed = runs.data.filter((run) => run.status === "concluido");
  const active = completed.find((run) => run.ativo) ?? null;
  const targetId = target ?? active?.id ?? null;
  const baseId = base ?? completed.find((run) => run.id !== targetId)?.id ?? null;
  const select = (next: { base?: string; alvo?: string }) => {
    const params = new URLSearchParams({ base: next.base ?? baseId ?? "", alvo: next.alvo ?? targetId ?? "" });
    router.replace(`/app/versoes?${params.toString()}`);
  };
  return (
    <>
      <PageHeader
        title="Versões"
        description="Cada treino guarda dados, métricas e previsão. Ative um treino anterior ou compare dois treinos."
      />
      <RunsTable runs={runs.data} />
      <Card>
        <CardHeader>
          <CardTitle>Comparativo antes × depois</CardTitle>
          <CardDescription>
            Δ MAPE em pontos percentuais (depois − antes); Δ % da soma dos 12 primeiros meses previstos.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-wrap gap-4">
            <RunSelect
              id="base"
              label="Antes (base)"
              value={baseId}
              runs={completed}
              exclude={targetId}
              onChange={(value) => select({ base: value })}
            />
            <RunSelect
              id="alvo"
              label="Depois (alvo)"
              value={targetId}
              runs={completed}
              exclude={baseId}
              onChange={(value) => select({ alvo: value })}
            />
          </div>
          {baseId != null && targetId != null && baseId !== targetId && (
            <Comparison base={baseId} target={targetId} />
          )}
          {(baseId == null || targetId == null) && (
            <p className="text-sm text-muted-foreground">
              São necessários dois treinos concluídos para comparar.
            </p>
          )}
        </CardContent>
      </Card>
    </>
  );
}
