export interface InversionFeed {
    id: string;
    symbol: string;
    feed_type: string;
    direction: string;
    value?: number | null;
    confidence?: number | null;
    payload?: any;
    metadata_?: any; // Mapped from metadata
    status: string;
    created_at: string;
    processed_at?: string | null;
    external_id?: string | null;
    source_id?: string | null;
  }
  
  export interface InversionFeedListResponse {
    total: number;
    items: InversionFeed[];
  }
  
  export interface InversionFeedCreate {
    symbol: string;
    feed_type: string;
    direction: 'up' | 'down' | 'neutral';
    value?: number;
    confidence?: number;
    payload?: any;
    metadata?: any;
    external_id?: string;
    source_id?: string;
  }
