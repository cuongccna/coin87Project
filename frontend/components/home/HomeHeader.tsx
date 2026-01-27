import { HomeSnapshot } from '../../lib/uiTypes';

export function HomeHeader({ snapshot }: { snapshot: HomeSnapshot }) {
  return (
    <div className="px-4 py-6 border-b border-border bg-background">
      <div className="flex justify-between items-end mb-4">
        <div>
          <h1 className="text-secondary text-sm font-medium tracking-wide">COIN87</h1>
          <div className="text-xxs text-tertiary font-mono mt-1">
             UPDATED {new Date(snapshot.last_updated_at).toLocaleTimeString()}
          </div>
        </div>
        <div className="text-right">
           <div className="text-2xl font-light text-primary tracking-tight">
             {snapshot.active_narratives_count}
           </div>
           <div className="text-xxs text-tertiary uppercase tracking-wider">Active Narratives</div>
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        <div className="h-1 flex-1 bg-surface_highlight rounded-full overflow-hidden">
          <div 
            className="h-full bg-secondary/50 rounded-full transition-all duration-500"
            style={{ width: `${snapshot.clarity_score}%` }} 
          />
        </div>
        <span className="text-xxs text-secondary font-mono">
          CLARITY {snapshot.clarity_score}%
        </span>
      </div>
    </div>
  )
}
