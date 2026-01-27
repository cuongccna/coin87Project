import { HomeHeader } from '../components/home/HomeHeader';
import { SilenceArea } from '../components/home/SilenceArea';
import { NarrativeCard } from '../components/narrative/NarrativeCard';
import { OfflineIndicator } from '../components/ui/OfflineIndicator';
import { HomeSnapshot, NarrativeSummary, ReliabilityStatus, NarrativeState } from '../lib/uiTypes';
import { ClientEntry } from '../components/ClientEntry';
import { api } from '../lib/api';
import { InformationReliabilityResponse, ReliabilityLevel } from '../lib/marketTypes';

// Type Mapping Helpers

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

export default async function HomePage() {
  // Fetch Real Data
  let data: InformationReliabilityResponse;
  
  try {
    data = await api.getInformationReliability("MARKET", 60); // Cache for 60s
  } catch (err) {
    console.error("Failed to fetch market intel:", err);
    // Returning empty/safe data to allow page load with "Offline" look
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

  const snapshot: HomeSnapshot = {
    active_narratives_count: data.state.active_narratives_count,
    clarity_score: data.state.confirmation_rate, // Using confirmation rate as proxy for clarity
    last_updated_at: new Date().toISOString() // Ideally backend timestamp
  };

  const allNarratives: NarrativeSummary[] = data.signals.map((signal, index) => ({
    id: signal.narrative_id ?? `signal-${index}`, // Use real ID if available, else safe fallback
    topic: signal.title,
    state: mapState(signal.persistence_hours),
    last_updated: new Date().toISOString(),
    first_seen_at: new Date(Date.now() - signal.persistence_hours * 3600 * 1000).toISOString(),
    reliability_score: signal.reliability_score,
    reliability_label: mapReliability(signal.reliability_level),
    is_ignored: signal.reliability_level === 'unverified', // Treat unverified as suppressed/noise
    explanation_metadata: {
        consensus_level: signal.confirmation_count > 5 ? 'high' : signal.confirmation_count > 2 ? 'medium' : 'low',
        source_diversity: 'limited', // Default
        is_steady: signal.persistence_hours > 24,
        has_contradictions: false // Not in basic signal
    }
  }));

  const activeNarratives = allNarratives.filter(n => !n.is_ignored);
  const ignoredNarratives = allNarratives.filter(n => n.is_ignored);

  return (
    <ClientEntry>
      <main className="min-h-screen bg-background text-primary pb-safe">
        {/* Offline Awareness Layer */}
        <OfflineIndicator lastUpdated={snapshot.last_updated_at} />
        
        <HomeHeader snapshot={snapshot} />
        
        <div className="px-4 py-6">
          <h2 className="text-xs font-mono uppercase text-tertiary mb-4 ml-1">
            Active Narratives
          </h2>
          
          {activeNarratives.length === 0 ? (
             <div className="text-sm text-tertiary p-4 border border-border/50 rounded-lg border-dashed">
                No active signals detected.
             </div>
          ) : (
            activeNarratives.map(n => (
                <NarrativeCard key={n.id} narrative={n} />
            ))
          )}
        </div>

        <SilenceArea ignoredNarratives={ignoredNarratives} />
      </main>
    </ClientEntry>
  );
}
