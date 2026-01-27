import type { EnvironmentState } from "../lib/types";

const stateColors: Record<EnvironmentState, string> = {
  CLEAN: "border-[var(--clean)] text-[var(--clean)]",
  CAUTION: "border-[var(--caution)] text-[var(--caution)]",
  CONTAMINATED: "border-[var(--contaminated)] text-[var(--contaminated)]",
};

export function EnvironmentStateBadge({ state }: { state: EnvironmentState }) {
  return (
    <span
      className={[
        "inline-flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs font-bold tracking-wide",
        stateColors[state],
      ].join(" ")}
      aria-label={`Environment state: ${state}`}
    >
      {state}
    </span>
  );
}

