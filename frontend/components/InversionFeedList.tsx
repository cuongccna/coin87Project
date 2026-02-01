// Client component
"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { InversionFeed } from "../lib/api/inversionTypes";
import Link from "next/link";

interface Props {
  initialItems: InversionFeed[];
  total: number;
  currentPage: number;
}

// Utility to render Risk Badge based on backend 'direction' or 'narrative_risk'
function RiskBadge({ level }: { level: string }) {
    const rawLevel = level ? level.toLowerCase() : 'low';
    
    if (rawLevel === 'high') {
        return (
            <span className="bg-red-900/50 text-red-200 border border-red-700 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wide">
               High Risk
            </span>
        );
    }
    if (rawLevel === 'medium') {
        return (
             <span className="bg-yellow-900/50 text-yellow-200 border border-yellow-700 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wide">
               Conflict
            </span>
        );
    }
    // Low / Info
    return (
        <span className="bg-green-900/40 text-green-200 border border-green-800 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wide">
           Info
        </span>
    );
}

function IRIDots({ score }: { score: number }) {
  const safeScore = Math.max(1, Math.min(5, score || 1));
  return (
  <div className="flex flex-col items-end gap-0.5 ml-2 group/risk cursor-help relative p-2 -mr-2 -mt-2 z-10">
    <span className="text-[9px] text-gray-500 uppercase tracking-tighter leading-none whitespace-nowrap">Risk Index</span>
    <div className="flex gap-0.5">
      {[...Array(5)].map((_, i) => (
        <span key={i} className={`text-[10px] leading-none ${i < safeScore ? 'text-indigo-400' : 'text-gray-800'}`}>
          ●
        </span>
      ))}
    </div>

    {/* Tooltip (shows on hover) */}
    <div className="absolute top-full right-0 mt-2 w-48 p-2.5 bg-gray-900 border border-gray-700 text-[11px] leading-snug text-gray-300 rounded-md shadow-2xl opacity-0 group-hover/risk:opacity-100 transition-opacity z-50 pointer-events-none">
      <span className="font-bold text-indigo-400 block mb-0.5">Risk Index</span>
      Likelihood this narrative leads to poor timing decisions
    </div>
  </div>
  );
}

