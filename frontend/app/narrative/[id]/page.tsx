import Link from 'next/link';
import { Badge, Card } from '../../../components/ui/Primitives';
import { api } from '../../../lib/api';
import { NarrativeDetailResponse } from '../../../lib/types'; // Ensure exported or types reference

// Helper to format date
const formatDate = (date: string | Date) => new Date(date).toLocaleDateString(undefined, { 
  year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' 
});

export default async function NarrativeDetailPage({ params }: { params: { id: string } }) {
  let n: NarrativeDetailResponse;
  
  try {
     n = await api.getNarrativeDetail(params.id);
  } catch (err) {
    return (
        <main className="min-h-screen bg-background text-primary pb-safe p-4">
             <div className="text-secondary">Narrative not found or error loading data.</div>
             <Link href="/" className="text-tertiary hover:text-primary mt-4 block">← Back to Dashboard</Link>
        </main>
    )
  }

  return (
    <main className="min-h-screen bg-background text-primary pb-safe">
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur border-b border-border px-4 py-4 flex items-center gap-4">
        <Link href="/" className="text-tertiary hover:text-primary transition-colors">
          ← Back
        </Link>
        <span className="text-xs font-mono text-tertiary uppercase truncate">
          Narrative Detail
        </span>
      </div>

      <div className="px-4 py-6">
        <div className="mb-6">
          <div className="flex flex-wrap gap-2 mb-3">
             <Badge variant={n.status === "ACTIVE" ? "strong" : "neutral"}>{n.status}</Badge>
             <Badge variant="neutral">SATURATION: {n.saturation_level}/5</Badge>
          </div>
          <h1 className="text-lg font-medium leading-relaxed text-strong mb-4">
            {n.theme}
          </h1>
          <p className="text-secondary text-sm leading-relaxed">
            First detected: {formatDate(n.first_seen_at)} <br/>
            Last active: {formatDate(n.last_seen_at)}
          </p>
        </div>

        <div className="mb-8">
          <h3 className="text-xs font-mono uppercase text-tertiary mb-3">Linked Risks</h3>
          {n.linked_risks.length === 0 ? (
             <div className="text-sm text-tertiary italic">No specific risk events linked to this narrative.</div>
          ) : (
            <div className="space-y-3">
                {n.linked_risks.map((risk, idx) => (
                <Card key={idx} className="bg-surface/50">
                    <div className="flex justify-between items-start mb-2">
                    <div className="text-sm text-primary font-bold">{risk.risk_type}</div>
                    </div>
                    <div className="flex items-center gap-3">
                        <Badge variant={risk.severity >= 4 ? "strong" : "neutral"}>
                        SEVERITY {risk.severity}
                        </Badge>
                        <span className="text-xs text-tertiary">Posture: {risk.recommended_posture}</span>
                    </div>
                    <div className="mt-2 text-xs text-secondary">
                        Valid: {formatDate(risk.valid_from)}
                    </div>
                </Card>
                ))}
            </div>
          )}
        </div>
        
        {/* Placeholder for future expansion */}
        <div className="mb-8 opacity-50">
             <h3 className="text-xs font-mono uppercase text-tertiary mb-3">Audit Trace</h3>
             <div className="text-xs text-tertiary border border-dashed border-border p-3 rounded">
                Audit trail not available in current release.
             </div>
        </div>
      </div>
    </main>
  );
}
