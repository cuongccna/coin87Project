import type { NarrativeResponse } from "../../lib/types";

export interface NarrativePressureSummaryProps {
  narratives: NarrativeResponse[];
}

export function NarrativePressureSummary({ narratives }: NarrativePressureSummaryProps) {
  const list = (narratives ?? []).slice(0, 8);

  if (!list.length) {
    return (
      <div className="py-4 border-t border-b border-slate-800">
        <div className="text-sm leading-relaxed text-slate-200">
          No dominant narrative pressure.
        </div>
        <div className="mt-2 text-xs leading-relaxed text-slate-500">
          Silence is acceptable. Avoid forcing interpretation.
        </div>
      </div>
    );
  }

  return (
    <div className="py-4 border-t border-b border-slate-800">
      <table className="w-full text-sm" aria-label="Narrative pressure summary">
        <thead>
          <tr className="text-xs text-slate-400 border-b border-slate-800">
            <th className="text-left py-2 pr-3 font-semibold">Theme (abstract)</th>
            <th className="text-left py-2 pr-3 font-semibold">Saturation</th>
            <th className="text-left py-2 font-semibold">Status</th>
          </tr>
        </thead>
        <tbody>
          {list.map((n) => (
            <tr key={n.narrative_id} className="border-b border-slate-800/60">
              <td className="py-3 pr-3 font-semibold text-slate-200">{n.theme}</td>
              <td className="py-3 pr-3 text-slate-200">{n.saturation_level}</td>
              <td className="py-3 text-slate-500">{n.status}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-3 text-xs leading-relaxed text-slate-500">
        No headlines. No sources. No assets. This section is pattern-focused.
      </div>
    </div>
  );
}

