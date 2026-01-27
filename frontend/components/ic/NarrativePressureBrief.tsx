import type { NarrativeResponse } from "../../lib/types";

const statusColors: Record<string, string> = {
  ACTIVE: "text-bullish",
  FADING: "text-neutral",
  DORMANT: "text-muted",
};

export function NarrativePressureBrief({ narratives }: { narratives: NarrativeResponse[] }) {
  const list = (narratives ?? []).slice(0, 8);

  if (!list.length) {
    return (
      <div className="rounded-lg border border-border bg-bg/30 p-4">
        <div className="text-sm text-muted">
          No active narratives above threshold. Silence is acceptable; avoid forcing interpretation.
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-bg/30 p-4">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm" aria-label="Narrative pressure brief">
          <thead>
            <tr>
              <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold text-muted">
                Theme (abstract)
              </th>
              <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold text-muted">
                Saturation (ordinal)
              </th>
              <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold text-muted">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {list.map((n) => (
              <tr key={n.narrative_id}>
                <td className="border-b border-border px-3 py-2 font-semibold text-text">
                  {n.theme}
                </td>
                <td className="border-b border-border px-3 py-2 text-text">
                  {n.saturation_level}
                </td>
                <td
                  className={[
                    "border-b border-border px-3 py-2",
                    statusColors[n.status] ?? "text-muted",
                  ].join(" ")}
                >
                  {n.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 text-xs text-muted">
        No drill-down and no headlines in IC Mode. This section exists to make narrative dominance explicit.
      </div>
    </div>
  );
}

