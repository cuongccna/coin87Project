import { api } from "../../../lib/api";
import { SnapshotHeader } from "../../../components/SnapshotHeader";
import { EnvironmentStateBadge } from "../../../components/EnvironmentStateBadge";
import { EmptyState } from "../../../components/EmptyState";
import { SystemMessage } from "../../../components/SystemMessage";

export const revalidate = 300;

export default async function HistoryDetailPage({ params }: { params: { contextId: string } }) {
  try {
    const item = await api.getDecisionHistoryItem(params.contextId, 300);

    return (
      <div className="vStack">
        <SnapshotHeader title="Decision Context" subtitle={item.context.context_time} />

        <div className="card">
          <div className="muted" style={{ fontSize: 12 }}>
            Context
          </div>
          <div style={{ marginTop: 8 }}>
            <div>
              <span className="muted">Type:</span> {item.context.context_type}
            </div>
            <div>
              <span className="muted">Time:</span> {item.context.context_time}
            </div>
            <div>
              <span className="muted">Description:</span> {item.context.description ?? "—"}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="hStack" style={{ justifyContent: "space-between" }}>
            <div>
              <div className="muted" style={{ fontSize: 12 }}>
                Decision environment at time
              </div>
              <div style={{ marginTop: 8 }}>
                <div>
                  <span className="muted">Snapshot:</span>{" "}
                  {item.decision_environment_at_time?.snapshot_time ?? "—"}
                </div>
                <div>
                  <span className="muted">Dominant risks:</span>{" "}
                  {item.decision_environment_at_time?.dominant_risks?.join(", ") || "—"}
                </div>
              </div>
            </div>
            {item.decision_environment_at_time ? (
              <EnvironmentStateBadge state={item.decision_environment_at_time.environment_state} />
            ) : (
              <span className="muted">—</span>
            )}
          </div>
          {item.decision_environment_at_time?.guidance ? (
            <div className="muted" style={{ marginTop: 10 }}>
              {item.decision_environment_at_time.guidance}
            </div>
          ) : null}
        </div>

        {item.impacts.length ? (
          <div className="card">
            <div style={{ fontWeight: 650, marginBottom: 10 }}>Qualitative outcomes (governance)</div>
            <table className="table" aria-label="Impact records">
              <thead>
                <tr>
                  <th>Recorded at</th>
                  <th>Outcome</th>
                  <th>Learning flags</th>
                </tr>
              </thead>
              <tbody>
                {item.impacts.map((i, idx) => (
                  <tr key={`${i.recorded_at}:${idx}`}>
                    <td>{i.recorded_at}</td>
                    <td>{i.qualitative_outcome}</td>
                    <td>{i.learning_flags.join(", ") || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No post-decision reflections recorded" body="This is valid." />
        )}
      </div>
    );
  } catch {
    return <SystemMessage kind="error" title="Not available" detail="Unable to load decision context." />;
  }
}

