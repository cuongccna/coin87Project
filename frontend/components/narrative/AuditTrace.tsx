
import { AuditTraceItem } from "../../lib/types";

export function AuditTrace({ items }: { items?: AuditTraceItem[] }) {
  if (!items || items.length === 0) {
    return (
      <div className="bg-surface/30 border border-border/50 rounded-lg p-6 text-center">
        <p className="text-tertiary text-sm italic">
          No audit trace available for this narrative.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-surface border border-border/50 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="bg-surface_highlight border-b border-border/50 text-xs text-tertiary font-mono uppercase tracking-wider">
          <tr>
            <th className="px-4 py-3 font-medium">Time (UTC)</th>
            <th className="px-4 py-3 font-medium">Source</th>
            <th className="px-4 py-3 font-medium">Event / Headline</th>
            <th className="px-4 py-3 font-medium text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/30">
          {items.map((item) => (
            <tr key={item.event_id} className="hover:bg-white/5 transition-colors">
              <td className="px-4 py-3 whitespace-nowrap text-tertiary font-mono text-xs">
                {new Date(item.created_at).toLocaleString('en-GB', { 
                    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false 
                })}
              </td>
              <td className="px-4 py-3 whitespace-nowrap">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-900/30 text-indigo-300 border border-indigo-800/50">
                  {item.source}
                </span>
              </td>
              <td className="px-4 py-3 max-w-md">
                 <div className="text-gray-300 font-medium truncate" title={item.title}>
                    {item.title}
                 </div>
              </td>
              <td className="px-4 py-3 text-right whitespace-nowrap">
                {item.url ? (
                  <a 
                    href={item.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-xs text-indigo-400 hover:text-indigo-300 hover:underline"
                  >
                    Open Source ↗
                  </a>
                ) : (
                  <span className="text-tertiary text-xs">-</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      
      {items.length >= 50 && (
          <div className="bg-surface_highlight/30 px-4 py-2 text-center text-xxs text-tertiary border-t border-border/30">
              Showing last 50 events. Older events are archived.
          </div>
      )}
    </div>
  );
}
