# SCOUT-X Live SITL Demonstrator

A simulation-only add-on for the SCOUT-X repository. It connects to ArduPilot SITL over MAVLink, reads live vehicle telemetry, runs controlled fault scenarios, records security events, and can request a safe flight mode (RTL or LOITER) after detection.

## What is actually simulated

- **Case 1 — GPS spoofing/anomaly:** SCOUT-X reads the live SITL GPS/position stream, creates a *separate synthetic spoofed observation* with a configurable offset, compares it with the unmodified baseline, detects the discrepancy, logs it, and optionally requests RTL. This demonstrates the detection/response pipeline without overwriting ArduPilot's EKF/GPS sensor input.
- **Case 2 — GCS link loss:** SCOUT-X simulates loss of the operator/GCS heartbeat at the application layer, detects the timeout, logs it, and optionally requests RTL or LOITER. The SITL MAVLink transport remains available so the demonstration controller can issue the response.
- **Case 3 — critical hijack alert:** a contained incident simulation. It logs a critical event, disables further demo commands in this process, and locks the demo state. It does **not** erase host files or attempt a real drone self-destruct.

The attached research describes ROS/ROS2/Gazebo sensor-topic spoofing and GPS/odometry manipulation. The supplied `spoofing-attacks-using-gazebo` scripts target ROS1/MAVROS topics (`/mavros/global_position/...`) and require a ROS1/GNC setup; they are not drop-in scripts for this user's Gazebo Sim 8 + ArduPilot SITL environment. `bebop_ros` is a separate ROS2 Jazzy/Gazebo Harmonic Bebop swarm stack. `GlobalHawks` contains camera detection/targeting code and an unsafe kamikaze example; it is not imported or executed by this demonstrator. Only its non-harmful pixel-to-GPS calculation concept is relevant to future perception work.

## Requirements

- Ubuntu/WSL with the existing ArduPilot SITL + Gazebo Sim 8 setup.
- Python 3.10+.
- `pymavlink` installed in the same Python environment used for the demo.

```bash
python3 -m pip install -r requirements.txt
```

## Start the existing simulator

**Terminal 1 — Gazebo** (keep your working resource-path exports):

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

Wait for MAVProxy to connect. If it does not forward telemetry to UDP 14550, use the connection string matching your MAVProxy `--out` configuration.

**Terminal 3 — SCOUT-X add-on:**

Copy this folder into your existing repository as `scoutx_live/`, and copy `requirements.txt` to the repo root, or clone this add-on alongside the repo. Then:

```bash
cd ~/SCOUT-X
python3 -m pip install -r requirements.txt
python3 -m scoutx_live --help
```

Default MAVLink endpoint is `udp:127.0.0.1:14550`.

## Run the scenarios

First confirm live telemetry (read-only):

```bash
python3 -m scoutx_live status --connect udp:127.0.0.1:14550
```

**Case 1 — GPS spoofing detection + RTL response:**

```bash
python3 -m scoutx_live run --case gps-spoof --connect udp:127.0.0.1:14550 --offset-m 35 --response RTL
```

The attack is injected into SCOUT-X's *shadow observation*, not the autopilot sensor. On detection, SCOUT-X requests RTL from SITL. For a safe demo, run only in the empty Gazebo world and ensure RTL is appropriate for the current home position.

**Case 2 — GCS heartbeat-loss detection + LOITER response:**

```bash
python3 -m scoutx_live run --case gcs-loss --connect udp:127.0.0.1:14550 --timeout-s 3 --response LOITER
```

This simulates the GCS heartbeat disappearing from SCOUT-X's monitor. MAVLink remains connected for the demo controller to request LOITER.

**Case 3 — contained critical incident / lockdown:**

```bash
python3 -m scoutx_live run --case critical-hijack --connect udp:127.0.0.1:14550 --response NONE
```

This is a safe software incident simulation only. It does not perform a destructive wipe.

## Important safety / scope

- Simulation-only. Do not connect this tool to a real vehicle.
- The `--response` option sends a mode-change command to the connected autopilot. It is disabled by default in status mode and only used when explicitly selected in `run`.
- RTL/LOITER acceptance depends on ArduPilot vehicle state, GPS/home validity, and mode availability. Always inspect SITL and the MAVProxy console.
- Case 1's injected offset is a SCOUT-X shadow-data anomaly, **not** a physical RF GNSS spoof and **not** an ArduPilot EKF-input spoof.
- Case 2 is an application-layer heartbeat-loss simulation, not a real radio/network outage.
- Logs are written to `scoutx_live/logs/security_events.jsonl`.

## Research basis and integration notes

- Patil et al., *ROS2-Based Simulation Framework for Cyberphysical Security Analysis of UAVs* (2024), describes modular ROS2/Gazebo sensor, autonomy, communication and attack-model components, including online and offline modes.
- Pekaric et al., *Simulation of Sensor Spoofing Attacks on UAVs Using the Gazebo Simulator* (2023), demonstrates that GPS spoofing effects on navigation require manipulating both global GPS and local odometry data; it also notes that GPS-only changes may not visibly affect the simulated vehicle without additional integration.
- The supplied ROS1 scripts publish to MAVROS topics and should only be run in their original ROS1/GNC workspace. This project deliberately avoids mixing those scripts into the current ROS2-free ArduPilot/Gazebo Sim setup.

## GitHub

From the root of your existing `SCOUT-X` clone, after copying this folder in:

```bash
git add scoutx_live requirements.txt README-live-demo.md
git commit -m "Add live SITL security scenario demonstrator"
git push origin main
```
