# Next.js (App Router) UI file structure (read-only IC dashboard)
frontend/
  app/
    layout.tsx
    globals.css
    page.tsx                         # Screen 1: Decision Environment (HOME)
    risk-events/page.tsx             # Screen 2: Active Decision Risks
    narratives/page.tsx              # Screen 3: Narrative Contamination
    narratives/[id]/page.tsx
    ic-mode/page.tsx                 # Screen 4: IC Preparation Mode
    history/page.tsx                 # Screen 5: Institutional Memory
    history/[contextId]/page.tsx
    governance/page.tsx              # Screen 6: Governance/Audit (restricted, partial)
  components/
    AppShell.tsx
    EnvironmentStateBadge.tsx
    SnapshotHeader.tsx
    RiskTable.tsx
    NarrativeCard.tsx
    GovernanceLogRow.tsx
    EmptyState.tsx
    SystemMessage.tsx
  lib/
    api.ts
    types.ts
