import { HomeHeader } from '../components/home/HomeHeader';
import { SilenceArea } from '../components/home/SilenceArea';
import { NarrativeCard } from '../components/narrative/NarrativeCard';
import { OfflineIndicator } from '../components/ui/OfflineIndicator';
import { HomeSnapshot, NarrativeSummary, ReliabilityStatus, NarrativeState } from '../lib/uiTypes';
import { ClientEntry } from '../components/ClientEntry';
import { api } from '../lib/api';
import { InformationReliabilityResponse, ReliabilityLevel } from '../lib/marketTypes';
import { NarrativeResponse } from '../lib/types';

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

function mapBackendStatusToUI(status: string): NarrativeState {
    switch (status) {
        case 'ACTIVE': return 'ACTIVE';
        case 'FADING': return 'FADING';
        case 'DORMANT': return 'DORMANT';
        default: return 'ACTIVE';
    }
}

/* -----------------------------
   Trust Thresholds (Coin87 Logic)
----------------------------- */

const ACTIVE_THRESHOLD = 0.6;
const EMERGING_THRESHOLD = 0.3;

export default async function HomePage() {
  let data: InformationReliabilityResponse;
  let activeNarrativesList: NarrativeResponse[] = [];

  try {
    const [intelRes, narrativesRes] = await Promise.allSettled([
      api.getInformationReliability("MARKET"),
      api.listNarratives({ active_only: true })
    ]);

    if (intelRes.status === 'fulfilled') {
      data = intelRes.value;
    } else {
      throw intelRes.reason;
    }

    if (narrativesRes.status === 'fulfilled') {
        activeNarrativesList = narrativesRes.value;
    } else {
        console.warn("Failed to fetch active narratives list", narrativesRes.reason);
    }

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

  // Signals for emerging/raw intelligence
  const signalNarratives: NarrativeSummary[] = data.signals.map((signal, index) => ({
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

  // True Active Narratives from narrative service
  const activeNarratives: NarrativeSummary[] = activeNarrativesList.map(n => ({
      id: n.narrative_id,
      topic: n.theme,
      state: mapBackendStatusToUI(n.status),
      last_updated: n.last_seen_at,
      first_seen_at: n.first_seen_at,
      reliability_score: n.saturation_level * 2, // 1-5 to 1-10 scale
      reliability_label: n.saturation_level >= 4 ? 'STRONG' : n.saturation_level >= 2 ? 'MODERATE' : 'WEAK',
      is_ignored: false,
      explanation_metadata: {
          consensus_level: n.saturation_level >= 4 ? 'high' : 'medium',
          source_diversity: 'limited', // Default
          is_steady: true,
          has_contradictions: false
      }
  }));

  const allNarratives = [...activeNarratives, ...signalNarratives];

  /* -----------------------------
     Tiered Information Zones
  ----------------------------- */

  // Use activeNarratives fetched directly from listNarratives
  // Use signals for Emeging only
  
  const emergingNarratives = signalNarratives.filter(
    n => n.reliability_score < ACTIVE_THRESHOLD * 10 && n.reliability_score >= EMERGING_THRESHOLD * 10
    // Note: signals reliability_score 0-10, thresholds are 0.6 (6.0)
  );

  const silenceNarratives = allNarratives.filter(
    n => n.reliability_score < EMERGING_THRESHOLD * 10
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
