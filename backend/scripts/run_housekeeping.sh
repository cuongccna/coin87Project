#!/bin/bash
# Run Housekeeping Job
PROJECT_ROOT="/opt/coin87Project"
cd $PROJECT_ROOT || exit
source backend/venv/bin/activate
export PYTHONPATH=$PROJECT_ROOT/backend
echo "Running Housekeeping Job..."
python backend/audit/job/run_housekeeping.py
