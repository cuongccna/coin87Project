export function IcSection({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className="rounded-lg border border-border bg-panel p-6 shadow-soft"
      aria-label={title}
    >
      <div className="mb-4 border-b border-border pb-4">
        <h2 className="text-base font-semibold text-text">{title}</h2>
        <p className="mt-1 text-xs text-muted">{subtitle}</p>
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

