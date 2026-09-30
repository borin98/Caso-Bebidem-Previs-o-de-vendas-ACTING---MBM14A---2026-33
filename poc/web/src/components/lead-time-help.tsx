"use client";

import { InfoIcon } from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { LEAD_TIME_HELP } from "@/lib/help";

/** Rótulo "Lead time" com ícone de ajuda (POC-26). */
export function LeadTimeLabel({ suffix = "" }: { suffix?: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      Lead time{suffix}
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-label="O que é lead time?"
            className="text-muted-foreground hover:text-foreground"
          >
            <InfoIcon className="size-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">{LEAD_TIME_HELP}</TooltipContent>
      </Tooltip>
    </span>
  );
}
