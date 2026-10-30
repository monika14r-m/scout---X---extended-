#!/usr/bin/env bash
set -euo pipefail

WORLD="$HOME/gz_ws/src/ardupilot_gazebo/worlds/iris_runway.sdf"
MODEL_DIR="$HOME/gz_ws/src/ardupilot_gazebo/models"
PLUGIN_DIR="$HOME/gz_ws/src/ardupilot_gazebo/build"

command -v gz >/dev/null 2>&1 || { echo "[SCOUT-X] Gazebo command 'gz' not found."; exit 1; }
[[ -f "$WORLD" ]] || { echo "[SCOUT-X] Iris runway world not found: $WORLD"; exit 1; }

export GZ_SIM_RESOURCE_PATH="$MODEL_DIR:$(dirname "$WORLD"):${GZ_SIM_RESOURCE_PATH:-}"
export GZ_SIM_SYSTEM_PLUGIN_PATH="$PLUGIN_DIR:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"

echo "[SCOUT-X] Launching the actual Gazebo Iris runway world."
echo "[SCOUT-X] Start ArduPilot SITL in a second Ubuntu terminal."
exec gz sim -v4 "$WORLD"
