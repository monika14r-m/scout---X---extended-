# SCOUT-X — Secure UAV Operations Simulation

SCOUT-X is a simulation-first UAV security project using an Iris aircraft in Gazebo Sim, ArduCopter SITL, MAVProxy, MAVLink and a Python monitoring layer.

## Project simulation page

**[Open the SCOUT-X project page](https://monika14r-m.github.io/scout---X---extended-/)**

The project page documents how to launch the actual Gazebo + ArduPilot simulation. It intentionally contains no browser-drawn drone animation and does not claim to stream a live Gazebo session. Gazebo runs on the project workstation; GitHub Pages hosts the project documentation and launch instructions.

## Run the actual simulation

See [simulation/README.md](simulation/README.md) for the complete setup and case instructions.

Quick start in three Ubuntu/WSL terminals:

1. Gazebo: `bash simulation/run_gazebo.sh`
2. ArduCopter SITL: `bash simulation/run_sitl.sh`
3. SCOUT-X telemetry: `PYTHONPATH=live_demo python3 -m scoutx_live status --connect udp:127.0.0.1:14550`

Run a scenario from the repository root with `bash simulation/run_case.sh CASE_NAME`.

## Project cases

1. **GCS command execution and logging** — send confirmed commands to SITL, observe the Iris in Gazebo, monitor telemetry and log the operation.
2. **GCS signal / packet loss** — simulate an application-level GCS heartbeat timeout, monitor the loss and request a configured SITL response. This is not a physical radio outage.
3. **Critical attack / hijack indicator** — record a simulated critical incident, capture telemetry and lock the demo controller. No destructive wipe is performed.
4. **Additional GPS anomaly** — compare authentic SITL reference telemetry with a synthetic shadow-data offset. It is not injected into the autopilot.

## Components

- Gazebo Sim 8.14.0 and Iris model
- ArduPilot SITL / ArduCopter
- MAVProxy and MAVLink
- Python and pymavlink
- JSON Lines security-event logging

## Important limitations

The local launch workflow is intended for simulation only. Case 2 currently simulates an application-level heartbeat timeout, not a real radio/packet outage. The GPS anomaly is generated in SCOUT-X shadow telemetry, not injected into the flight controller. Case 3 is a non-destructive demo lockdown. Live MAVLink connectivity must be verified on the actual workstation before claiming an end-to-end live run.

Real Gazebo recordings should be captured from the simulator and added under `docs/media/`. No simulated footage is fabricated or presented as a live recording.

## Repository layout

- `simulation/` — Gazebo, SITL and scenario launch scripts
- `live_demo/` — Python/MAVLink monitoring and scenario package
- `index.html` — GitHub Pages project page
- `.github/workflows/pages.yml` — GitHub Pages deployment workflow

**Source:** https://github.com/monika14r-m/scout---X---extended-
