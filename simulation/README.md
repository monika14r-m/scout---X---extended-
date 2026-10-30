# SCOUT-X — Real Gazebo + ArduPilot simulation

This folder contains the launch workflow for the **actual Gazebo Iris + ArduCopter SITL simulation**. It does not draw a substitute drone in a browser.

## What runs where

- **Gazebo Sim 8** renders the Iris aircraft and runway.
- **ArduPilot SITL** runs the flight controller.
- **MAVProxy** connects to SITL and forwards MAVLink telemetry.
- **SCOUT-X live demo** reads telemetry and runs the contained project scenarios.

The simulator runs on the user's Linux/WSL machine. GitHub Pages cannot execute Gazebo or ArduPilot; it can host source code and recorded simulator footage.

## Start the real simulation

Open three Ubuntu terminals (not Windows CMD).

### Terminal 1 — Gazebo renderer

~~~bash
cd ~/scout---X---extended-
bash simulation/run_gazebo.sh
~~~

### Terminal 2 — ArduCopter SITL and MAVProxy

~~~bash
cd ~/scout---X---extended-
bash simulation/run_sitl.sh
~~~

Wait for the MAV> prompt. In MAVProxy, check outputs:

~~~text
output
~~~

If 127.0.0.1:14550 is missing, add it:

~~~text
output add 127.0.0.1:14550
~~~

### Terminal 3 — SCOUT-X telemetry monitor

~~~bash
cd ~/scout---X---extended-
source ~/venv-ardupilot/bin/activate
python3 -m pip install -r live_demo/requirements.txt
PYTHONPATH=live_demo python3 -m scoutx_live status --connect udp:127.0.0.1:14550
~~~

A successful connection prints a heartbeat and live GPS/position telemetry. If it times out, the live integration is not yet connected; troubleshoot the MAVLink UDP route first.

## Run the project scenarios

Run only against local SITL, never a physical aircraft.

### Case 1 — GCS command execution and logging

~~~bash
bash simulation/run_case.sh case1-command
~~~

After explicit confirmation, the script sends GUIDED/ARM/TAKEOFF to SITL. Watch the Iris in Gazebo.

### Case 2 — GCS signal / packet loss

~~~bash
bash simulation/run_case.sh case2-gcs-loss
~~~

This injects an application-level SCOUT-X heartbeat timeout and can request a SITL safe mode. It does not physically disconnect MAVLink or disable a radio.

### Case 3 — Critical attack / hijack indicator

~~~bash
bash simulation/run_case.sh case3-critical-hijack
~~~

This records a simulated critical incident and locks the demo controller. It does not execute a real hijack, isolate ArduPilot, or erase data.

### Additional — GPS anomaly

~~~bash
bash simulation/run_case.sh gps-spoof
~~~

This creates a synthetic offset in SCOUT-X shadow telemetry and compares it with the live SITL reference. It does not inject spoofed GPS into the flight controller or transmit RF signals.

## Evidence and logs

JSON Lines events are written to live_demo/scoutx_live/logs/security_events.jsonl.

For a project presentation, record the **actual Gazebo window and SCOUT-X terminal together** while each case runs. Store real recordings under docs/media/ and embed those recordings in the project page. No recording is claimed until it has actually been captured.

## Important boundary

These scripts make local Gazebo/SITL scenarios reproducible. They do not make Gazebo run inside GitHub Pages. GitHub hosts the code and documentation; the simulator runs locally.