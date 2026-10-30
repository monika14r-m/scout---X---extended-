#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

[[ -f "$HOME/venv-ardupilot/bin/activate" ]] || { echo "[SCOUT-X] Missing $HOME/venv-ardupilot."; exit 1; }
source "$HOME/venv-ardupilot/bin/activate"
python3 -m pip install -q -r live_demo/requirements.txt

CASE="${1:-}"
if [[ -z "$CASE" ]]; then
  echo "Usage: bash simulation/run_case.sh {case1-command|case2-gcs-loss|case3-critical-hijack|gps-spoof}"
  exit 2
fi

CONNECT="${SCOUTX_MAVLINK_ENDPOINT:-udp:127.0.0.1:14550}"
BASE=(python3 -m scoutx_live run --connect "$CONNECT" --case "$CASE")

case "$CASE" in
  case1-command)
    echo "[SCOUT-X] Case 1 sends ARM/TAKEOFF commands to SITL."
    read -r -p "Confirm this is Gazebo/ArduPilot SITL (not a real UAV). Type SITL to continue: " answer
    [[ "$answer" == "SITL" ]] || { echo "Cancelled."; exit 1; }
    exec env PYTHONPATH="$ROOT/live_demo" "${BASE[@]}" --confirm-sitl --takeoff-m 5
    ;;
  case2-gcs-loss)
    exec env PYTHONPATH="$ROOT/live_demo" "${BASE[@]}" --timeout-s 3 --response RTL
    ;;
  case3-critical-hijack)
    exec env PYTHONPATH="$ROOT/live_demo" "${BASE[@]}"
    ;;
  gps-spoof)
    exec env PYTHONPATH="$ROOT/live_demo" "${BASE[@]}" --offset-m 35 --response LOITER
    ;;
  *)
    echo "Unknown case: $CASE"
    echo "Valid: case1-command, case2-gcs-loss, case3-critical-hijack, gps-spoof"
    exit 2
    ;;
esac
