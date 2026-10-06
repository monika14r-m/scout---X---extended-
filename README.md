# SCOUT-X
## Secure Command And Operations for UAV Telemetry-eXtended

SCOUT-X is a simulation-only UAV security demonstration built around ArduPilot SITL, Gazebo and MAVLink.

### Demonstration cases
1. Normal GCS command / UAV operation
2. GPS spoofing detection
3. Altitude anomaly detection
4. Unauthorized command detection
5. Communication-loss detection and safe response
6. Critical hijack response with simulated data wipe and lock

> Safety: all attack and wipe functions are intended for a local simulation. The wipe operation is restricted to the project's `test_data/` directory.

### Prerequisites
- Ubuntu/WSL
- ArduPilot SITL
- Gazebo
- Python 3
- pymavlink

### Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run
Start your existing ArduPilot/Gazebo setup first. Then, from this repository:

```bash
source .venv/bin/activate
python3 demo.py --mode normal
```

Attack modes:

```bash
python3 demo.py --mode gps_spoofing
python3 demo.py --mode altitude
python3 demo.py --mode command_injection
python3 demo.py --mode communication_loss
python3 demo.py --mode critical_hijack
```

The monitor connects to MAVLink and reports live telemetry when a heartbeat is available. Attack modules provide controlled simulation triggers. The project does not claim that an attack is affecting Gazebo unless the corresponding MAVLink/SITL connection is active.

### Existing ArduPilot/Gazebo setup
The repository intentionally does not bundle the ArduPilot source tree or Gazebo build artifacts. Use the existing local installation.

Typical SITL command used with this project:

```bash
cd ~/ardupilot
./Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --console --map
```
