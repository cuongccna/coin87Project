import Link from 'next/link';
import { HomeSnapshot } from '../../lib/uiTypes';

export function HomeHeader({ snapshot }: { snapshot: HomeSnapshot }) {
  return (
    <div className="px-4 py-6 border-b border-border bg-background">
      <div className="flex justify-between items-end mb-4">
        <div>
          <h1 className="text-secondary text-sm font-medium tracking-wide" title="System-level narratives with sufficient confirmation.">COIN87</h1>
          <div className="text-xxs text-tertiary font-mono mt-1">
            UPDATED {new Date(snapshot.last_updated_at).toLocaleString('en-US', { timeZone: 'Asia/Bangkok', hour12: false })} UTC+7
          </div>
        </div>
        <div className="text-right">
           <div className="text-2xl font-light text-primary tracking-tight" title="System-level narratives with sufficient confirmation.">
             {snapshot.active_narratives_count}
           </div>
           <div className="text-xxs text-tertiary uppercase tracking-wider">Active Narratives</div>
           {process.env.NEXT_PUBLIC_FEATURE_INVERSION === 'true' && (
             <div className="mt-2">
               <Link href="/inversion" className="text-xxs text-indigo-600 hover:underline">Inversion Feeds</Link>
             </div>
           )}
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        <div className="h-1 flex-1 bg-surface_highlight rounded-full overflow-hidden">
          <div 
            className="h-full bg-secondary/50 rounded-full transition-all duration-500"
            style={{ width: `${snapshot.clarity_score}%` }} 
            title="Indicates how coherent current information is."
          />
        </div>
        <span className="text-xxs text-secondary font-mono" title="Indicates how coherent current information is.">
          Clarity: {Math.round(snapshot.clarity_score)}%
        </span>
      </div>
    </div>
  )
}
