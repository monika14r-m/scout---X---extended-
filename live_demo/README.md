# SCOUT-X Live SITL Demonstrator

A simulation-only add-on for SCOUT-X. It connects to ArduPilot SITL over MAVLink, reads live telemetry, runs contained scenarios, records security events, and can request RTL/LOITER after detection.

## What each scenario does

- **Case 1 — GCS command execution:** sends GUIDED, ARM and TAKEOFF commands to ArduPilot SITL. This is a real command to the simulated vehicle; it requires the explicit `--confirm-sitl` flag.
- **Case 2 — GCS heartbeat loss:** simulates an application-layer GCS heartbeat timeout while keeping the MAVLink control channel available for a response. It can request RTL or LOITER. This is not a real radio/network outage.
- **Case 3 — critical hijack alert:** records a simulated critical incident and locks the demo controller. It does not erase host files or perform destructive actions.
- **Additional GPS spoof test:** creates a synthetic spoofed *shadow observation* and compares it with live SITL GPS. It does not alter ArduPilot's EKF/GPS input and is not RF spoofing.

The supplied ROS1/MAVROS spoofing scripts are not drop-in compatible with the current Gazebo Sim 8 + ArduPilot setup. The Bebop ROS2 stack is a separate simulator. The GlobalHawks archive contains unrelated camera-targeting code; unsafe kamikaze material is not used here.

## Requirements

- Ubuntu/WSL with the existing ArduPilot SITL + Gazebo Sim 8 setup
- Python 3.10+
- `pymavlink`

From the repository root:

```bash
python3 -m pip install -r live_demo/requirements.txt
```

## Start simulation

**Terminal 1 — Gazebo:**

```bash
cd ~/gz_ws
export GZ_SIM_RESOURCE_PATH=$HOME/gz_ws/src/ardupilot_gazebo/models:$HOME/gz_ws/src/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH
export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/gz_ws/src/ardupilot_gazebo/build:$GZ_SIM_SYSTEM_PLUGIN_PATH
gz sim -v4 ~/gz_ws/src/ardupilot_gazebo/worlds/iris_runway.sdf
```

**Terminal 2 — ArduPilot SITL + MAVProxy:**

```bash
cd ~/ardupilot
source ~/venv-ardupilot/bin/activate
./Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --console --map
```

Ensure MAVProxy forwards telemetry to UDP 14550. If not, use the endpoint matching its `--out` setting.

**Terminal 3 — SCOUT-X:** run from the repository root:

```bash
python3 -m pip install -r live_demo/requirements.txt
python3 -m scoutx_live --help
```

The package directory is `live_demo/scoutx_live`; copy it to the repository root as `scoutx_live/` before running the commands below, or adjust `PYTHONPATH=live_demo` when running.

Read-only telemetry check:

```bash
PYTHONPATH=live_demo python3 -m scoutx_live status --connect udp:127.0.0.1:14550
```

## Run cases

**Case 1 — GCS command execution / takeoff (SITL only):**

```bash
PYTHONPATH=live_demo python3 -m scoutx_live run --case case1-command --connect udp:127.0.0.1:14550 --takeoff-m 5 --confirm-sitl
```

Watch the Iris in Gazebo. Only run in the empty simulation world.

**Case 2 — simulated GCS heartbeat loss + RTL:**

```bash
PYTHONPATH=live_demo python3 -m scoutx_live run --case case2-gcs-loss --connect udp:127.0.0.1:14550 --timeout-s 3 --response RTL
```

**Case 3 — critical hijack indicator + demo lockdown:**

```bash
PYTHONPATH=live_demo python3 -m scoutx_live run --case case3-critical-hijack --connect udp:127.0.0.1:14550
```

**Additional — GPS shadow anomaly + RTL:**

```bash
PYTHONPATH=live_demo python3 -m scoutx_live run --case gps-spoof --connect udp:127.0.0.1:14550 --offset-m 35 --response RTL
```

Logs are written to `live_demo/scoutx_live/logs/security_events.jsonl`.

## Safety and limitations

- Simulation-only. Do not connect to a real vehicle.
- Case 1 sends ARM/TAKEOFF to SITL only after explicit `--confirm-sitl`.
- Case 2 simulates the heartbeat timeout inside the SCOUT-X monitor; the underlying MAVLink link remains available so a response can be sent.
- GPS spoofing is injected into SCOUT-X's shadow copy only, not into the autopilot's EKF or physical GNSS receiver.
- Case 3 performs no file deletion, secure wipe, or real system lockout.
- RTL/LOITER availability depends on vehicle state and home/GPS validity. Observe SITL and MAVProxy output.

**Validation status:** Python syntax and the included lightweight unit test were checked. A successful live Gazebo/SITL run has not yet been verified; confirm heartbeat and telemetry before demonstrating.