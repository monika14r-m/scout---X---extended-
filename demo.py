#!/usr/bin/env python3
import argparse
import time

from config.config import MAVLINK_ENDPOINT, HEARTBEAT_TIMEOUT
from scout_x.telemetry_monitor import TelemetryMonitor
from scout_x.response_manager import ResponseManager
from scout_x.security_middleware import log_event

MODES = {
    "normal": None,
    "gps_spoofing": "GPS_ANOMALY",
    "altitude": "ALTITUDE_ANOMALY",
    "command_injection": "COMMAND_INJECTION",
    "communication_loss": "COMMUNICATION_LOSS",
    "critical_hijack": "CRITICAL_HIJACK",
}

def main():
    parser = argparse.ArgumentParser(
        description="SCOUT-X Gazebo/ArduPilot security demonstration"
    )
    parser.add_argument(
        "--mode",
        choices=MODES.keys(),
        default="normal"
    )
    args = parser.parse_args()

    print("=" * 55)
    print("SCOUT-X UAV SECURITY DEMONSTRATION")
    print(f"MODE: {args.mode.upper()}")
    print("=" * 55)

    monitor = TelemetryMonitor(
        MAVLINK_ENDPOINT,
        HEARTBEAT_TIMEOUT
    )

    try:
        monitor.connect()
    except Exception as exc:
        print(f"[SCOUT-X] MAVLink connection failed: {exc}")
        print(
            "[SCOUT-X] Start ArduPilot/Gazebo first and verify "
            f"the MAVLink endpoint: {MAVLINK_ENDPOINT}"
        )
        return 1

    log_event(f"DEMO STARTED: {args.mode.upper()}")

    if args.mode == "normal":
        log_event("SYSTEM STATUS: NORMAL")
        monitor.stream(seconds=15)
        return 0

    threat_type = MODES[args.mode]

    print(f"\n[SCOUT-X] SIMULATED ATTACK: {args.mode.upper()}")
    print("[SCOUT-X] Live MAVLink telemetry remains monitored.")

    if threat_type == "GPS_ANOMALY":
        log_event("THREAT: GPS SPOOFING SIMULATION")
        log_event("RESPONSE: GPS ANOMALY MONITORING ACTIVE")

    elif threat_type == "ALTITUDE_ANOMALY":
        log_event("THREAT: ALTITUDE MANIPULATION SIMULATION")
        log_event("RESPONSE: ALTITUDE ANOMALY MONITORING ACTIVE")

    elif threat_type == "COMMAND_INJECTION":
        log_event("THREAT: COMMAND INJECTION SIMULATION")
        log_event("RESPONSE: UNAUTHORIZED COMMAND REJECTED")

    elif threat_type == "COMMUNICATION_LOSS":
        log_event("THREAT: COMMUNICATION LOSS SIMULATION")
        log_event("RESPONSE: AUTONOMOUS / SAFE MODE")

    elif threat_type == "CRITICAL_HIJACK":
        log_event("THREAT: CRITICAL HIJACK SIMULATION")
        log_event("RESPONSE: LOCKDOWN")
        ResponseManager().respond({
            "type": "CRITICAL_HIJACK",
            "severity": "CRITICAL"
        })

    # Continue showing actual telemetry from SITL/Gazebo.
    monitor.stream(seconds=15)

    log_event("DEMO COMPLETED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
