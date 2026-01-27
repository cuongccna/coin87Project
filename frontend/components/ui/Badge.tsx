type BiasType = "bullish" | "bearish" | "neutral";
type BadgeVariant = "bias" | "category" | "severity";

const biasColors: Record<BiasType, string> = {
  bullish: "text-bullish border-bullish/30",
  bearish: "text-bearish border-bearish/30",
  neutral: "text-neutral border-neutral/30",
};

const severityColors: Record<"high" | "medium" | "low", string> = {
  high: "text-text border-text/30 bg-text/5",
  medium: "text-muted border-border bg-bg/30",
  low: "text-muted border-border bg-bg/20",
};

type BadgeProps =
  | { variant: "bias"; value: BiasType }
  | { variant: "category"; value: string }
  | { variant: "severity"; value: "high" | "medium" | "low" };

export function Badge(props: BadgeProps) {
  let colorClasses = "";
  let label = "";

  if (props.variant === "bias") {
    colorClasses = biasColors[props.value];
    label = props.value.toUpperCase();
  } else if (props.variant === "category") {
    colorClasses = "text-muted border-border bg-bg/30";
    label = props.value;
  } else if (props.variant === "severity") {
    colorClasses = severityColors[props.value];
    label = props.value === "high" ? "HIGH impact" : props.value === "medium" ? "MEDIUM impact" : "LOW impact";
  }

  return (
    <span
      className={[
        "inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] font-medium",
        colorClasses,
      ].join(" ")}
    >
      {label}
    </span>
  );
}
