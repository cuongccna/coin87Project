import { api } from "../../../lib/api";
import { SnapshotHeader } from "../../../components/SnapshotHeader";
import { EmptyState } from "../../../components/EmptyState";
import { SystemMessage } from "../../../components/SystemMessage";

export const revalidate = 300;

export default async function NarrativeDetailPage({ params }: { params: { id: string } }) {
  try {
    const n = await api.getNarrative(params.id);

    return (
      <div className="vStack">
        <SnapshotHeader title="Narrative Detail" subtitle="Read-only. No headlines." />

        <div className="card">
          <div style={{ fontWeight: 650 }}>{n.theme}</div>
          <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
            Status: {n.status} · Saturation: {n.saturation_level}
          </div>
          <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
            First seen: {n.first_seen_at} · Last seen: {n.last_seen_at}
          </div>
        </div>

        {n.linked_risks.length ? (
          <div className="card">
            <div style={{ fontWeight: 650, marginBottom: 10 }}>Linked active risks (abstracted)</div>
            <table className="table" aria-label="Linked risks">
              <thead>
                <tr>
                  <th>Risk type</th>
                  <th>Severity</th>
                  <th>Posture</th>
                  <th>Validity</th>
                </tr>
              </thead>
              <tbody>
                {n.linked_risks.map((r, idx) => (
                  <tr key={`${r.risk_type}:${r.valid_from}:${idx}`}>
                    <td>{r.risk_type}</td>
                    <td>{r.severity}</td>
                    <td>{r.recommended_posture}</td>
                    <td className="muted" style={{ fontSize: 12 }}>
                      {r.valid_from} → {r.valid_to ?? "open"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No linked active risks" body="This is valid. Not all narratives are active risks." />
        )}
      </div>
    );
  } catch {
    return <SystemMessage kind="error" title="Not available" detail="Unable to load narrative detail." />;
  }
}

