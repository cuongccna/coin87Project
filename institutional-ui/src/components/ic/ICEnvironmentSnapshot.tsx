import type { DecisionEnvironmentResponse } from "../../lib/types";

export interface ICEnvironmentSnapshotProps {
  env: DecisionEnvironmentResponse;
}

function EnvironmentStateBadge({
  state,
}: {
  state: "CLEAN" | "CAUTION" | "CONTAMINATED";
}) {
  const classes =
    state === "CLEAN"
      ? "border-slate-600 text-slate-200"
      : state === "CAUTION"
        ? "border-amber-700 text-amber-200"
        : "border-rose-800 text-rose-200";

  return (
    <div
      className={`border rounded-md px-5 py-4 text-center font-bold tracking-wide ${classes}`}
      aria-label={`Environment state: ${state}`}
    >
      {state}
    </div>
  );
}

function RiskDensityIndicator({ riskDensity }: { riskDensity: number }) {
  // Ordinal label only (no charts).
  const label = riskDensity <= 0 ? "LOW" : riskDensity <= 2 ? "MEDIUM" : "HIGH";
  return (
    <div className="inline-flex items-center gap-2">
      <span className="text-sm font-semibold text-slate-200">{label}</span>
      <span className="text-xs text-slate-500">(density={riskDensity})</span>
    </div>
  );
}

export function ICEnvironmentSnapshot({ env }: ICEnvironmentSnapshotProps) {
  const dominant = (env.dominant_risks ?? []).slice(0, 3);

  return (
    <div className="border-t border-b border-slate-800 py-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
        <div className="lg:col-span-2">
          <div className="text-xs text-slate-400">Snapshot timestamp</div>
          <div className="mt-2 text-xs font-mono text-slate-200">{env.snapshot_time}</div>

          <div className="mt-4 text-xs text-slate-400">
            Dominant risk categories (max 3)
          </div>
          <div className="mt-2 text-sm leading-relaxed text-slate-200">
            {dominant.length ? dominant.join(", ") : "None"}
          </div>

          <div className="mt-4 text-xs text-slate-400">Risk density (ordinal)</div>
          <div className="mt-2">
            <RiskDensityIndicator riskDensity={env.risk_density} />
          </div>

          {env.data_stale ? (
            <div className="mt-4 text-xs leading-relaxed text-slate-500">
              Data may be stale. Treat environment as CAUTION if uncertain.
            </div>
          ) : null}
        </div>

        <div className="lg:col-span-1 flex justify-center lg:justify-end">
          <EnvironmentStateBadge state={env.environment_state} />
        </div>
      </div>
    </div>
  );
}

