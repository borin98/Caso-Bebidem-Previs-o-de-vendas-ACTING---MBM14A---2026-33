import {
  ArrowRightIcon,
  BoxesIcon,
  CalendarSyncIcon,
  DatabaseIcon,
  EyeIcon,
  HistoryIcon,
  ShoppingCartIcon,
  SwordsIcon,
  TrendingDownIcon,
  TriangleAlertIcon,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { brand } from "@/config/brand";

const PROBLEMS = [
  {
    icon: TriangleAlertIcon,
    title: "Ruptura na prateleira",
    text: "O produto acaba antes do pedido chegar e a venda vai para o concorrente.",
  },
  {
    icon: BoxesIcon,
    title: "Capital parado em estoque",
    text: "Compra por intuição gera excesso de itens que giram devagar.",
  },
  {
    icon: TrendingDownIcon,
    title: "Previsão em planilha",
    text: "Médias manuais ignoram sazonalidade e tendência e não dizem quanto erram.",
  },
];

const STEPS = [
  {
    icon: DatabaseIcon,
    title: "Dados",
    text: "Carregue a planilha de vendas ou feche o mês digitando as vendas de cada produto.",
  },
  {
    icon: SwordsIcon,
    title: "Competição de modelos",
    text: "Machine learning, regressões clássicas e séries temporais são testados nos meses mais recentes de venda; vence o menor erro.",
  },
  {
    icon: ShoppingCartIcon,
    title: "Recomendação de compra",
    text: "A previsão do vencedor encontra o seu estoque: quanto comprar, até quando e qual o risco.",
  },
];

const TRUST = [
  {
    icon: EyeIcon,
    title: "Métricas abertas",
    text: "MAPE, MAD, RMSE e MPE de cada modelo, com o critério de escolha à vista.",
  },
  {
    icon: CalendarSyncIcon,
    title: "Re-treino a cada fechamento",
    text: "Fechou o mês, os modelos são avaliados de novo com o dado mais recente.",
  },
  {
    icon: HistoryIcon,
    title: "Versões auditáveis",
    text: "Cada treino fica guardado; compare antes e depois e reative uma versão anterior.",
  },
];

function FeatureGrid({ items }: { items: typeof PROBLEMS }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {items.map((item) => (
        <Card key={item.title}>
          <CardHeader>
            <item.icon className="mb-2 size-6 text-primary" />
            <CardTitle>{item.title}</CardTitle>
            <CardDescription>{item.text}</CardDescription>
          </CardHeader>
        </Card>
      ))}
    </div>
  );
}

function Section({
  id,
  title,
  children,
}: {
  id?: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="flex scroll-mt-8 flex-col gap-6">
      <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
      {children}
    </section>
  );
}

export function LandingProblem() {
  return (
    <Section title="O problema">
      <FeatureGrid items={PROBLEMS} />
    </Section>
  );
}

export function LandingHowItWorks() {
  return (
    <Section id="como-funciona" title="Como funciona">
      <FeatureGrid items={STEPS} />
    </Section>
  );
}

export function LandingTrust() {
  return (
    <Section title="Por que confiar">
      <FeatureGrid items={TRUST} />
    </Section>
  );
}

export function LandingFinalCta() {
  return (
    <section className="flex flex-col items-center gap-4 rounded-xl border bg-muted/40 p-10 text-center">
      <h2 className="text-2xl font-semibold tracking-tight">Veja o plano de compra do case</h2>
      <p className="max-w-xl text-muted-foreground">{brand.slogan}</p>
      <Button size="lg" asChild>
        <Link href="/app">
          Abrir o painel
          <ArrowRightIcon data-icon="inline-end" />
        </Link>
      </Button>
    </section>
  );
}
