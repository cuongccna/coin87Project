export function GovernanceLogRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border py-2.5 last:border-b-0">
      <div className="text-sm text-muted">{label}</div>
      <div className="max-w-[720px] text-right text-sm text-text">{value}</div>
    </div>
  );
}

