import { FlaskConicalIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { DEMO_POSITIONS_BADGE } from "@/lib/help";

/** Selo de A14/POC-30: some quando o usuário salva posições ou importa estoque. */
export function DemoPositionsBadge() {
  return (
    <Badge variant="secondary" className="w-fit">
      <FlaskConicalIcon data-icon="inline-start" />
      {DEMO_POSITIONS_BADGE}
    </Badge>
  );
}
