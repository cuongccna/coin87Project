export interface DiscussionRiskItemProps {
  riskTypeName: string;
  whyThisMatters: string;
  typicalFailureMode: string;
}

export function DiscussionRiskItem({
  riskTypeName,
  whyThisMatters,
  typicalFailureMode,
}: DiscussionRiskItemProps) {
  return (
    <div className="py-3 border-t border-slate-800">
      <div className="text-xs font-semibold tracking-wide text-slate-200">
        {riskTypeName}
      </div>
      <p className="mt-2 text-sm leading-relaxed text-slate-200">{whyThisMatters}</p>
      <div className="mt-3 text-xs text-slate-500">Typical failure mode</div>
      <p className="mt-1 text-sm leading-relaxed text-slate-200">{typicalFailureMode}</p>
    </div>
  );
}

