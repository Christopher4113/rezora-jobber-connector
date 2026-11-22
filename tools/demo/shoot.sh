#!/usr/bin/env bash
# Usage: tools/demo/shoot.sh 2026-11-30   (a Monday the Jobber test account hasn't been used for yet)
# Needs the demo server running: uv run uvicorn rezora_jobber.server:app --port 8000
set -euo pipefail
cd "$(dirname "$0")/../.."
MONDAY=${1:?pass a Monday, e.g. 2026-11-30}
TUESDAY=$(python3 -c "import datetime,sys;print(datetime.date.fromisoformat(sys.argv[1])+datetime.timedelta(days=1))" "$MONDAY")
uv run python seed.py "$TUESDAY"                       # the visit the leak call collides with
mkdir -p takes
DEMO_NOW="${MONDAY}T09:00" reshoot web tools/demo/storyboard.py takes/web.mp4
