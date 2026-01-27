import Link from "next/link";
import type { NarrativeResponse } from "../lib/types";

const statusColors: Record<string, string> = {
  ACTIVE: "text-high-reliability",
  FADING: "text-neutral",
  DORMANT: "text-muted",
};

export function NarrativeCard({
  n,
  linkedRiskCount,
}: {
  n: NarrativeResponse;
  linkedRiskCount?: number;
}) {
  return (
    <div className="rounded-lg border border-border bg-panel p-4 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-semibold text-text">{n.theme}</div>
        <div className={["text-xs", statusColors[n.status] ?? "text-muted"].join(" ")}>
          {n.status}
        </div>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        <div className="flex items-center gap-1">
          <span className="text-muted">Saturation:</span>
          <span className="font-semibold text-text">{n.saturation_level}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-muted">Last seen:</span>
          <span className="text-muted">{n.last_seen_at}</span>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-border pt-3">
        <div className="text-xs text-muted">
          Linked risks: {linkedRiskCount ?? "—"}
        </div>
        <Link
          href={`/narratives/${n.narrative_id}`}
          className="text-xs text-muted transition-colors hover:text-text"
        >
          View →
        </Link>
      </div>
    </div>
  );
}

