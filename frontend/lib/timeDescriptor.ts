// Temporal descriptor logic for Coin87 risks
// Follows Manifesto: "Time is shown only to explain behavior."

type TemporalDescriptor = "BURST" | "INTERMITTENT" | "PERSISTENT" | "ISOLATED";

// Human-readable strings for UI (English — short, descriptive)
// Use concise phrases to avoid repeated verbose text in the UI.
export const TEMPORAL_LABELS: Record<TemporalDescriptor, string> = {
  BURST: "Concentrated burst",
  INTERMITTENT: "Intermittent",
  PERSISTENT: "Persistent",
  ISOLATED: "Isolated",
};

/**
 * Determines the behavioral temporal descriptor for a risk group.
 * Logic is internal and not exposed directly as thresholds.
 */
export function determineTemporalDescriptor(
  occurrenceCount: number,
  validFrom: string, // ISO string
  validTo: string | null // ISO string or null (ongoing)
): TemporalDescriptor {
  // 1. ISOLATED: Very few occurrences, no strong pattern
  if (occurrenceCount <= 1) {
    return "ISOLATED";
  }

  const start = new Date(validFrom).getTime();
  const end = validTo ? new Date(validTo).getTime() : Date.now();
  const durationMs = end - start;
  
  // Convert minimal units for readability (approximate)
  const durationHours = durationMs / (1000 * 60 * 60);

  // 2. BURST: High density in short time
  // Heuristic: If multiple events happen within a very short window (e.g., < 24h)
  // or density is very high.
  if (durationHours < 24 && occurrenceCount > 1) {
    return "BURST";
  }

  // 3. PERSISTENT: Long duration or ongoing
  // Heuristic: If validTo is null (ongoing) or duration is significant (> 7 days)
  if (validTo === null || durationHours > 24 * 7) {
    return "PERSISTENT";
  }

  // 4. INTERMITTENT: Default fallback for repeated events over medium term
  // Implies recurrence but not necessarily continuous or bursty
  return "INTERMITTENT";
}
