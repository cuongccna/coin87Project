#!/bin/bash
# Run Derive Risk Job
PROJECT_ROOT="/opt/coin87Project"
cd $PROJECT_ROOT || exit
source backend/venv/bin/activate
export PYTHONPATH=$PROJECT_ROOT/backend
echo "Running Derive Risk Job..."
python backend/derive/job/run_derive_risk.py
