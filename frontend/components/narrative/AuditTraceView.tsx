import { Badge, Card } from '../ui/Primitives';

interface AuditFactor {
  [key: string]: string;
}

interface AuditTrace {
  id: string;
  summary: string;
  type: string;
  factors: AuditFactor;
  timestamp: string;
}

export function AuditTraceView({ traces }: { traces: AuditTrace[] }) {
  if (!traces.length) return null;

  return (
    <div className="mt-6">
      <h3 className="text-xs font-mono uppercase text-tertiary mb-3">Reliability Audit</h3>
      <div className="space-y-3">
        {traces.map((trace) => (
          <div key={trace.id} className="relative pl-4 border-l border-border pb-1">
            <div className="absolute -left-[3px] top-1.5 w-1.5 h-1.5 rounded-full bg-tertiary" />
            
            <div className="text-xxs text-tertiary font-mono mb-1">
               {new Date(trace.timestamp).toLocaleDateString()} {trace.type.replace('_', ' ')}
            </div>
            
            <p className="text-sm text-secondary mb-2">{trace.summary}</p>
            
            <div className="flex flex-wrap gap-2">
              {Object.entries(trace.factors).map(([k, v]) => (
                <span key={k} className="inline-flex items-center px-1.5 py-0.5 rounded bg-surface_highlight text-xxs text-tertiary border border-border/50">
                  <span className="opacity-70 mr-1">{k}:</span> {v}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
