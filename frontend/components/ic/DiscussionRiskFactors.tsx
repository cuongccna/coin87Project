import type { DecisionEnvironmentResponse, DecisionRiskEventResponse } from "../../lib/types";

type RiskFactor = {
  risk_type: string;
  why_it_matters: string;
  typical_failure_mode: string;
};

function buildRiskFactors(
  env: DecisionEnvironmentResponse,
  risks: DecisionRiskEventResponse[],
): RiskFactor[] {
  const out: RiskFactor[] = [];

  const dominant = new Set((env.dominant_risks ?? []).map((x) => x.toLowerCase()));
  const riskTypes = new Set((risks ?? []).map((r) => String(r.risk_type).toLowerCase()));

  const has = (k: string) => dominant.has(k) || riskTypes.has(k);

  if (has("narrative_contamination") || has("narrative contamination")) {
    out.push({
      risk_type: "Narrative Contamination",
      why_it_matters:
        "High narrative saturation increases conformity pressure and narrows acceptable viewpoints in discussion.",
      typical_failure_mode:
        "Thesis drift: the committee debates story coherence instead of verification gates.",
    });
  }

  if (has("timing_distortion") || has("timing distortion")) {
    out.push({
      risk_type: "Timing Distortion",
      why_it_matters: "Information bursts bias urgency perception and compress diligence windows.",
      typical_failure_mode:
        "Premature action: decisions are made to relieve discomfort rather than improve certainty.",
    });
  }

  if (has("consensus_trap") || has("consensus trap")) {
    out.push({
      risk_type: "Consensus Trap",
      why_it_matters:
        "Perceived alignment can create reputational pressure to ‘not be late’, independent of evidence quality.",
      typical_failure_mode:
        "Oversizing / forced communication: the committee acts to match optics, not verification.",
    });
  }

  if (has("structural_decision_risk") || has("structural decision risk")) {
    out.push({
      risk_type: "Structural Decision Risk",
      why_it_matters:
        "Recurring contamination patterns degrade process discipline over repeated cycles.",
      typical_failure_mode:
        "Institutional memory gap: repeated mistakes because prior context is not recalled under pressure.",
    });
  }

  if (env.data_stale) {
    out.push({
      risk_type: "Coverage / Staleness",
      why_it_matters:
        "Stale evaluation increases false confidence and makes ‘clean’ posture unreliable.",
      typical_failure_mode:
        "False cleanliness: the committee proceeds without shared reality on what was observed.",
    });
  }

  return out.slice(0, 5);
}

export function DiscussionRiskFactors({
  env,
  risks,
}: {
  env: DecisionEnvironmentResponse;
  risks: DecisionRiskEventResponse[];
}) {
  const factors = buildRiskFactors(env, risks);

  if (!factors.length) {
    return (
      <div className="rounded-lg border border-border bg-bg/30 p-4">
        <div className="text-sm text-muted">
          No discussion risk factors detected above conservative thresholds. This is a valid state.
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-bg/30 p-4">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm" aria-label="Discussion risk factors">
          <thead>
            <tr>
              <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold text-muted">
                Risk type
              </th>
              <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold text-muted">
                Why this matters in IC
              </th>
              <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold text-muted">
                Typical failure mode
              </th>
            </tr>
          </thead>
          <tbody>
            {factors.map((f) => (
              <tr key={f.risk_type}>
                <td className="border-b border-border px-3 py-2 font-semibold text-text">
                  {f.risk_type}
                </td>
                <td className="border-b border-border px-3 py-2 text-text">
                  {f.why_it_matters}
                </td>
                <td className="border-b border-border px-3 py-2 text-text">
                  {f.typical_failure_mode}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 text-xs text-muted">
        Notes: no severity ranking, no urgency framing. This section is designed to slow discussion.
      </div>
    </div>
  );
}

