"use client";

import type { InformationReliabilityResponse, InformationCategory } from "../../lib/marketTypes";

// Allowed factors only - focused on information reliability
type RankingFactor = "cross-source confirmation" | "source reliability" | "temporal persistence" | "information freshness";

function rankingExplanation(item: InformationReliabilityResponse["signals"][number]): string {
  let factor1: RankingFactor = "cross-source confirmation";
  let factor2: RankingFactor = "information freshness";

  if (item.category === "narrative") {
    factor1 = "temporal persistence";
  } else if (item.category === "correction") {
    factor1 = "source reliability";
  }

  // Assuming breakdown might not be fully populated or matching legacy code perfectly, simplifying:
  if (item.persistence_hours > 24) {
    factor2 = "temporal persistence";
  } else if (item.reliability_score >= 8.5) {
    factor2 = "cross-source confirmation";
  }

  return `Ranked high due to ${factor1} and ${factor2}.`;
}

// Category-based analyst interpretation templates (max 160 chars total)
// Focused on information reliability, NOT market outcomes
const ANALYST_INTERPRETATION: Record<InformationCategory, string[]> = {
  narrative: [
    "This narrative has shown consistent cross-source confirmation over time.",
    "Information persistence suggests reliable sourcing and verification.",
  ],
  correction: [
    "Correction signals indicate evolving information landscape.",
    "Source behavior shows responsiveness to new data.",
  ],
  event: [
    "Event confirmed by multiple independent sources.",
    "Temporal consistency indicates reliable information flow.",
  ],
  rumor: [
    "Information lacks cross-source confirmation.",
    "Source reliability for this category remains unverified.",
  ],
};

function analystInterpretation(item: InformationReliabilityResponse["signals"][number]): string {
  const templates = ANALYST_INTERPRETATION[item.category] || ANALYST_INTERPRETATION.narrative; // Fallback
  const idx = Math.floor(item.reliability_score * 10) % templates.length;
  return templates[idx];
}

export function AnalystSheet(props: {
  open: boolean;
  onClose: () => void;
  item: InformationReliabilityResponse["signals"][number] | null;
}) {
  if (!props.open || !props.item) return null;

  const b = props.item.breakdown;
  const hasBreakdown = Boolean(b);

  return (
    <div className="fixed inset-0 z-20">
      <button
        type="button"
        className="absolute inset-0 bg-black/50"
        onClick={props.onClose}
        aria-label="Close analyst view"
      />

      <div className="absolute inset-x-0 bottom-0 mx-auto w-full max-w-2xl rounded-t-xl border border-border bg-panel p-4 shadow-soft sm:bottom-auto sm:top-20 sm:rounded-xl">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="text-xs text-muted">Analyst View</div>
            <div className="mt-1 truncate text-sm font-semibold text-text">{props.item.title}</div>
          </div>
          <button
            type="button"
            className="rounded-md border border-border bg-bg/20 px-2 py-1 text-xs text-text transition-colors duration-150 hover:border-muted"
            onClick={props.onClose}
          >
            Close
          </button>
        </div>

        {/* Why ranked high */}
        <div className="mt-3 rounded-lg border border-border bg-bg/10 p-2">
          <div className="text-xs text-muted">Why ranked high:</div>
          <div className="mt-0.5 text-sm text-text">{rankingExplanation(props.item)}</div>
        </div>

        {/* Analyst interpretation */}
        <div className="mt-2 rounded-lg border border-border bg-bg/10 p-2">
          <div className="text-xs text-muted">Analyst interpretation:</div>
          <div className="mt-0.5 text-sm text-text">{analystInterpretation(props.item)}</div>
        </div>

        <div className="mt-3 grid max-h-[45vh] grid-cols-1 gap-3 overflow-auto sm:max-h-[50vh] sm:grid-cols-2">
          {hasBreakdown ? (
            <div className="rounded-lg border border-border bg-bg/20 p-3">
              <div className="text-xs text-muted">Reliability breakdown</div>
              <div className="mt-2 space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted">Source reliability</span>
                  <span className="font-semibold">{b!.source_reliability}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Cross-confirmation</span>
                  <span className="font-semibold">{b!.cross_confirmation}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Temporal persistence</span>
                  <span className="font-semibold">{b!.temporal_persistence}</span>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

