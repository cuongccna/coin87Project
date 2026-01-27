import { api } from "../../lib/api";
import { SnapshotHeader } from "../../components/SnapshotHeader";
import { RiskTable } from "../../components/RiskTable";
import { EmptyState } from "../../components/EmptyState";
import { SystemMessage } from "../../components/SystemMessage";

export const revalidate = 300;

export default async function RiskEventsPage() {
  try {
    const risks = await api.listRiskEvents({ min_severity: 3 }, 300);

    return (
      <div className="vStack">
        <SnapshotHeader
          title="Active Decision Risks"
          subtitle="Conservative view. No urgency framing. Empty list is valid."
        />
        {risks.length ? (
          <div className="card">
            <RiskTable risks={risks} />
          </div>
        ) : (
          <EmptyState
            title="No active risks above threshold"
            body="Silence is acceptable. Maintain normal diligence cadence."
          />
        )}
      </div>
    );
  } catch {
    return <SystemMessage kind="error" title="System unavailable" detail="Unable to load risk events." />;
  }
}

