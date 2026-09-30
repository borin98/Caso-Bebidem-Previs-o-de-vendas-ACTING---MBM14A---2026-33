"use client";

import { BarChart3Icon, DatabaseIcon, HistoryIcon, LayoutDashboardIcon } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { TrainingStatus } from "@/components/training-status";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { brand } from "@/config/brand";

const NAV = [
  { href: "/app", label: "Painel", icon: LayoutDashboardIcon },
  { href: "/app/modelos", label: "Modelos", icon: BarChart3Icon },
  { href: "/app/dados", label: "Dados", icon: DatabaseIcon },
  { href: "/app/versoes", label: "Versões", icon: HistoryIcon },
];

export function AppSidebar() {
  const pathname = usePathname();
  return (
    <Sidebar>
      <SidebarHeader>
        <Link href="/" className="flex items-center gap-2 px-2 py-1.5 font-semibold">
          {brand.logoPath != null && <Image src={brand.logoPath} alt="" width={24} height={24} />}
          {brand.name}
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild isActive={pathname === item.href}>
                    <Link href={item.href}>
                      <item.icon />
                      <span>{item.label}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <TrainingStatus />
      </SidebarFooter>
    </Sidebar>
  );
}
