# Ingestion jobs (sample)

This folder contains helper scripts to POST sample Inversion Feed items to the backend API.

Usage example:

```bash
# set token if needed (reads NEXT_PUBLIC_UI_BEARER_TOKEN or C87_UI_BEARER_TOKEN if present)
export NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
export NEXT_PUBLIC_UI_BEARER_TOKEN=eyJ...yourtoken...

python ingest_inversion_sample.py --file sample_inversions.json

# dry-run
python ingest_inversion_sample.py --file sample_inversions.json --dry-run
```

The script posts to `POST /v1/inversion-feeds/` and will print responses for each item.
