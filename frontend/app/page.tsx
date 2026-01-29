import { HomeHeader } from '../components/home/HomeHeader';
import { SilenceArea } from '../components/home/SilenceArea';
import { NarrativeCard } from '../components/narrative/NarrativeCard';
import { OfflineIndicator } from '../components/ui/OfflineIndicator';
import { HomeSnapshot, NarrativeSummary, ReliabilityStatus, NarrativeState } from '../lib/uiTypes';
import { ClientEntry } from '../components/ClientEntry';
import { api } from '../lib/api';
import { InformationReliabilityResponse, ReliabilityLevel } from '../lib/marketTypes';

/* -----------------------------
   Type Mapping Helpers
----------------------------- */

function mapReliability(level: ReliabilityLevel): ReliabilityStatus {
  switch (level) {
    case 'high': return 'STRONG';
    case 'medium': return 'MODERATE';
    case 'low': return 'WEAK';
    case 'unverified': return 'NOISE';
    default: return 'NOISE';
  }
}

function mapState(persistenceHours: number): NarrativeState {
  if (persistenceHours < 24) return 'EMERGING';
  if (persistenceHours < 72) return 'ACTIVE';
  if (persistenceHours < 168) return 'SATURATED';
  return 'FADING';
}

/* -----------------------------
   Trust Thresholds (Coin87 Logic)
----------------------------- */

const ACTIVE_THRESHOLD = 0.6;
const EMERGING_THRESHOLD = 0.3;

export default async function HomePage() {
  let data: InformationReliabilityResponse;

  try {
    data = await api.getInformationReliability("MARKET");
  } catch (err) {
    console.error("Failed to fetch market intel:", err);
    data = {
      state: {
        overall_reliability: "unverified",
        confirmation_rate: 0,
        contradiction_rate: 0,
        active_narratives_count: 0
      },
      signals: []
    };
  }

  /* -----------------------------
     Snapshot Header
  ----------------------------- */

  const snapshot: HomeSnapshot = {
    active_narratives_count: data.state.active_narratives_count,
    clarity_score: Math.min(Math.max(data.state.confirmation_rate, 0), 100), // Ensure clarity_score is between 0 and 100
    last_updated_at: new Date().toISOString() // Ideally backend timestamp
  };

  /* -----------------------------
     Map Backend → UI Model
  ----------------------------- */

  const allNarratives: NarrativeSummary[] = data.signals.map((signal, index) => ({
    id: signal.narrative_id ?? `signal-${index}`,
    topic: signal.title,
    state: mapState(signal.persistence_hours),
    last_updated: new Date().toISOString(),
    first_seen_at: new Date(Date.now() - signal.persistence_hours * 3600 * 1000).toISOString(),
    reliability_score: signal.reliability_score,
    reliability_label: mapReliability(signal.reliability_level),
    is_ignored: false, // no hard suppression here anymore
    explanation_metadata: {
      consensus_level:
        signal.confirmation_count > 5 ? 'high' :
        signal.confirmation_count > 2 ? 'medium' : 'low',
      source_diversity: 'limited',
      is_steady: signal.persistence_hours > 24,
      has_contradictions: false
    }
  }));

  /* -----------------------------
     Tiered Information Zones
  ----------------------------- */

  const activeNarratives = allNarratives.filter(
    n => n.reliability_score >= ACTIVE_THRESHOLD
  );

  const emergingNarratives = allNarratives.filter(
    n => n.reliability_score < ACTIVE_THRESHOLD && n.reliability_score >= EMERGING_THRESHOLD
  );

  const silenceNarratives = allNarratives.filter(
    n => n.reliability_score < EMERGING_THRESHOLD
  );

  /* -----------------------------
     Render
  ----------------------------- */

  return (
    <ClientEntry>
      <main className="min-h-screen bg-background text-primary pb-safe">

        <OfflineIndicator lastUpdated={snapshot.last_updated_at} />
        <HomeHeader snapshot={snapshot} />

        {/* ACTIVE ZONE */}
        <div className="px-4 py-6">
          <h2 className="text-xs font-mono uppercase text-tertiary mb-4 ml-1">
            Active Narratives (High Trust)
          </h2>

          {activeNarratives.length === 0 ? (
            <div className="text-sm text-tertiary p-4 border border-border/50 rounded-lg border-dashed">
              No high-confidence narratives detected.
            </div>
          ) : (
            activeNarratives.map(n => (
              <NarrativeCard key={n.id} narrative={n} />
            ))
          )}
        </div>

        {/* EMERGING ZONE */}
        <div className="px-4 pb-6">
          <h2 className="text-xs font-mono uppercase text-tertiary mb-4 ml-1">
            Emerging Narratives (Forming Consensus)
          </h2>

          {emergingNarratives.length === 0 ? (
            <div className="text-sm text-tertiary p-4 border border-border/30 rounded-lg border-dashed">
              No emerging narratives.
            </div>
          ) : (
            emergingNarratives.map(n => (
              <NarrativeCard key={n.id} narrative={n} />
            ))
          )}
        </div>

        {/* SILENCE ZONE */}
        <SilenceArea ignoredNarratives={silenceNarratives} />

      </main>
    </ClientEntry>
  );
}