export default function InversionFeedList({ initialItems, total, currentPage }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [symbol, setSymbol] = useState(searchParams.get("symbol") || "");
  const [status, setStatus] = useState(searchParams.get("status") || "");
  const [narrativeRisk, setNarrativeRisk] = useState(searchParams.get("narrative_risk") || "");
  const [newItemsCount, setNewItemsCount] = useState(0);

  // Realtime SSE Connection
  useEffect(() => {
    // Determine API Base URL
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';
    const cleanBaseUrl = baseUrl.replace(/\/$/, '');
    const sseUrl = `${cleanBaseUrl}/v1/inversion-stream`;

    console.log(`[InvStream] Connecting to ${sseUrl}`);
    const eventSource = new EventSource(sseUrl);

    eventSource.onopen = () => {
        console.log("[InvStream] Connection open");
    };

    eventSource.addEventListener("inversion_update", (event: MessageEvent) => {
        try {
            const data = JSON.parse(event.data);
            console.log("[InvStream] New Event:", data);
            setNewItemsCount((prev) => prev + 1);
        } catch (e) {
            console.error("[InvStream] Parse error", e);
        }
    });

    eventSource.onerror = (err) => {
        console.error("[InvStream] Connection error", err);
    };

    return () => {
        console.log("[InvStream] Closing connection");
        eventSource.close();
    };
  }, []); 

  const handleRefresh = () => {
    setNewItemsCount(0);
    router.refresh(); 
  };

  const handleFilter = () => {
    const params = new URLSearchParams();
    if (symbol) params.set("symbol", symbol);
    if (status) params.set("status", status);
    if (narrativeRisk) params.set("narrative_risk", narrativeRisk);
    params.set("page", "1"); 
    router.push(`/inversion?${params.toString()}`);
  };

  const handleNextPage = () => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(currentPage + 1));
    router.push(`/inversion?${params.toString()}`);
  }

  const handlePrevPage = () => {
    if (currentPage > 1) {
        const params = new URLSearchParams(searchParams.toString());
        params.set("page", String(currentPage - 1));
        router.push(`/inversion?${params.toString()}`);
    }
  }

  return (
    <div className="space-y-6">
      {/* Realtime Notification Bar */}
      {newItemsCount > 0 && (
        <div className="bg-gradient-to-r from-indigo-900 to-slate-900 border-indigo-700 border text-indigo-100 px-4 py-3 rounded-md flex justify-between items-center shadow-lg animate-pulse ring-1 ring-indigo-500">
            <span className="font-medium flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-green-400 inline-block animate-ping"></span>
                {newItemsCount} new Analysis available
            </span>
            <button 
                onClick={handleRefresh}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-1.5 rounded text-sm font-bold transition shadow-sm"
            >
                Load Latest
            </button>
        </div>
      )}

      {/* Filters (Simplified) */}
      <div className="flex gap-4 items-end bg-surface/50 p-4 rounded-lg border border-border/50">
        <div>
          <label className="block text-xs font-semibold text-tertiary uppercase tracking-wider mb-1">Symbol</label>
          <input
            type="text"
            className="w-24 bg-background border border-border rounded px-2 py-1 text-sm text-primary focus:outline-none focus:border-indigo-500"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="BTC"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-tertiary uppercase tracking-wider mb-1">Type</label>
          <select
            value={narrativeRisk}
            onChange={(e) => setNarrativeRisk(e.target.value)}
            className="bg-background border border-border rounded px-2 py-1 text-sm text-primary focus:outline-none"
          >
            <option value="">All</option>
            <option value="LOW">INFO</option>
            <option value="MEDIUM">CONFLICT</option>
            <option value="HIGH">HIGH RISK</option>
          </select>
        </div>
        <button
          onClick={handleFilter}
          className="px-4 py-1 h-8 bg-indigo-600 text-white rounded hover:bg-indigo-700 text-xs font-bold uppercase"
        >
          Filter
        </button>
      </div>

      {/* List - The Inversion Card Layout */}
      <div className="flex flex-col gap-4">
        {initialItems.map((item) => {
            // Safe accessors for new payload fields
            const p = item.payload || {};
            const summary = p.inversion_summary || "Automated market monitoring active.";
            const whyShown = p.why_shown || "Informational update";
            const riskLevel = p.narrative_risk || item.direction; // fallback
            const iriScore = p.iri_score || 1;
            const feedIcon = p.feed_icon || 'ℹ️';
            
            // Visual Style Check: INFO feeds are dimmed
            const isInfo = riskLevel.toLowerCase() === 'low';
            const cardOpacity = isInfo ? "bg-surface/40 hover:bg-surface/80 border-border/50" : "bg-surface border-border";
            const iconOpacity = isInfo ? "opacity-50 grayscale" : "opacity-100";

            return (
                <div key={item.id} className={`relative group border rounded-lg p-5 hover:border-indigo-500/50 transition-all duration-300 shadow-sm ${cardOpacity}`}>
                    {/* Top Row: Symbol & Risk Badge */}
                    <div className="flex justify-between items-start mb-3">
                        <div className="flex items-center gap-3">
                            <h3 className="text-xl font-bold tracking-tight text-white">{item.symbol}</h3>
                            <RiskBadge level={riskLevel} />
                        </div>
                        <div className="flex items-center gap-4">
                            <IRIDots score={iriScore} />
                            <div className="text-xs font-mono text-tertiary">
                                {new Date(item.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                            </div>
                        </div>
                    </div>

                    {/* Middle: Narrative Summary */}
                    <div className="mb-4 pr-12">
                        <div className="flex gap-3 items-start">
                            <span className={`text-2xl mt-0.5 ${iconOpacity}`} title="Feed Type">{feedIcon}</span>
                            <p className="text-gray-300 font-medium leading-relaxed">
                                {summary}
                            </p>
                        </div>
                    </div>

                    {/* Bottom: Why Shown + Metadata */}
                    <div className="flex justify-between items-end border-t border-border/30 pt-3 mt-2">
                        <div className="flex flex-col gap-1">
                             <div className="flex items-center gap-2">
                                <span className="text-[10px] text-gray-500 uppercase font-bold tracking-wider">[Shown because]</span>
                                <span className="text-xs text-indigo-300 bg-indigo-900/20 px-1.5 py-0.5 rounded">
                                    {whyShown}
                                </span>
                             </div>
                             <div className="mt-1 text-xs text-gray-500 truncate max-w-sm ml-1 opacity-70">
                                Source: {p.source || 'Unknown'}
                             </div>
                        </div>

                        <div className="flex flex-col items-end gap-1">
                             <div className="text-[10px] text-tertiary uppercase tracking-wider">Assessment Confidence</div>
                             <div className="text-sm font-bold text-gray-200">
                                {((item.confidence || 0.8) * 100).toFixed(0)}%
                             </div>
                             <Link 
                                href={`/inversion/${item.id}`}
                                className="absolute inset-0 z-10"
                                aria-label="View Analysis"
                            />
                        </div>
                    </div>
                </div>
            );
        })}
        
        {initialItems.length === 0 && (
            <div className="text-center text-tertiary py-12 border border-dashed border-border rounded-lg bg-surface/30">
                <p>No active narrative risks detected.</p>
                <p className="text-sm mt-2">Market appears consensus-driven.</p>
            </div>
        )}
      </div>

      {/* Pagination Controls */}
      <div className="flex justify-between items-center pt-4 border-t border-border">
        <button
          disabled={currentPage <= 1}
          onClick={handlePrevPage}
          className="px-4 py-2 border border-border rounded disabled:opacity-50 text-sm font-medium hover:bg-surface transition"
        >
            Previous
        </button>
        <span className="text-xs text-tertiary font-mono">Page {currentPage}</span>
        <button
            disabled={currentPage * 20 >= total}
            onClick={handleNextPage}
          className="px-4 py-2 border border-border rounded disabled:opacity-50 text-sm font-medium hover:bg-surface transition"
        >
            Next
        </button>
      </div>
    </div>
  );
}
