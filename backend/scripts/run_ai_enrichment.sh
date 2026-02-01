#!/bin/bash
# Run AI Enrichment Job
PROJECT_ROOT="/opt/coin87Project"
cd $PROJECT_ROOT || exit
source backend/venv/bin/activate
export PYTHONPATH=$PROJECT_ROOT/backend

# Load env to ensure GEMINI_API_KEY is available (though python script does load_env_if_present)
if [ -f "backend/.env" ]; then
    set -a
    source backend/.env
    set +a
fi

echo "Running AI Enrichment Job..."
python backend/ingestion/jobs/run_ai_enrichment.py --batch-size 20 --min-content-length 200
