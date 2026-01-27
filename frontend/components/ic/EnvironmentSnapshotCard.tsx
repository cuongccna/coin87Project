import type { DecisionEnvironmentResponse } from "../../lib/types";
import { EnvironmentStateBadge } from "./EnvironmentStateBadge";
import { SystemMessage } from "./SystemMessage";

export function EnvironmentSnapshotCard({ env }: { env: DecisionEnvironmentResponse }) {
  const dominant = (env.dominant_risks ?? []).slice(0, 3);

  return (
    <div className="rounded-lg border border-border bg-bg/30 p-4">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex-1 space-y-3">
          <div>
            <div className="text-xs text-muted">Snapshot time</div>
            <div className="font-mono text-sm text-text">{env.snapshot_time}</div>
          </div>

          <div>
            <div className="text-xs text-muted">Dominant risk categories (max 3)</div>
            <div className="text-sm font-semibold text-text">
              {dominant.length ? dominant.join(", ") : "None"}
            </div>
          </div>

          <div>
            <div className="text-xs text-muted">Risk density (ordinal)</div>
            <div className="text-sm font-semibold text-text">{env.risk_density}</div>
          </div>
        </div>

        <div className="flex items-center justify-center sm:justify-end" aria-label="Environment state">
          <EnvironmentStateBadge state={env.environment_state} size="xl" />
        </div>
      </div>

      {env.data_stale ? (
        <div className="mt-4">
          <SystemMessage
            kind="stale"
            title="Data may be stale"
            detail={`Staleness: ${env.staleness_seconds ?? "unknown"} seconds. Treat as CAUTION if uncertain.`}
          />
        </div>
      ) : null}

      <div className="mt-4 border-t border-border pt-4">
        <div className="text-xs text-muted">Guidance (neutral)</div>
        <div className="mt-1 text-sm text-muted">{env.guidance}</div>
      </div>
    </div>
  );
}

