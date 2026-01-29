import { api } from "../../lib/api";
import { SnapshotHeader } from "../../components/SnapshotHeader";
import { EmptyState } from "../../components/EmptyState";
import { SystemMessage } from "../../components/SystemMessage";
import Link from "next/link";

export const revalidate = 600;

export default async function HistoryPage() {
  try {
    const end = new Date();
    const start = new Date(end.getTime() - 30 * 24 * 3600 * 1000);

    const items = await api.listDecisionHistory(
      { start_time: start.toISOString(), end_time: end.toISOString() },
    );

    return (
      <div className="vStack">
        <SnapshotHeader
          title="Institutional Memory"
          subtitle="Post-mortem. No performance charts. No P&L attribution."
        />

        {items.length ? (
          <div className="card">
            <table className="table" aria-label="Decision contexts">
              <thead>
                <tr>
                  <th>Context time</th>
                  <th>Context type</th>
                  <th>Environment state</th>
                  <th>Learning flags</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.context.context_id}>
                    <td>{it.context.context_time}</td>
                    <td>{it.context.context_type}</td>
                    <td>{it.decision_environment_at_time?.environment_state ?? "—"}</td>
                    <td>
                      {Array.from(new Set(it.impacts.flatMap((i) => i.learning_flags))).join(", ") ||
                        "—"}
                    </td>
                    <td>
                      <Link href={`/history/${it.context.context_id}`} className="muted">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No decision contexts in range"
            body="Silence is acceptable. Institutional memory grows over time."
          />
        )}
      </div>
    );
  } catch {
    return <SystemMessage kind="error" title="System unavailable" detail="Unable to load decision history." />;
  }
}

