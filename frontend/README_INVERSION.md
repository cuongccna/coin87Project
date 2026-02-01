# Inversion Feed Feature - Frontend Guide

## Overview
UI for viewing Inversion Feeds at `/inversion`.
Includes a list view with filters and a detail view.

## Environment Variables
- `NEXT_PUBLIC_FEATURE_INVERSION`: Set to `true` to enable the feature UI components. 
  - If `false` or missing, the page may show a warning or be hidden (logic in `page.tsx`).

## Development
1. Ensure backend is running (`uvicorn app.main:app`).
2. Run frontend:
   ```bash
   npm run dev
   ```
3. Visit `http://localhost:3000/inversion`.

## Components
- `app/inversion/page.tsx`: Server component fetching list.
- `app/inversion/[id]/page.tsx`: Server component fetching detail.
- `components/InversionFeedList.tsx`: Client component for list rendering/filtering.
- `lib/api/inversionApi.ts`: API wrapper.
