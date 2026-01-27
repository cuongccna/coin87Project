/**
 * Dispatcher State Store
 *
 * Tracks:
 * - Last dispatch timestamp per alert type (for rate limiting)
 * - Set of dispatched news IDs (for deduplication)
 *
 * In-memory implementation with Redis-ready interface.
 */

import type { AlertType } from "./alertTypes";

export type DispatcherState = {
  lastDispatchAtByType: Map<AlertType, number>;
  dispatchedNewsIds: Set<string>;
  lastGlobalDispatchAt: number | null;
};

export interface DispatcherStateStore {
  getState(): DispatcherState;
  setState(next: DispatcherState): void;
  recordDispatch(type: AlertType, now: number, newsId?: string): void;
  canDispatch(type: AlertType, now: number, cooldownMs: number): boolean;
  isNewsDispatched(newsId: string): boolean;
}

export function createInitialDispatcherState(): DispatcherState {
  return {
    lastDispatchAtByType: new Map(),
    dispatchedNewsIds: new Set(),
    lastGlobalDispatchAt: null,
  };
}

export class InMemoryDispatcherStore implements DispatcherStateStore {
  private state: DispatcherState;

  constructor() {
    this.state = createInitialDispatcherState();
  }

  getState(): DispatcherState {
    return {
      lastDispatchAtByType: new Map(this.state.lastDispatchAtByType),
      dispatchedNewsIds: new Set(this.state.dispatchedNewsIds),
      lastGlobalDispatchAt: this.state.lastGlobalDispatchAt,
    };
  }

  setState(next: DispatcherState): void {
    this.state = {
      lastDispatchAtByType: new Map(next.lastDispatchAtByType),
      dispatchedNewsIds: new Set(next.dispatchedNewsIds),
      lastGlobalDispatchAt: next.lastGlobalDispatchAt,
    };
  }

  canDispatch(type: AlertType, now: number, cooldownMs: number): boolean {
    // Global cooldown check
    if (this.state.lastGlobalDispatchAt !== null) {
      if (now - this.state.lastGlobalDispatchAt < cooldownMs) {
        return false;
      }
    }

    // Per-type cooldown check
    const lastTypeDispatch = this.state.lastDispatchAtByType.get(type);
    if (lastTypeDispatch !== undefined) {
      if (now - lastTypeDispatch < cooldownMs) {
        return false;
      }
    }

    return true;
  }

  isNewsDispatched(newsId: string): boolean {
    return this.state.dispatchedNewsIds.has(newsId);
  }

  recordDispatch(type: AlertType, now: number, newsId?: string): void {
    this.state.lastDispatchAtByType.set(type, now);
    this.state.lastGlobalDispatchAt = now;

    if (newsId) {
      this.state.dispatchedNewsIds.add(newsId);
    }
  }
}
