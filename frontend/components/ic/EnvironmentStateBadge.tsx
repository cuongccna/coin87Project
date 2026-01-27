import type { EnvironmentState } from "../../lib/types";

type BadgeSize = "sm" | "md" | "lg" | "xl";

const sizeClasses: Record<BadgeSize, string> = {
  sm: "px-2 py-1 text-xs",
  md: "px-2.5 py-1.5 text-xs",
  lg: "px-3 py-2 text-sm",
  xl: "px-4 py-3 text-base",
};

const stateColors: Record<EnvironmentState, string> = {
  CLEAN: "border-[var(--clean)] text-[var(--clean)]",
  CAUTION: "border-[var(--caution)] text-[var(--caution)]",
  CONTAMINATED: "border-[var(--contaminated)] text-[var(--contaminated)]",
};

export function EnvironmentStateBadge({
  state,
  size = "md",
}: {
  state: EnvironmentState;
  size?: BadgeSize;
}) {
  return (
    <span
      className={[
        "inline-flex items-center gap-2 rounded-lg border font-bold tracking-wide",
        sizeClasses[size],
        stateColors[state],
      ].join(" ")}
      aria-label={`Environment state: ${state}`}
    >
      {state}
    </span>
  );
}

