export function SnapshotHeader({
  title,
  subtitle,
  right,
}: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h1 className="text-base font-semibold text-text">{title}</h1>
        {subtitle ? (
          <p className="mt-1 text-xs text-muted">{subtitle}</p>
        ) : null}
      </div>
      {right ?? null}
    </div>
  );
}

