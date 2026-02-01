# Inversion Feed Feature - Backend Guide

## Overview
The Inversion Feed subsystem captures and processes high-value signal inversions (price/momentum) from various sources.

## Setup & Migration
1. **Apply Migrations**
   The feature adds `inversion_feeds` table.
   ```bash
   cd backend
   alembic upgrade head
   ```

## Configuration
- No specific backend env var required yet (default enabled). A `FEATURE_INVERSION` toggle can be added to `app/core/config.py` if needed.

## API Usage
**Base URL**: `/api/v1/inversion-feeds`

### Create Feed (POST /)
```json
{
  "symbol": "BTC",
  "feed_type": "price-inversion",
  "direction": "down",
  "confidence": 0.95,
  "payload": {"source": "manual_test"}
}
```
*Note*: This enqueues a background task to process the feed.

### List Feeds (GET /)
Filter by `symbol`, `status`, `start`, `end`.
```bash
curl "http://localhost:8000/api/v1/inversion-feeds?symbol=BTC&limit=5"
```

## Background Processing
The endpoints automatically schedule processing. To run manually or debug:

```bash
# Process a specific feed ID
python backend/ingestion/jobs/process_inversion_feed.py <UUID>
```

## Testing
Run the dedicated test suite:
```bash
pytest backend/tests/test_inversion_feed.py
```
