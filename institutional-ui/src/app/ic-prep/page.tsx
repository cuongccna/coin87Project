import type { ReactNode } from "react";

import type {
  DecisionEnvironmentResponse,
  DecisionRiskEventResponse,
  NarrativeResponse,
} from "../../lib/types";
import { ICEnvironmentSnapshot } from "../../components/ic/ICEnvironmentSnapshot";
import { DiscussionRiskItem } from "../../components/ic/DiscussionRiskItem";
import { NarrativePressureSummary } from "../../components/ic/NarrativePressureSummary";
import { ICQuestionPrompt } from "../../components/ic/ICQuestionPrompt";

export const revalidate = 300; // minutes-level cadence; no frequent polling

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <section className="py-5 border-b border-slate-800">
      <div className="text-xs font-semibold tracking-wide text-slate-200">
        {title}
      </div>
      <div className="mt-2 text-sm leading-relaxed text-slate-400">{subtitle}</div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function NeutralSystemMessage({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="py-4 border-t border-b border-slate-800">
      <div className="text-xs font-semibold tracking-wide text-slate-200">{title}</div>
      <div className="mt-2 text-sm leading-relaxed text-slate-300">{detail}</div>
    </div>
  );
}

async function fetchJson<T>(path: string): Promise<T> {
  const base = process.env.C87_API_BASE_URL;
  const token = process.env.C87_UI_BEARER_TOKEN;

  if (!base || !token) {
    throw new Error("MISSING_ENV");
  }

  const res = await fetch(`${base}${path}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "X-Request-Id": crypto.randomUUID(),
    },
    // No polling; cache at minutes-level.
    next: { revalidate },
  });

  if (!res.ok) throw new Error(`HTTP_${res.status}`);
  return (await res.json()) as T;
}

type DiscussionRiskFactor = {
  key: string;
  riskTypeName: string;
  whyThisMatters: string;
  typicalFailureMode: string;
};

function buildDiscussionRiskFactors(
  env: DecisionEnvironmentResponse,
  risks: DecisionRiskEventResponse[],
): DiscussionRiskFactor[] {
  // Minimal mapping only. No scoring, no ranking, no urgency framing.
  const out: DiscussionRiskFactor[] = [];

  const dominant = new Set((env.dominant_risks ?? []).map((x) => x.toLowerCase()));
  const riskTypes = new Set((risks ?? []).map((r) => String(r.risk_type).toLowerCase()));
  const has = (k: string) => dominant.has(k) || riskTypes.has(k);

  if (has("narrative_contamination") || has("narrative contamination")) {
    out.push({
      key: "narrative_contamination",
      riskTypeName: "Narrative Contamination",
      whyThisMatters:
        "High narrative saturation increases conformity pressure and narrows acceptable viewpoints in discussion.",
      typicalFailureMode:
        "Thesis drift: the committee debates story coherence instead of verification gates.",
    });
  }

  if (has("timing_distortion") || has("timing distortion")) {
    out.push({
      key: "timing_distortion",
      riskTypeName: "Timing Distortion",
      whyThisMatters: "Information bursts bias urgency perception and compress diligence windows.",
      typicalFailureMode:
        "Premature action: decisions are made to relieve discomfort rather than improve certainty.",
    });
  }

  if (has("consensus_trap") || has("consensus trap")) {
    out.push({
      key: "consensus_trap",
      riskTypeName: "Consensus Trap",
      whyThisMatters:
        "Perceived alignment can create reputational pressure to ‘not be late’, independent of evidence quality.",
      typicalFailureMode:
        "Oversizing / forced communication: the committee acts to match optics, not verification.",
    });
  }

  if (has("structural_decision_risk") || has("structural decision risk")) {
    out.push({
      key: "structural_decision_risk",
      riskTypeName: "Structural Decision Risk",
      whyThisMatters:
        "Recurring contamination patterns degrade process discipline over repeated cycles.",
      typicalFailureMode:
        "Institutional memory gap: repeated mistakes because prior context is not recalled under pressure.",
    });
  }

  if (env.data_stale) {
    out.push({
      key: "staleness",
      riskTypeName: "Coverage / Staleness",
      whyThisMatters:
        "Stale evaluation increases false confidence and makes ‘clean’ posture unreliable.",
      typicalFailureMode:
        "False cleanliness: the committee proceeds without shared reality on what was observed.",
    });
  }

  return out.slice(0, 5);
}

const DEFAULT_QUESTIONS: string[] = [
  "What evidence would change DELAY → REVIEW today?",
  "Are we reacting to consensus optics rather than verified facts?",
  "Which decision can be deferred without breaching governance discipline?",
  "What would we write in a post-mortem if this narrative proves false?",
  "What is our explicit stop condition for continuing discussion on this topic?",
];

export default async function ICPreparationModePage() {
  try {
    const [env, risks, narratives] = await Promise.all([
      fetchJson<DecisionEnvironmentResponse>("/v1/decision/environment"),
      fetchJson<DecisionRiskEventResponse[]>("/v1/decision/risk-events?min_severity=3"),
      fetchJson<NarrativeResponse[]>(
        "/v1/decision/narratives?min_saturation=2&active_only=true",
      ),
    ]);

    const factors = buildDiscussionRiskFactors(env, risks);

    return (
      <div className="max-w-6xl">
        <header className="pb-4 border-b border-slate-800">
          <div className="text-base font-semibold tracking-wide text-slate-100">
            IC Preparation Mode
          </div>
          <div className="mt-2 text-sm leading-relaxed text-slate-400">
            Agenda-style view. Designed to slow discussion and surface bias.
            This page is read-only and intended for screen-sharing or printing.
          </div>
        </header>

        <div className="mt-2">
          {/* SECTION 1 */}
          <Section
            title="SECTION 1 — Decision Environment Snapshot"
            subtitle="Establish shared reality before opinions. No links. No drill-down."
          >
            <ICEnvironmentSnapshot env={env} />
          </Section>

          {/* SECTION 2 */}
          <Section
            title="SECTION 2 — Discussion Risk Factors"
            subtitle="Textual explanation > numbers. Max 5 items. No severity ranking."
          >
            {factors.length ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                {factors.map((f) => (
                  <DiscussionRiskItem
                    key={f.key}
                    riskTypeName={f.riskTypeName}
                    whyThisMatters={f.whyThisMatters}
                    typicalFailureMode={f.typicalFailureMode}
                  />
                ))}
              </div>
            ) : (
              <NeutralSystemMessage
                title="No discussion-level risks detected"
                detail="This is a valid state. Maintain normal diligence cadence and avoid manufacturing urgency."
              />
            )}
          </Section>

          {/* SECTION 3 */}
          <Section
            title="SECTION 3 — Narrative Pressure Summary"
            subtitle="Abstract themes only. No headlines. No sources. No assets."
          >
            <NarrativePressureSummary narratives={narratives} />
          </Section>

          {/* SECTION 4 */}
          <Section
            title="SECTION 4 — IC Discipline Questions"
            subtitle="Read aloud. No checkboxes. No answers. No CTA."
          >
            <ICQuestionPrompt questions={DEFAULT_QUESTIONS} />
          </Section>
        </div>

        <div className="mt-4 text-xs text-slate-500">
          TODO: Print-friendly layout tuning (page breaks) and optional single-page export formatting.
        </div>
      </div>
    );
  } catch {
    return (
      <NeutralSystemMessage
        title="IC Preparation Mode unavailable"
        detail="Unable to load required read-only inputs. Treat environment as uncertain and avoid forced action."
      />
    );
  }
}

