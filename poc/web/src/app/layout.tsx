import type { Metadata } from "next";
import "katex/dist/katex.min.css";


import { brand } from "@/config/brand";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: brand.name,
  description: brand.slogan,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  const brandStyle = {
    "--primary": brand.primaryColor,
    "--primary-foreground": "oklch(0.985 0 0)",
    "--sidebar-primary": brand.primaryColor,
    "--chart-1": brand.primaryColor,
  } as React.CSSProperties;
  return (
    <html lang="pt-BR" className="h-full antialiased" style={brandStyle}>
      <body className="flex min-h-full flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
