import { api } from "../../lib/api";
import { SnapshotHeader } from "../../components/SnapshotHeader";
import { NarrativeCard } from "../../components/NarrativeCard";
import { EmptyState } from "../../components/EmptyState";
import { SystemMessage } from "../../components/SystemMessage";

export const revalidate = 600;

export default async function NarrativesPage() {
  try {
    const narratives = await api.listNarratives({ min_saturation: 2, active_only: true });

    // NOTE: "linked risk count" is not provided by list endpoint.
    // We keep this page low-noise by not fan-out calling detail per narrative.
    // Drill-down page shows linked risks explicitly.
    return (
      <div className="vStack">
        <SnapshotHeader
          title="Narrative Contamination"
          subtitle="Narratives are governance objects, not headlines."
        />

        {narratives.length ? (
          <div className="vStack">
            {narratives.map((n) => (
              <NarrativeCard key={n.narrative_id} n={n} linkedRiskCount={undefined} />
            ))}
          </div>
        ) : (
          <EmptyState
            title="No active narratives above threshold"
            body="Silence is acceptable. Avoid forcing interpretation."
          />
        )}
      </div>
    );
  } catch {
    return <SystemMessage kind="error" title="System unavailable" detail="Unable to load narratives." />;
  }
}

