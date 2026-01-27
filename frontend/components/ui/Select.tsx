type SelectSize = "sm" | "md";

const sizeClasses: Record<SelectSize, string> = {
  sm: "px-2 py-1 text-xs",
  md: "px-2.5 py-1.5 text-sm",
};

export function Select({
  value,
  onChange,
  options,
  size = "sm",
  className = "",
  "aria-label": ariaLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  size?: SelectSize;
  className?: string;
  "aria-label"?: string;
}) {
  return (
    <select
      className={[
        "rounded-md border border-border bg-panel text-text outline-none",
        "transition-colors duration-150 focus:border-muted",
        sizeClasses[size],
        className,
      ].join(" ")}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label={ariaLabel}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
