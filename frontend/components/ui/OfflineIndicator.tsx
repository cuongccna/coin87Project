'use client';

import { useEffect, useState } from 'react';

export function OfflineIndicator({ lastUpdated }: { lastUpdated: string }) {
  const [isOffline, setIsOffline] = useState(false);
  const [timeAgo, setTimeAgo] = useState("");

  useEffect(() => {
    // 1. Network Status Listeners
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Initial check
    setIsOffline(!navigator.onLine);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  useEffect(() => {
    // 2. Data Freshness Calculation (runs every minute)
    const updateTimeContext = () => {
      if (!lastUpdated) return;
      const diff = new Date().getTime() - new Date(lastUpdated).getTime();
      const diffMins = Math.floor(diff / 60000);
      
      if (diffMins < 1) setTimeAgo("just now");
      else if (diffMins < 60) setTimeAgo(`${diffMins}m ago`);
      else {
        const diffHrs = Math.floor(diffMins / 60);
        setTimeAgo(`${diffHrs}h ago`);
      }
    };

    updateTimeContext();
    const interval = setInterval(updateTimeContext, 60000);
    return () => clearInterval(interval);
  }, [lastUpdated]);

  // "No reliable information available yet" state is handled by parent if data empty.
  // Here we only show the status strip.

  if (!isOffline) return null;

  return (
    <div className="bg-surface_highlight border-b border-border py-1.5 px-4 text-center animate-in fade-in slide-in-from-top-1">
      <p className="text-xxs font-mono text-tertiary uppercase tracking-wider">
        Offline • Showing last update ({timeAgo})
      </p>
    </div>
  );
}
