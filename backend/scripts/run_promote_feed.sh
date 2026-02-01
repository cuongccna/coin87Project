#!/bin/bash
# Run Feed Promotion Job
PROJECT_ROOT="/opt/coin87Project"
cd $PROJECT_ROOT || exit
source backend/venv/bin/activate
export PYTHONPATH=$PROJECT_ROOT/backend
echo "Running Feed Promotion Job..."
python backend/derive/job/promote_feed.py
