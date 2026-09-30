"use client";

import { toast } from "sonner";

import { ForecastChart } from "@/components/forecast-chart";
import { LeadTimeLabel } from "@/components/lead-time-help";
import { Badge } from "@/components/ui/badge";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  type PlanRead,
  type ProductPlan,
  errorMessage,
  useModelChoice,
  useRun,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  SITUATION_LABEL,
  SITUATION_VARIANT,
  fmtNumber,
  fmtPct,
  monthLabel,
} from "@/lib/format";
import { BAND_LEGEND } from "@/lib/help";

const AUTO = "__vencedor__";

function ModelPicker({ plan, product }: { plan: PlanRead; product: ProductPlan }) {
  const run = useRun(plan.run_id);
  const choose = useModelChoice();
  const result = run.data?.resultado?.produtos.find((item) => item.produto === product.produto);
  const models = (result?.modelos ?? [])
    .filter((model) => model.aplicavel)
    .sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99));
  const winner = models.find((model) => model.vencedor);
  const change = (value: string) =>
    choose.mutate(
      { runId: plan.run_id, produto: product.produto, modelo: value === AUTO ? null : value },
      { onError: (error) => toast.error(errorMessage(error)) },
    );
  return (
    <Field>
      <FieldLabel htmlFor="modelo-em-uso">Modelo em uso</FieldLabel>
      <Select value={product.escolha_manual ? product.modelo_em_uso : AUTO} onValueChange={change}>
        <SelectTrigger id="modelo-em-uso" className="w-full sm:w-96">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectItem value={AUTO}>Vencedor automático ({winner?.label ?? "…"})</SelectItem>
            {models
              .filter((model) => model.vencedor === false)
              .map((model) => (
                <SelectItem key={model.modelo} value={model.modelo}>
                  {model.label} · MAPE {fmtPct(model.mape)}
                </SelectItem>
              ))}
          </SelectGroup>
        </SelectContent>
      </Select>
      <FieldDescription>
        A escolha manual vale só para este treino; ao ativar outro treino, volta o vencedor.
      </FieldDescription>
    </Field>
  );
}

function Facts({ plan, product }: { plan: PlanRead; product: ProductPlan }) {
  const horizon = plan.parametros.horizonte_meses;
  const facts: { label: React.ReactNode; value: string }[] = [
    { label: `Previsão ${horizon} ${horizon > 1 ? "meses" : "mês"}`, value: fmtNumber(product.demanda_horizonte) },
    { label: "Estoque + a receber", value: fmtNumber(product.disponivel) },
    { label: "Estoque de segurança", value: fmtNumber(product.estoque_seguranca) },
    { label: "Necessidade de compra", value: fmtNumber(product.necessidade) },
    { label: "Comprar até", value: product.comprar_ate_texto },
    {
      label: <LeadTimeLabel suffix=" · múltiplo" />,
      value: `${fmtNumber(product.lead_time, 1)} m · ${fmtNumber(product.multiplo)}`,
    },
    { label: "Erro médio (MAD)", value: `${fmtNumber(product.mad, 1)} un.` },
    { label: "MAPE", value: fmtPct(product.mape) },
    { label: "Acurácia", value: fmtPct(product.acuracia) },
  ];
  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {facts.map((fact, index) => (
        <div key={index} className="flex flex-col gap-1 rounded-lg border p-3">
          <dt className="text-xs text-muted-foreground">{fact.label}</dt>
          <dd className="text-lg font-semibold tabular-nums">{fact.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function Projection({ product }: { product: ProductPlan }) {
  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Mês</TableHead>
            <TableHead className="text-right">Estoque inicial</TableHead>
            <TableHead className="text-right">Venda prevista</TableHead>
            <TableHead className="text-right">Estoque final</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {product.projecao.map((row) => (
            <TableRow
              key={row.periodo}
              data-negativo={row.final < 0}
              className={cn(row.final < 0 && "bg-destructive/10 text-destructive")}
            >
              <TableCell>{monthLabel(row.periodo)}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtNumber(row.inicial)}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtNumber(row.venda_prevista)}</TableCell>
              <TableCell className="text-right tabular-nums">{fmtNumber(row.final)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** Detalhe do produto (POC-28) com escolha manual de modelo (POC-36). */
export function ProductDetail({
  plan,
  produto,
  onClose,
}: {
  plan: PlanRead;
  produto: string | null;
  onClose: () => void;
}) {
  const product = plan.produtos.find((item) => item.produto === produto) ?? null;
  return (
    <Sheet open={product != null} onOpenChange={(open) => open === false && onClose()}>
      <SheetContent className="w-full overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-3xl">
        {product != null && (
          <>
            <SheetHeader>
              <SheetTitle className="flex flex-wrap items-center gap-2 text-xl">
                {product.label}
                <Badge variant={SITUATION_VARIANT[product.situacao]}>
                  {SITUATION_LABEL[product.situacao]}
                </Badge>
                {product.escolha_manual && <Badge variant="outline">Escolha manual</Badge>}
                {product.excede_capacidade === true && (
                  <Badge variant="destructive">Excede capacidade</Badge>
                )}
              </SheetTitle>
              <SheetDescription>
                Modelo em uso: {product.modelo_label}
                {product.estoque_informado === false && " · sem estoque informado, considerado zero"}
              </SheetDescription>
            </SheetHeader>
            <div className="flex flex-col gap-6 px-4 pb-6">
              <ModelPicker plan={plan} product={product} />
              <Facts plan={plan} product={product} />
              <div className="flex flex-col gap-2">
                <ForecastChart product={product} horizon={plan.parametros.horizonte_meses} />
                <p className="text-xs text-muted-foreground">
                  Faixa sombreada: previsão ± MAD — {BAND_LEGEND}.
                </p>
              </div>
              <div className="flex flex-col gap-2">
                <h3 className="text-sm font-medium">
                  Estoque projetado mês a mês (sem a nova compra)
                </h3>
                <Projection product={product} />
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
