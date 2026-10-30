#!/usr/bin/env bash
set -euo pipefail

ARDUPILOT_DIR="$HOME/ardupilot"
VENV="$HOME/venv-ardupilot"
SIM_VEHICLE="$ARDUPILOT_DIR/Tools/autotest/sim_vehicle.py"

[[ -f "$SIM_VEHICLE" ]] || { echo "[SCOUT-X] SITL launcher not found: $SIM_VEHICLE"; exit 1; }
[[ -f "$VENV/bin/activate" ]] || { echo "[SCOUT-X] Python environment not found: $VENV"; exit 1; }

source "$VENV/bin/activate"
cd "$ARDUPILOT_DIR"

echo "[SCOUT-X] Starting ArduCopter SITL with Gazebo Iris."
echo "[SCOUT-X] At MAV>, verify output includes 127.0.0.1:14550."
exec "$SIM_VEHICLE" -v ArduCopter -f gazebo-iris --console --map
