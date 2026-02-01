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

    return (
      <main className="max-w-4xl mx-auto p-4 md:p-8 space-y-6">
        {/* Navigation */}
        <div className="flex items-center gap-4 text-sm font-medium">
            <Link href="/inversion" className="text-tertiary hover:text-white transition">&larr; Back to Inversion Feed</Link>
        </div>

        {/* HERO SECTION: The Judgement / Insight */}
        <div className={`relative border-l-4 ${borderColor} ${bgColor} pl-6 py-6 rounded-r-lg shadow-lg`}>
            <div className="absolute top-4 right-4">
                 <span className={`px-3 py-1 text-xs font-bold uppercase tracking-widest border rounded
                    ${isHighRisk ? 'text-red-200 border-red-800 bg-red-900/60' : 
                      isMediumRisk ? 'text-yellow-200 border-yellow-800 bg-yellow-900/60' :
                      'text-green-200 border-green-800 bg-green-900/40'}`}>
                    {p.narrative_risk || 'Standard Analysis'}
                 </span>
            </div>
            
            <h1 className="text-3xl font-bold text-white mb-2 leading-tight pr-32">
                {p.inversion_summary || "Automated market consensus detected."}
            </h1>
            
            <div className="flex flex-col gap-2 mt-4 max-w-2xl">
                <div className="flex items-start gap-2">
                     <span className="text-indigo-400 font-bold uppercase text-xs mt-1 w-24 flex-shrink-0">Why Shown:</span>
                     <span className="text-gray-200 font-medium">{p.why_shown || "Informational update"}</span>
                </div>
                 <div className="flex items-start gap-2">
                     <span className="text-tertiary font-bold uppercase text-xs mt-1 w-24 flex-shrink-0">Inversion Hint:</span>
                     <span className="text-tertiary italic">
                        "If you act now, you’re likely reacting to information already priced in."
                     </span>
                </div>
            </div>
        </div>

        {/* TRAPPED BOX (Jewish Logic) */}
        <div className="bg-surface/50 border border-red-900/30 rounded-lg p-4 flex gap-4 items-center">
            <div className="bg-red-900/20 p-2 rounded text-2xl">☠️</div>
            <div>
                <h3 className="text-xs font-bold text-red-400 uppercase tracking-widest mb-1">Who Gets Trapped?</h3>
                <p className="text-gray-300 text-sm font-medium">
                    {trappedPersona}
                </p>
            </div>
        </div>

        {/* MID SECTION: Context & Expectation Gap */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-surface border border-border rounded-lg p-5">
                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Narrative Context</h3>
                <p className="text-lg font-medium text-white mb-2">
                    "{p.title || 'No title available'}"
                </p>
                <div className="text-sm text-tertiary">
                    Source: <span className="text-primary">{p.source}</span>
                </div>
                <div className="mt-4 pt-4 border-t border-border/30">
                     <div className="flex justify-between items-center">
                        <span className="text-xs uppercase text-tertiary">Inversion Assessment Confidence</span>
                        <span className="text-xl font-bold text-white">
                             {((feed.confidence || 0.8) * 100).toFixed(0)}%
                        </span>
                    </div>
                </div>
            </div>

            <div className="bg-surface border border-border rounded-lg p-5 flex flex-col justify-start">
                 <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-indigo-400 uppercase tracking-wider">Expectation Gap</h3>
                    <span className="text-xl">📊</span>
                 </div>
                 
                 <div className="space-y-4">
                    <div>
                        <span className="text-xs font-bold text-gray-500 uppercase block mb-1">Expected if Narrative True:</span>
                        <div className="text-sm text-gray-300 pl-2 border-l-2 border-green-500/30">
                            • Sustained Volume Spike<br/>
                            • Spot Buying Dominance
                        </div>
                    </div>
                     <div>
                        <span className="text-xs font-bold text-gray-500 uppercase block mb-1">What to Watch (The Trap):</span>
                        <div className="text-sm text-white font-medium pl-2 border-l-2 border-red-500/50">
                            "{expectationGap}"
                        </div>
                    </div>
                 </div>
            </div>
        </div>

        {/* BOTTOM SECTION: Raw Metadata */}
        <div className="pt-8 border-t border-border/20">
             <h3 className="text-xs font-bold text-tertiary uppercase tracking-wider mb-4">Raw Inversion Data</h3>
             <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono text-gray-500">
                <div>ID: {feed.id.slice(0, 8)}...</div>
                <div>Created: {new Date(feed.created_at).toLocaleString()}</div>
                <div>Risk Score: {p.iri_score || 'N/A'}/5</div>
             </div>
             
             <div className="mt-4 p-4 bg-surface_highlight/30 rounded border border-border/30 overflow-x-auto">
                <pre className="text-[10px] text-tertiary">
                    {JSON.stringify(feed, null, 2)}
                </pre>
             </div>
        </div>

      </main>
    );
  } catch (e) {
    notFound();
  }
}
