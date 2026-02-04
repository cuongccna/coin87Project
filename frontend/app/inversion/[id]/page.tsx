// Client -> Server component mismatch fix if needed, but this is a page, so standard async RSC is fine.
import { fetchInversionFeed } from "../../../lib/api/inversionApi";
import Link from "next/link";
import { notFound } from "next/navigation";

export default async function FeedDetailPage({ params }: { params: { id: string } }) {
  try {
    const feed = await fetchInversionFeed(params.id);
    // Payload from new Promote logic
    const p = feed.payload || {};
    
    // Risk Mapping
    const riskLevel = p.narrative_risk || feed.direction;
    const isHighRisk = riskLevel && riskLevel.toLowerCase() === 'high';
    const isMediumRisk = riskLevel && riskLevel.toLowerCase() === 'medium';
    
    // Theme colors based on risk
    const borderColor = isHighRisk ? 'border-red-600' : isMediumRisk ? 'border-yellow-600' : 'border-indigo-600';
    const bgColor = isHighRisk ? 'bg-red-950/20' : isMediumRisk ? 'bg-yellow-950/20' : 'bg-indigo-950/20';
    
    const trappedPersona = p.trapped_persona || "Impulse traders acting on headlines.";
    const expectationGap = p.expectation_gap || "Wait for volume confirmation.";
    const riskScore = Math.min(5, Math.max(1, p.iri_score || 3));
    const confidencePercent = Math.round((riskScore / 5) * 100);

    return (
      <main className="max-w-4xl mx-auto p-4 sm:p-6 md:p-8 space-y-4 sm:space-y-6">
        {/* Navigation */}
        <div className="flex items-center gap-4 text-sm font-medium">
            <Link href="/inversion" className="text-tertiary hover:text-white transition">&larr; Back to Inversion Feed</Link>
        </div>

        {/* HERO SECTION: The Judgement / Insight */}
        <div className={`relative border-l-4 ${borderColor} ${bgColor} pl-4 sm:pl-6 py-4 sm:py-6 rounded-r-lg shadow-lg`}>
            <div className="absolute top-4 right-4">
                 <span className={`px-2 sm:px-3 py-1 text-xs font-bold uppercase tracking-widest border rounded
                    ${isHighRisk ? 'text-red-200 border-red-800 bg-red-900/60' : 
                      isMediumRisk ? 'text-yellow-200 border-yellow-800 bg-yellow-900/60' :
                      'text-green-200 border-green-800 bg-green-900/40'}`}>
                    {p.narrative_risk || 'Standard Analysis'}
                 </span>
            </div>
            
            <h1 className="text-xl sm:text-2xl md:text-3xl lg:text-4xl font-bold text-white mb-3 sm:mb-4 leading-tight pr-24 sm:pr-32">
                {p.inversion_summary || "Automated market consensus detected."}
            </h1>
            
            <div className="flex flex-col gap-2 mt-3 sm:mt-4 max-w-2xl">
                 <div className="flex items-start gap-2">
                     <span className="text-tertiary font-bold uppercase text-xs mt-1 flex-shrink-0">Hint:</span>
                     <span className="text-tertiary italic text-sm">
                        "If you act now, you’re likely reacting to information already priced in."
                     </span>
                </div>
            </div>
        </div>

        {/* TRAPPED BOX */}
        <div className="bg-surface/50 border border-red-900/30 rounded-lg p-4 sm:p-5 flex gap-4 items-start sm:items-center">
            <div className="bg-red-900/20 p-2 rounded text-xl sm:text-2xl flex-shrink-0">☠️</div>
            <div className="flex-1">
                <h3 className="text-xs font-bold text-red-400 uppercase tracking-widest mb-1">Who Gets Trapped?</h3>
                <p className="text-gray-300 text-sm font-medium">
                    {trappedPersona}
                </p>
            </div>
        </div>

        {/* MID SECTION: Context & Expectation Gap (Responsive Grid) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
            <div className="bg-surface border border-border rounded-lg p-4 sm:p-5">
                <h3 className="text-xs sm:text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Narrative Context</h3>
                <p className="text-base sm:text-lg font-medium text-white mb-2 line-clamp-3">
                    "{p.title || 'No title available'}"
                </p>
                <div className="text-xs sm:text-sm text-tertiary mb-4">
                    Source: <span className="text-primary font-medium">{p.source}</span>
                </div>
                <div className="pt-4 border-t border-border/30">
                     <div className="flex justify-between items-center">
                        <span className="text-xs uppercase text-tertiary">Risk Confidence</span>
                        <span className="text-lg sm:text-xl font-bold text-white">
                             {confidencePercent}%
                        </span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">(Based on Risk Index: {riskScore}/5)</div>
                </div>
            </div>

            <div className="bg-surface border border-border rounded-lg p-4 sm:p-5 flex flex-col justify-start">
                 <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xs sm:text-sm font-bold text-indigo-400 uppercase tracking-wider">Expectation Gap</h3>
                    <span className="text-lg sm:text-xl">📊</span>
                 </div>
                 
                 <div className="space-y-3 sm:space-y-4">
                    <div>
                        <span className="text-xs font-bold text-gray-500 uppercase block mb-1">Expectation Gap (AI Analysis):</span>
                         <div className="text-xs sm:text-sm text-gray-300 pl-2 border-l-2 border-green-500/30">
                            {/* If dynamic mechanism is present (not default), show it as primary */}
                            {expectationGap !== "Wait for volume confirmation." ? (
                                <p className="text-white font-medium">"{expectationGap}"</p>
                            ) : (
                                <>
                                    <p className="mb-1">Generic Validation:</p>
                                    <ul className="list-disc pl-4 space-y-1 opacity-80">
                                        <li>Sustained Volume Spike</li>
                                        <li>Spot Buying Dominance</li>
                                    </ul>
                                </>
                            )}
                        </div>
                    </div>
                    {/* Only show 'What to Watch' if we have extra tips (optional, simplified for now) */}
                 </div>
            </div>
        </div>

        {/* BOTTOM SECTION: Raw Metadata (Collapsible) */}
        <details className="pt-6 sm:pt-8 border-t border-border/20 group cursor-pointer">
            <summary className="text-xs font-bold text-tertiary uppercase tracking-wider cursor-pointer hover:text-primary transition">
                + Raw Inversion Data (Click to expand)
            </summary>
             <div className="mt-4 space-y-3">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono text-gray-500">
                    <div>ID: {feed.id.slice(0, 8)}...</div>
                    <div>Created: {new Date(feed.created_at).toLocaleDateString()}</div>
                    <div>Risk Score: {p.iri_score || 'N/A'}/5</div>
                </div>
                
                <div className="p-3 bg-surface_highlight/20 rounded border border-border/30 overflow-x-auto">
                    <pre className="text-[10px] text-tertiary">
                        {JSON.stringify(feed, null, 2)}
                    </pre>
                </div>
             </div>
        </details>

      </main>
    );
  } catch (e) {
    notFound();
  }
}
