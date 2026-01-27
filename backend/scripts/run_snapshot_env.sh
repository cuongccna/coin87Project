#!/bin/bash
# Run Snapshot Job
PROJECT_ROOT="/opt/coin87Project"
cd $PROJECT_ROOT || exit
source backend/venv/bin/activate
export PYTHONPATH=$PROJECT_ROOT/backend
echo "Running Snapshot Environment Job..."
python backend/snapshot/job/run_snapshot_env.py
