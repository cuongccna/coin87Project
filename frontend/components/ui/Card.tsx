export function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={[
        "rounded-lg border border-border bg-panel p-4 shadow-soft",
        className,
      ].join(" ")}
    >
      {children}
    </div>
  );
}
