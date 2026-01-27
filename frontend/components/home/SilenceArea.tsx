'use client';

/*
 * COMPONENT: Silence Area
 * -----------------------
 * DESIGN RATIONALE (MANIFESTO LOCK):
 * 
 * 1. "Silence is intentional suppression of noise."
 *    - This component creates a designated separate space for low-value info.
 *    - It reduces cognitive load by hiding noise by default.
 *
 * 2. Visual Hierarchy:
 *    - De-emphasized typography (text-tertiary, smaller).
 *    - No badges, no bright colors.
 *    - Interactions are "high friction" (text click) to discourage casual browsing.
 * 
 * 3. Ethics:
 *    - We show this data to avoid accusations of censorship.
 *    - But we frame it as "Completeness only".
 */

import { useState } from 'react';
import { NarrativeSummary } from '../../lib/uiTypes';
import { Card } from '../ui/Primitives';

interface SilenceAreaProps {
  ignoredNarratives: NarrativeSummary[];
}

export function SilenceArea({ ignoredNarratives }: SilenceAreaProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedItem, setSelectedItem] = useState<NarrativeSummary | null>(null);

  if (!ignoredNarratives || ignoredNarratives.length === 0) return null;

  return (
    <section className="mt-12 px-4 pb-12 border-t border-border/30 pt-8">
      
      {/* 1. Toggle / Header (Text Affordance Only) */}
      <div className="flex justify-center">
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-xs font-mono text-tertiary/70 hover:text-tertiary hover:underline transition-colors focus:outline-none"
        >
          {isExpanded ? "Hide ignored information" : "Ignored information"}
        </button>
      </div>

      {/* 2. Expanded Content */}
      {isExpanded && (
        <div className="mt-6 max-w-lg mx-auto animate-in fade-in slide-in-from-top-2 duration-300">
          
          {/* Explanation */}
          <p className="text-center text-xs text-tertiary mb-6 px-8 leading-relaxed">
            These items were evaluated as low information value<br className="hidden sm:block"/> 
            and are not included in the main view.
          </p>

          {/* List of Suppressed Narratives */}
          <div className="space-y-1">
            {ignoredNarratives.map(item => (
              <div 
                key={item.id}
                onClick={() => setSelectedItem(item)}
                className="group cursor-pointer py-2 px-3 rounded-md hover:bg-surface_highlight transition-colors flex justify-between items-center"
              >
                <span className="text-sm text-secondary group-hover:text-primary transition-colors truncate">
                  {item.topic}
                </span>
                {/* Minimal arrow, hidden by default only shown on hover to reduce noise */}
                <span className="text-tertiary/0 group-hover:text-tertiary text-xs transition-opacity">
                  →
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Minimal Detail Modal (Internal) */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/90 backdrop-blur-[2px]" onClick={() => setSelectedItem(null)}>
          <div 
            className="bg-surface border border-border/50 shadow-lg max-w-xs w-full p-6 text-center rounded-lg"
            onClick={e => e.stopPropagation()}
          >
            <h4 className="text-sm font-medium text-secondary mb-2">
              {selectedItem.topic}
            </h4>
            
            <p className="text-xs text-tertiary mb-6 italic">
              This information is shown for completeness only.
            </p>

            <button 
              onClick={() => setSelectedItem(null)}
              className="text-xs text-primary border border-border px-4 py-2 rounded hover:bg-surface_highlight transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
