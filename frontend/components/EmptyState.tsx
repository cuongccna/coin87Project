export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-border bg-panel p-4 shadow-soft">
      <div className="font-semibold text-text">{title}</div>
      <div className="mt-1.5 text-sm text-muted">{body}</div>
    </div>
  );
}

