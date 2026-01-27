#!/bin/bash
# Run Ingestion Job
PROJECT_ROOT="/opt/coin87Project"
cd $PROJECT_ROOT || exit
source backend/venv/bin/activate
export PYTHONPATH=$PROJECT_ROOT/backend
echo "Running Ingestion Job..."
python backend/ingestion/jobs/run_ingestion.py
