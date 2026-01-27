import type { DecisionRiskEventResponse } from "../lib/types";

const postureColors: Record<string, string> = {
  IGNORE: "text-muted",
  REVIEW: "text-neutral",
  DELAY: "text-bearish",
};

export function RiskTable({ risks }: { risks: DecisionRiskEventResponse[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm" aria-label="Active decision risk events">
        <thead>
          <tr>
            <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold text-muted">
              Risk type
            </th>
            <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold text-muted">
              Affected decision
            </th>
            <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold text-muted">
              Severity
            </th>
            <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold text-muted">
              Validity window
            </th>
            <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold text-muted">
              Posture
            </th>
          </tr>
        </thead>
        <tbody>
          {risks.map((r, idx) => (
            <tr key={`${r.risk_type}:${r.detected_at}:${idx}`} className="hover:bg-bg/30">
              <td className="border-b border-border px-3 py-2 text-text">{r.risk_type}</td>
              <td className="border-b border-border px-3 py-2 text-text">
                {r.affected_decisions.join(", ")}
              </td>
              <td className="border-b border-border px-3 py-2 text-text">{r.severity}</td>
              <td className="border-b border-border px-3 py-2 text-xs text-muted">
                {r.time_relevance.valid_from} → {r.time_relevance.valid_to ?? "open"}
              </td>
              <td
                className={[
                  "border-b border-border px-3 py-2 font-medium",
                  postureColors[r.recommended_posture] ?? "text-text",
                ].join(" ")}
              >
                {r.recommended_posture}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

