import { api } from "../../lib/api";
import { SnapshotHeader } from "../../components/SnapshotHeader";
import { GovernanceLogRow } from "../../components/GovernanceLogRow";
import { SystemMessage } from "../../components/SystemMessage";

export const revalidate = 600;

export default async function GovernancePage() {
  try {
    const env = await api.getDecisionEnvironment();

    return (
      <div className="vStack">
        <SnapshotHeader
          title="Governance / Audit"
          subtitle="Restricted. Read-only. No exports by default."
        />

        <div className="card">
          <GovernanceLogRow label="Current environment state" value={env.environment_state} />
          <GovernanceLogRow label="Snapshot time" value={env.snapshot_time} />
          <GovernanceLogRow label="Dominant risks" value={env.dominant_risks.join(", ") || "None"} />
          <GovernanceLogRow label="Risk density" value={String(env.risk_density)} />
          <GovernanceLogRow label="Data stale" value={env.data_stale ? "YES" : "NO"} />
        </div>

        <SystemMessage
          kind="neutral"
          title="Audit streams not exposed via current API"
          detail="Re-evaluation logs and access log summaries require dedicated GET endpoints (not implemented here)."
        />
      </div>
    );
  } catch {
    return <SystemMessage kind="error" title="System unavailable" detail="Unable to load governance view." />;
  }
}

