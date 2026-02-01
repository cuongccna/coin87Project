import Link from 'next/link';
import { Card } from '../ui/Primitives';
import { NarrativeSummary } from '../../lib/uiTypes';

export function NarrativeCard({ narrative }: { narrative: NarrativeSummary }) {
  // 1. Reliability Logic: Only STRONG/MODERATE should appear ideally.
  const isStrong = narrative.reliability_label === "STRONG";

  // 2. Lifecycle Visuals
  // "Lifecycle should be conveyed by... textual indicator... optional minimal progress bar/dot"
  const stateColors: Record<string, string> = {
    EMERGING: "text-secondary",
    ACTIVE: "text-strong",
    SATURATED: "text-secondary",
    FADING: "text-tertiary",
    DORMANT: "text-tertiary"
  };

  const stateLabel = narrative.state;
  
  // 3. Time Context: "Active for X hours/days"
  const now = new Date();
  const firstSeen = new Date(narrative.first_seen_at);
  const diffMs = now.getTime() - firstSeen.getTime();
  const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHrs / 24);
  
  let timeContext = "";
  if (diffDays > 0) {
    timeContext = `Active for ${diffDays}d`;
  } else {
    timeContext = `Active for ${diffHrs}h`;
  }

  const isPrimary = narrative.id === 'primary'; // Example logic to identify primary narrative

  const cardClass = isPrimary
    ? "flex flex-col gap-3 p-4 bg-surface border border-border/50 shadow-soft text-primary font-bold"
    : "flex flex-col gap-3 p-4 bg-surface border border-border/50 shadow-soft opacity-80";

  const primaryLabel = isPrimary ? (
    <span className="text-xs text-secondary font-mono">Primary narrative</span>
  ) : null;

  return (
    <Link href={`/narrative/${narrative.id}`} className="block mb-3 active:scale-[0.99] transition-transform duration-100 touch-manipulation">
      <Card className={cardClass}>
        {primaryLabel}
        <div className="flex justify-between items-center text-xxs font-mono tracking-wider">
          <div className="flex items-center gap-2">
            <span className={`uppercase font-semibold ${stateColors[narrative.state] || 'text-secondary'}`}>
              {stateLabel}
            </span>
             <span className="text-tertiary">
               •
             </span>
             <span className="text-tertiary">{timeContext}</span>
          </div>
          <div className={`flex items-center space-x-1.5 ${isStrong ? 'opacity-100' : 'opacity-80'}`}>
             <div className={`w-1.5 h-1.5 rounded-full ${isStrong ? 'bg-strong' : 'bg-moderate'}`} />
             <span className={`${isStrong ? 'text-strong' : 'text-moderate'} font-medium`} title={narrative.reliability_label === 'STRONG' ? 'High consistency across trusted sources.' : 'Partial confirmation with remaining uncertainty.'}>
               {narrative.reliability_label === 'WEAK' ? 'Low confirmation' : narrative.reliability_label}
             </span>
          </div>
        </div>
        <h3 className={`font-sans text-sm font-medium leading-relaxed tracking-wide ${isStrong ? 'text-primary' : 'text-secondary'}`}>
          {narrative.topic}
        </h3>
      </Card>
    </Link>
  )
}
