import { api } from "../../lib/api";
import { IcSection } from "../../components/ic/IcSection";
import { EnvironmentSnapshotCard } from "../../components/ic/EnvironmentSnapshotCard";
import { DiscussionRiskFactors } from "../../components/ic/DiscussionRiskFactors";
import { NarrativePressureBrief } from "../../components/ic/NarrativePressureBrief";
import { IcQuestions } from "../../components/ic/IcQuestions";
import { SystemMessage } from "../../components/ic/SystemMessage";

export const revalidate = 300;

export default async function ICPreparationModePage() {
  try {
    const [env, risks, narratives] = await Promise.all([
      api.getDecisionEnvironment(300),
      api.listRiskEvents({ min_severity: 3 }, 300),
      api.listNarratives({ min_saturation: 2, active_only: true }, 600),
    ]);

    return (
      <div className="icPage">
        <IcSection title="1) Decision Environment Snapshot" subtitle="Establish shared reality before opinions.">
          <EnvironmentSnapshotCard env={env} />
        </IcSection>

        <IcSection
          title="2) Cognitive & Social Risk Warnings"
          subtitle="Bias risks likely to appear in discussion. Textual explanation over numbers."
        >
          <DiscussionRiskFactors env={env} risks={risks} />
        </IcSection>

        <IcSection title="3) Narrative Pressure Brief" subtitle="Narrative dominance without headlines.">
          <NarrativePressureBrief narratives={narratives} />
        </IcSection>

        <IcSection title="4) Questions IC Should Explicitly Ask" subtitle="Constructive friction. No acceleration.">
          <IcQuestions />
        </IcSection>
      </div>
    );
  } catch {
    return (
      <SystemMessage
        kind="error"
        title="System unavailable"
        detail="Unable to generate IC Preparation Mode. Treat environment as uncertain and avoid forced action."
      />
    );
  }
}

