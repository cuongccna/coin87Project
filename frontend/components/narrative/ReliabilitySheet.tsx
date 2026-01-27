/*
 * COMPONENT: Reliability Explanation Sheet
 * ----------------------------------------
 * DESIGN RATIONALE (MANIFESTO LOCK):
 * 
 * 1. Interaction: 
 *    - Accessibility is deliberately high-friction (Long-press/Explicit action).
 *    - Purpose: Prevent users from checking reliability scores obsessively.
 *    - "Transparency builds trust only when it is restrained."
 *
 * 2. Visuals:
 *    - No score gauges or color-coded progressive bars.
 *    - Plain text priority to force reading over scanning.
 *    - Muted colors (Zinc) to lower emotional valence.
 *
 * 3. Copy:
 *    - "Why this is shown" instead of "Reliability Report".
 *    - Focus on *process* (verification, consensus) rather than *outcome* (price, truth).
 *    - Bullet points limited to 4 to prevent information overload.
 */

import { useEffect, useState } from 'react';
import { NarrativeSummary } from '../../lib/uiTypes';

interface ReliabilitySheetProps {
  narrative: NarrativeSummary | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ReliabilitySheet({ narrative, isOpen, onClose }: ReliabilitySheetProps) {
  const [isVisible, setIsVisible] = useState(false);

  // Handle animation states
  useEffect(() => {
    if (isOpen) {
      setIsVisible(true);
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
    } else {
      const timer = setTimeout(() => setIsVisible(false), 300); // Match transition duration
      document.body.style.overflow = 'unset';
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  if (!isVisible && !isOpen) return null;
  if (!narrative) return null;

  // --- CONTENT MAPPING LOGIC (Locked per Manifesto) ---

  // 1. Reliability Summary
  const getSummaryText = (n: NarrativeSummary) => {
    switch (n.reliability_label) {
      case 'STRONG':
        return "This information has been independently verified by multiple high-trust sources.";
      case 'MODERATE':
        return "This narrative is credible but is still developing or relies on fewer sources.";
      case 'WEAK':
        return "Information is limited or contains contradictions. Review with caution.";
      case 'NOISE':
        return "This pattern appears to be market noise.";
      default:
        return "Reliability analysis is pending.";
    }
  };

  // 2. Contributing Factors (Bullet List)
  const getFactors = (n: NarrativeSummary) => {
    const factors = [];
    const meta = n.explanation_metadata;

    if (!meta) return ["Standard reliability checks passed."];

    // Factor: Consensus
    if (meta.consensus_level === 'high') {
      factors.push("Confirmed by multiple independent sources");
    } else if (meta.consensus_level === 'medium') {
      factors.push("Partial consensus among sources");
    }

    // Factor: Diversity
    if (meta.source_diversity === 'broad') {
      factors.push("Sources from different sectors align");
    }

    // Factor: Stability
    if (n.state === 'ACTIVE' || n.state === 'SATURATED') {
       if (meta.is_steady) {
         factors.push("Information persisted over several hours");
       }
    }
    
    // Factor: Contradictions
    if (meta.has_contradictions) {
      factors.push("Some conflicting reports observed");
    } else if (n.reliability_label === 'STRONG') {
      factors.push("No significant contradictions observed");
    }

    return factors.slice(0, 4); // Max 4
  };

  // 3. Time Context
  const getTimeContext = (n: NarrativeSummary) => {
    const now = new Date();
    const firstSeen = new Date(n.first_seen_at);
    const diffMs = now.getTime() - firstSeen.getTime();
    const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffHrs < 1) return "Observed for less than 1 hour";
    if (diffHrs > 24) return `Observed for ${Math.floor(diffHrs/24)} days`;
    return `Observed for ${diffHrs} hours`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div 
        className={`absolute inset-0 bg-background/80 backdrop-blur-sm transition-opacity duration-300 ${isOpen ? 'opacity-100' : 'opacity-0'}`}
        onClick={onClose}
      />

      {/* Sheet Content */}
      <div className={`
        relative w-full max-w-md bg-surface border-t border-border shadow-2xl p-6 pb-10 sm:rounded-lg sm:border sm:pb-6
        transition-transform duration-300 ease-out transform
        ${isOpen ? 'translate-y-0' : 'translate-y-full sm:translate-y-10 sm:opacity-0'}
      `}>
        {/* Drag Handle (Mobile visual cue) */}
        <div className="w-12 h-1.5 bg-border rounded-full mx-auto mb-6 sm:hidden" />

        <div className="space-y-6">
          {/* Header */}
          <div className="flex justify-between items-start">
            <h2 className="text-lg font-semibold text-primary tracking-tight">
              Why this is shown
            </h2>
            <button 
              onClick={onClose}
              className="p-2 -mr-2 text-tertiary hover:text-primary transition-colors touch-manipulation"
              aria-label="Close"
            >
              ✕
            </button>
          </div>

          {/* Reliability Summary */}
          <div className="p-4 bg-background rounded-md border border-border/50">
             <div className="flex items-center gap-2 mb-2">
               <div className={`w-2 h-2 rounded-full ${
                 narrative.reliability_label === 'STRONG' ? 'bg-strong' : 
                 narrative.reliability_label === 'MODERATE' ? 'bg-moderate' : 'bg-weak'
               }`} />
               <span className="text-xs font-mono uppercase text-tertiary">
                 {narrative.reliability_label} Signal
               </span>
             </div>
             <p className="text-sm text-primary leading-relaxed">
               {getSummaryText(narrative)}
             </p>
          </div>

          {/* Contributing Factors */}
          <div>
            <h3 className="text-xs font-mono uppercase text-tertiary mb-3 relative top-0.5">
              Contributing Factors
            </h3>
            <ul className="space-y-3">
              {getFactors(narrative).map((factor, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-secondary">
                  <span className="block w-1 h-1 mt-2 rounded-full bg-tertiary/50" />
                  {factor}
                </li>
              ))}
            </ul>
          </div>

          {/* Footer / Time Context */}
          <div className="pt-4 border-t border-border/50">
            <p className="text-xs text-tertiary text-center font-mono">
              {getTimeContext(narrative)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
