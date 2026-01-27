type MessageKind = "neutral" | "stale" | "error";

const borderColors: Record<MessageKind, string> = {
  neutral: "border-border",
  stale: "border-[var(--caution)]",
  error: "border-[var(--contaminated)]",
};

export function SystemMessage({
  kind,
  title,
  detail,
}: {
  kind: MessageKind;
  title: string;
  detail: string;
}) {
  return (
    <div
      className={[
        "rounded-lg border bg-panel p-4 shadow-soft",
        borderColors[kind],
      ].join(" ")}
    >
      <div className="font-semibold text-text">{title}</div>
      <div className="mt-1.5 text-sm text-muted">{detail}</div>
    </div>
  );
}
