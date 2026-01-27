import type { ReactNode } from "react";

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <section className="border border-slate-800 rounded-xl bg-slate-900/30 p-5">
      <div className="text-sm font-semibold text-slate-100">{title}</div>
      <div className="mt-1 text-xs text-slate-400">{subtitle}</div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export default function DecisionEnvironmentHomePage() {
  // TODO(data binding): Fetch GET /v1/decision/environment (server-side) using a GET-only wrapper.
  // Rules: no polling faster than minutes; empty state is valid; never fabricate data.

  return (
    <div className="max-w-5xl">
      <div className="mb-6">
        <div className="text-lg font-semibold tracking-wide">
          Decision Environment
        </div>
        <div className="mt-1 text-sm text-slate-400">
          Answer in &lt; 10 seconds: is it safe to make discretionary decisions
          today?
        </div>
      </div>

      <Section
        title="Current snapshot"
        subtitle="No drill-down by default. No urgency framing."
      >
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-400">Environment state</div>
            <div className="mt-2 text-sm font-semibold">
              —{/* TODO: EnvironmentStateBadge */}
            </div>
          </div>

          <div className="border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-400">Snapshot time</div>
            <div className="mt-2 text-xs font-mono text-slate-300">—</div>
          </div>

          <div className="border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-400">Risk density (ordinal)</div>
            <div className="mt-2 text-sm font-semibold">—{/* TODO: RiskDensityIndicator */}</div>
          </div>
        </div>

        <div className="mt-4 border border-slate-800 rounded-lg p-4">
          <div className="text-xs text-slate-400">Dominant risk categories</div>
          <div className="mt-2 text-sm text-slate-200">
            None{/* TODO: max 3 dominant risks from API */}
          </div>
        </div>

        <div className="mt-4 border border-slate-800 rounded-lg p-4">
          <div className="text-xs text-slate-400">Guidance (neutral)</div>
          <div className="mt-2 text-sm text-slate-300">
            No actionable risk detected. Silence is valid.
            {/* TODO: guidance from API */}
          </div>
        </div>

        <div className="mt-4 text-xs text-slate-500">
          TODO: If API marks data as stale, show timestamp clearly and treat as
          CAUTION by default.
        </div>
      </Section>
    </div>
  );
}

