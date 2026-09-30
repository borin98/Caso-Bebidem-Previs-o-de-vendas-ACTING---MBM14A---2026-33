"use client";

import { AppSidebar } from "@/components/app-sidebar";
import { ApiUnavailable } from "@/components/api-unavailable";
import { Separator } from "@/components/ui/separator";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { brand } from "@/config/brand";
import { ApiUnavailable as ApiUnavailableError, useOverview } from "@/lib/api";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const overview = useOverview();
  const unavailable = overview.error instanceof ApiUnavailableError;
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-12 items-center gap-2 border-b px-4">
          <SidebarTrigger />
          <Separator orientation="vertical" className="h-4" />
          <span className="text-sm text-muted-foreground">{brand.slogan}</span>
        </header>
        <div className="flex flex-1 flex-col gap-6 p-4 md:p-6">
          {unavailable && <ApiUnavailable onRetry={() => void overview.refetch()} />}
          {unavailable === false && children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
