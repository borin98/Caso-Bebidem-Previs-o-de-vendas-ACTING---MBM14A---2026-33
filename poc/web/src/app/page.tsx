import { ArrowRightIcon } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { LandingNumbers } from "@/components/landing-numbers";
import {
  LandingFinalCta,
  LandingHowItWorks,
  LandingProblem,
  LandingTrust,
} from "@/components/landing-sections";
import { Button } from "@/components/ui/button";
import { brand } from "@/config/brand";

export default function Home() {
  return (
    <div className="flex flex-col">
      <header className="border-b">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
          <span className="flex items-center gap-2 font-semibold">
            {brand.logoPath != null && (
              <Image src={brand.logoPath} alt="" width={24} height={24} />
            )}
            {brand.name}
          </span>
          <Button variant="ghost" asChild>
            <Link href="/app">Abrir o painel</Link>
          </Button>
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-16 px-6 py-12">
        <section className="flex flex-col items-start gap-6">
          <h1 className="max-w-3xl text-4xl font-semibold tracking-tight md:text-5xl">
            Menos estoque parado, menos ruptura, compra na medida certa.
          </h1>
          <p className="max-w-2xl text-lg text-muted-foreground">
            {brand.name}: modelos de previsão competem produto a produto e a previsão vencedora
            vira recomendação de compra, a partir do seu estoque.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button size="lg" asChild>
              <Link href="/app">
                Ver demonstração
                <ArrowRightIcon data-icon="inline-end" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <a href="#como-funciona">Como funciona</a>
            </Button>
          </div>
        </section>
        <LandingNumbers />
        <LandingProblem />
        <LandingHowItWorks />
        <LandingTrust />
        <LandingFinalCta />
      </main>
    </div>
  );
}
