# coin87 IC UI (Next.js App Router)

Environment variables (server-side):

- `C87_API_BASE_URL` (example: `http://localhost:8000`)
- `C87_UI_BEARER_TOKEN` (institutional JWT; provisioned out of band)

This UI is intentionally read-only and low-interaction.

## Run locally

From the repo root:

```powershell
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
C87_API_BASE_URL=http://127.0.0.1:8000
C87_UI_BEARER_TOKEN=PASTE_YOUR_JWT_HERE
```

Start UI:

```powershell
npm run dev
```

Open `http://localhost:3000`.

## Manual “read-only UI” check (DevTools)

- Open Chrome DevTools → Network
- Reload page
- **PASS if**: only `GET` (plus `OPTIONS/HEAD`) and no `POST/PUT/PATCH/DELETE`
- Wait 60s
- **PASS if**: no rapid repeating requests (no polling storm)
