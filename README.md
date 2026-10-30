# SCOUT-X — Secure UAV Operations Simulation

SCOUT-X explores secure UAV telemetry monitoring, threat detection and defensive response under simulated operational and cyber events.

## Interactive browser showcase

**[Open the SCOUT-X Simulation Lab](https://monika14r-m.github.io/scout---X---extended-/)**

The GitHub Pages site is a self-contained, browser-only demonstration. It includes interactive visual scenarios for:

1. **GCS command execution and logging** — simulated command receipt, validation, flight-state change and operation logging.
2. **GCS signal / packet loss** — simulated heartbeat timeout, autonomous monitoring, and a simulated RTL response.
3. **Critical attack / hijack indicator** — simulated threat classification, demo control-path isolation, lockdown and audit logging.
4. **Additional GPS / altitude anomaly** — synthetic shadow telemetry deviation, threshold detection and evidence logging.

All aircraft movement, telemetry, attack events and responses on the Pages site are generated locally in the browser. The website does **not** connect to Gazebo, ArduPilot, MAVLink or a real UAV. It is a deployable visual scenario showcase, not a live SITL control station.

## Local ArduPilot SITL add-on

The experimental Python package in [live_demo](live_demo/README.md) is a separate integration path for the local Gazebo Sim 8 + ArduPilot SITL environment. It is not required by the browser showcase. Its live SITL connection has not yet been verified end-to-end.

### Local simulation stack

- Gazebo Sim 8.14.0 with the Iris model and runway world
- ArduPilot SITL / ArduCopter
- MAVProxy and MAVLink
- Python / pymavlink for the experimental live add-on

See [live_demo/README.md](live_demo/README.md) for setup details and the explicit limitations of each scenario.

## Deployment

GitHub Actions deploys the root `index.html` to GitHub Pages when it changes on `main`. In repository settings, set **Pages → Build and deployment → Source: GitHub Actions** if Pages is not already enabled. The workflow is in `.github/workflows/pages.yml`.

## Scope and safety

- Browser scenarios are deterministic demonstrations, not hardware or SITL telemetry.
- The GCS-loss browser case simulates a heartbeat timeout; it does not disable a real network link.
- The critical-incident browser case simulates isolation and demo lockdown only; it does not wipe files.
- GPS/altitude anomaly uses synthetic shadow data and does not spoof an autopilot sensor.
- Never connect experimental attack code to a real aircraft.

## Repository

- [Source code](https://github.com/monika14r-m/scout---X---extended-)
- [Experimental live SITL add-on](https://github.com/monika14r-m/scout---X---extended-/tree/main/live_demo)
