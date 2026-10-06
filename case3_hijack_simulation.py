#!/usr/bin/env python3
"""
SCOUT-X Case 3 - Critical Hijack / Capture Simulation

Simulation-only:
  1. Connects to ArduPilot SITL over MAVLink.
  2. Monitors the real simulated UAV telemetry.
  3. After --delay seconds, injects a BENIGN simulated anomaly:
       - requests a GUIDED -> LAND transition
       - marks the event as a simulated hijack/capture
  4. SCOUT-X records the critical event.
  5. It destroys ONLY the demo copies of security/mission logs under
     ./case3_demo_data/ (never system files and never the Git repository).
  6. Creates a final status file showing that the simulated system is locked.

This is intended for a Gazebo/ArduPilot classroom demonstration.
"""

import argparse
import json
import shutil
import time
from datetime import datetime
from pathlib import Path

from pymavlink import mavutil


ROOT = Path(__file__).resolve().parent
DEMO_DATA = ROOT / "case3_demo_data"
EVENT_LOG = DEMO_DATA / "security_events.log"
STATUS_FILE = DEMO_DATA / "system_status.json"


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message):
    DEMO_DATA.mkdir(parents=True, exist_ok=True)
    line = f"[{timestamp()}] {message}"
    print(line)
    with EVENT_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def create_demo_logs():
    DEMO_DATA.mkdir(parents=True, exist_ok=True)

    (DEMO_DATA / "mission_data.json").write_text(
        json.dumps(
            {
                "mission": "SCOUT-X-CASE-3",
                "classification": "SIMULATION",
                "created": timestamp(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (DEMO_DATA / "telemetry_snapshot.json").write_text(
        json.dumps(
            {
                "note": "Dummy telemetry snapshot for secure-wipe demonstration",
                "created": timestamp(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def telemetry_snapshot(master):
    msg = master.recv_match(
        type=["GLOBAL_POSITION_INT", "SYS_STATUS", "HEARTBEAT"],
        blocking=False,
    )

    if msg is None:
        return None

    result = {"type": msg.get_type()}

    if msg.get_type() == "GLOBAL_POSITION_INT":
        result.update(
            {
                "lat": msg.lat / 1e7,
                "lon": msg.lon / 1e7,
                "relative_alt_m": msg.relative_alt / 1000.0,
            }
        )

    elif msg.get_type() == "SYS_STATUS":
        result["battery_percent"] = msg.battery_remaining

    elif msg.get_type() == "HEARTBEAT":
        result["base_mode"] = msg.base_mode
        result["custom_mode"] = msg.custom_mode

    return result


def request_safe_land(master):
    """
    Sends a normal MAVLink LAND command to the simulated vehicle.
    This is the visible Gazebo response for the demonstration.
    """
    log("RESPONSE: REQUESTING SIMULATED EMERGENCY LAND")

    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND,
        0,
        0, 0, 0, 0,
        0, 0, 0,
    )


def secure_wipe_demo_data():
    """
    Deletes only files inside ./case3_demo_data/.
    This is deliberately bounded to the project demo directory.
    """
    log("RESPONSE: SECURE LOG WIPE INITIATED")

    # Stop writing EVENT_LOG before deleting it.
    files_to_remove = list(DEMO_DATA.rglob("*"))

    for item in files_to_remove:
        if item.is_file():
            # Overwrite only the demo file before deleting it.
            try:
                size = item.stat().st_size
                if size:
                    with item.open("r+b") as f:
                        f.write(b"\x00" * size)
                        f.flush()
                item.unlink()
            except FileNotFoundError:
                pass

    # Remove empty directories created under the demo directory.
    for directory in sorted(
        [p for p in DEMO_DATA.rglob("*") if p.is_dir()],
        reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            pass

    DEMO_DATA.mkdir(parents=True, exist_ok=True)

    STATUS_FILE.write_text(
        json.dumps(
            {
                "status": "LOCKED",
                "security_event": "CRITICAL_HIJACK",
                "demo_log_wipe": "COMPLETED",
                "timestamp": timestamp(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"[{timestamp()}] SIMULATED DATA WIPE COMPLETED")
    print(f"[{timestamp()}] SYSTEM STATUS: LOCKED")
    print(f"[SCOUT-X] Remaining status file: {STATUS_FILE}")


def run(endpoint, delay):
    print("=" * 64)
    print("SCOUT-X — CASE 3: CRITICAL HIJACK / CAPTURE SIMULATION")
    print("=" * 64)
    print(f"MAVLink endpoint : {endpoint}")
    print(f"Attack delay     : {delay}s")
    print("Gazebo response  : simulated emergency LAND")
    print("Log response     : wipe ONLY ./case3_demo_data/")
    print("=" * 64)

    create_demo_logs()

    log("CASE 3 STARTED")
    log("SCOUT-X STATUS: MONITORING UAV")

    master = mavutil.mavlink_connection(endpoint)

    print("[SCOUT-X] Waiting for ArduPilot heartbeat...")
    heartbeat = master.wait_heartbeat(timeout=10)

    if heartbeat is None:
        print("[SCOUT-X] ERROR: No MAVLink heartbeat.")
        print("Start ArduPilot/Gazebo first.")
        return 1

    log(
        f"UAV CONNECTED: system={master.target_system}, "
        f"component={master.target_component}"
    )

    start = time.time()

    while time.time() - start < delay:
        data = telemetry_snapshot(master)
        if data:
            print("[LIVE TELEMETRY]", data)
        time.sleep(0.5)

    # -------- CRITICAL SIMULATED EVENT --------
    log("CRITICAL FAILURE / HIJACK CONDITION DETECTED")
    log("THREAT: UAV CONTROL CHANNEL COMPROMISED")
    log("THREAT CAPTURED BY SCOUT-X")

    request_safe_land(master)

    # Give ArduPilot/Gazebo a moment to show the response.
    time.sleep(2)

    log("SYSTEM RESPONSE: UAV LOCKDOWN")
    secure_wipe_demo_data()

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--endpoint",
        default="tcp:127.0.0.1:5760",
        help="ArduPilot SITL MAVLink endpoint",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=15,
        help="Seconds of live simulation before the critical event",
    )

    args = parser.parse_args()
    raise SystemExit(run(args.endpoint, args.delay))
