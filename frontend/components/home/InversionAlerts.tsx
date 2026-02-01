
import Link from 'next/link';
import { fetchInversionFeeds } from '../../lib/api/inversionApi';

export async function InversionAlerts() {
  // Fetch only HIGH and MEDIUM risk items
  // We can't filter multiple values in one query param usually unless API supports it.
  // We'll fetch 'HIGH' first. If empty, maybe 'MEDIUM'. Or just fetch recent and filter client side (but component is server side).
  // The API supports narrative_risk filtering.
  // Let's try to fetch HIGH first.
  
  let alerts = [];
  try {
      const highRes = await fetchInversionFeeds({ narrative_risk: 'HIGH', limit: 3 });
      alerts = [...highRes.items];
      
      if (alerts.length < 2) {
          const mediumRes = await fetchInversionFeeds({ narrative_risk: 'MEDIUM', limit: 3 - alerts.length });
          alerts = [...alerts, ...mediumRes.items];
      }
  } catch (e) {
      console.error("Failed to fetch inversion alerts", e);
      return null;
  }

  if (alerts.length === 0) return null;

  return (
    <div className="mx-4 mt-6 border border-yellow-800/50 bg-yellow-900/10 rounded-lg p-3">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-xs font-bold text-yellow-500 uppercase tracking-wider flex items-center gap-2">
           <span className="text-sm">⚠️</span> Inversion Alerts (Today)
        </h3>
        <Link href="/inversion?narrative_risk=HIGH" className="text-xxs text-yellow-600/70 hover:text-yellow-400 font-mono flex items-center gap-1 transition-colors">
          VIEW ALL →
        </Link>
      </div>

      <div className="mb-3 pl-0.5">
         <p className="text-xxs text-yellow-700 font-medium italic opacity-70 leading-tight">
            Signals where narrative leads price, not capital.
         </p>
      </div>

      <div className="flex flex-col gap-2">
         {alerts.map(item => (
             <Link href={`/inversion/${item.id}`} key={item.id} className="block group">
                 <div className="flex justify-between items-start">
                    <span className="text-xs text-gray-300 font-medium group-hover:text-white transition-colors line-clamp-1">
                      • {item.payload?.inversion_summary ?? item.payload?.title ?? item.source_id ?? `Feed ${item.id}`}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border ml-2 whitespace-nowrap ${
                        (item.payload?.narrative_risk || 'LOW').toUpperCase() === 'HIGH' 
                        ? 'bg-red-900/40 border-red-800 text-red-300' 
                        : 'bg-yellow-900/40 border-yellow-800 text-yellow-300'
                    }`}>
                        {(item.payload?.narrative_risk || 'MEDIUM').toUpperCase()}
                    </span>
                 </div>
             </Link>
         ))}
      </div>
      
      <div className="mt-2 text-xxs text-yellow-700/70 border-t border-yellow-900/30 pt-1.5 font-mono">
         {alerts.length} narratives show capital–narrative divergence
      </div>
    </div>
  );
}
