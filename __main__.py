import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

from pymavlink import mavutil

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "security_events.jsonl"


def log_event(event, **details):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": "SCOUT-X",
        "event": event,
        **details,
    }
    print(json.dumps(row, indent=2))
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def connect_vehicle(endpoint, timeout):
    print(f"[SCOUT-X] Connecting to SITL: {endpoint}")
    master = mavutil.mavlink_connection(endpoint, autoreconnect=True)
    hb = master.wait_heartbeat(timeout=timeout)
    if hb is None:
        raise TimeoutError(
            f"No MAVLink heartbeat from {endpoint}. Check SITL and MAVProxy --out."
        )
    print(f"[SCOUT-X] Heartbeat received: system={master.target_system}, "
          f"component={master.target_component}")
    return master


def read_position(master, timeout=8):
    deadline = time.time() + timeout
    gps = None
    pos = None
    while time.time() < deadline:
        msg = master.recv_match(
            type=["GLOBAL_POSITION_INT", "GPS_RAW_INT", "VFR_HUD"],
            blocking=True, timeout=1
        )
        if msg is None:
            continue
        if msg.get_type() == "GLOBAL_POSITION_INT":
            pos = {
                "lat": msg.lat / 1e7,
                "lon": msg.lon / 1e7,
                "relative_alt_m": msg.relative_alt / 1000.0,
                "vx_cms": msg.vx,
                "vy_cms": msg.vy,
            }
        elif msg.get_type() == "GPS_RAW_INT":
            gps = {
                "lat": msg.lat / 1e7,
                "lon": msg.lon / 1e7,
                "fix_type": msg.fix_type,
                "satellites_visible": msg.satellites_visible,
                "eph": msg.eph,
            }
        if gps and pos:
            return gps, pos
    raise TimeoutError("No usable GPS_RAW_INT + GLOBAL_POSITION_INT telemetry received.")


def request_mode(master, mode):
    if mode == "NONE":
        return
    mapping = master.mode_mapping()
    if not mapping or mode not in mapping:
        raise RuntimeError(f"Mode {mode} is unavailable. Available: {sorted(mapping or {})}")
    mode_id = mapping[mode]
    master.mav.set_mode_send(
        master.target_system,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        mode_id,
    )
    log_event("FLIGHT_MODE_REQUESTED", requested_mode=mode)


def run_gps_spoof(master, offset_m, response):
    gps, pos = read_position(master)
    print("\n[BASELINE] Live SITL GPS / position")
    print(json.dumps({"gps": gps, "position": pos}, indent=2))

    # Create a shadow observation: alter only SCOUT-X's copy.
    lat_scale = 111_320.0
    lon_scale = max(1.0, 111_320.0 * math.cos(math.radians(gps["lat"])))
    spoofed = dict(gps)
    spoofed["lat"] += offset_m / lat_scale
    spoofed["lon"] += offset_m / lon_scale

    delta_lat = (spoofed["lat"] - gps["lat"]) * lat_scale
    delta_lon = (spoofed["lon"] - gps["lon"]) * lon_scale
    discrepancy = math.hypot(delta_lat, delta_lon)
    threshold_m = 10.0

    print("\n[ATTACK] GPS spoofing scenario injected into SCOUT-X shadow telemetry")
    print(json.dumps({"authentic_reference": gps, "spoofed_observation": spoofed}, indent=2))
    if discrepancy >= threshold_m:
        log_event(
            "GPS_SPOOFING_ANOMALY_DETECTED",
            discrepancy_m=round(discrepancy, 2),
            threshold_m=threshold_m,
            gps_fix_type=gps["fix_type"],
            response=response,
            injection_layer="SCOUT_X_SHADOW_TELEMETRY_ONLY",
        )
        print(f"\n[DETECTION] GPS anomaly: {discrepancy:.1f} m (threshold {threshold_m:.1f} m)")
        print("[RESPONSE] Requesting safe SITL response.")
        request_mode(master, response)
        log_event("GPS_SCENARIO_COMPLETE", result="DETECTED", response=response)
    else:
        log_event("GPS_SCENARIO_NO_ALERT", discrepancy_m=round(discrepancy, 2))
        print("[RESULT] Offset below detection threshold; no response requested.")


def run_gcs_loss(master, timeout_s, response):
    print(f"\n[CASE 2] Monitoring GCS heartbeat for {timeout_s:.1f}s")
    print("[SCOUT-X] Simulating application-layer GCS heartbeat loss.")
    # A deterministic timeout event is used while retaining the MAVLink control
    # channel for the safety response. This does not disconnect SITL itself.
    last_heartbeat = time.monotonic()
    simulated_gcs_heartbeat = True
    time.sleep(timeout_s)
    simulated_gcs_heartbeat = False
    elapsed = time.monotonic() - last_heartbeat
    if not simulated_gcs_heartbeat and elapsed >= timeout_s:
        log_event(
            "GCS_HEARTBEAT_LOSS_DETECTED",
            timeout_s=timeout_s,
            elapsed_s=round(elapsed, 2),
            response=response,
            injection_layer="SCOUT_X_APPLICATION_HEARTBEAT_SIMULATION",
        )
        print("[DETECTION] GCS heartbeat timeout detected.")
        print("[RESPONSE] Requesting safe SITL response.")
        request_mode(master, response)
        log_event("GCS_LOSS_SCENARIO_COMPLETE", result="DETECTED", response=response)


def run_critical(master):
    gps, pos = read_position(master)
    log_event(
        "CRITICAL_UAV_INCIDENT_SIMULATED",
        threat="SIMULATED_HIJACK_INDICATOR",
        telemetry_snapshot={"gps": gps, "position": pos},
        action="DEMO_LOCKDOWN_ONLY",
    )
    print("[CRITICAL] Simulated incident recorded.")
    print("[LOCKDOWN] Demo controller locked; no destructive action performed.")
    log_event("DEMO_LOCKED", destructive_actions=False)


def main():
    parser = argparse.ArgumentParser(
        prog="python3 -m scoutx_live",
        description="SCOUT-X simulation-only ArduPilot SITL scenario runner",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status", help="Read live SITL telemetry only")
    run = sub.add_parser("run", help="Run a contained security scenario")
    for p in (status, run):
        p.add_argument("--connect", default="udp:127.0.0.1:14550")
        p.add_argument("--heartbeat-timeout", type=int, default=15)
    run.add_argument("--case", choices=["case1-command", "case2-gcs-loss", "case3-critical-hijack", "gps-spoof"], required=True)
    run.add_argument("--takeoff-m", type=float, default=5.0)
    run.add_argument("--confirm-sitl", action="store_true",
                     help="Required before Case 1 sends an arm/takeoff command to SITL")
    run.add_argument("--offset-m", type=float, default=35.0)
    run.add_argument("--timeout-s", type=float, default=3.0)
    run.add_argument("--response", choices=["NONE", "LOITER", "RTL"], default="NONE")
    args = parser.parse_args()

    master = connect_vehicle(args.connect, args.heartbeat_timeout)
    if args.command == "status":
        gps, pos = read_position(master)
        print(json.dumps({"gps": gps, "position": pos}, indent=2))
        log_event("LIVE_TELEMETRY_READ", gps=gps, position=pos)
        return
    if args.case == "case1-command":
        if not args.confirm_sitl:
            raise SystemExit("Case 1 can arm/take off SITL. Re-run with --confirm-sitl after confirming this is simulation only.")
        gps, pos = read_position(master)
        log_event("GCS_COMMAND_RECEIVED", command="TAKEOFF", target_altitude_m=args.takeoff_m)
        # Request GUIDED mode and arm/takeoff using MAVLink command_long.
        mapping = master.mode_mapping() or {}
        if "GUIDED" not in mapping:
            raise RuntimeError("GUIDED mode unavailable in this vehicle mode map.")
        master.mav.set_mode_send(master.target_system,
                                 mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                                 mapping["GUIDED"])
        master.mav.command_long_send(
            master.target_system, master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
            1, 0, 0, 0, 0, 0, 0
        )
        time.sleep(2)
        master.mav.command_long_send(
            master.target_system, master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0,
            0, 0, 0, float("nan"), 0, 0, args.takeoff_m
        )
        log_event("GCS_COMMAND_TRANSMITTED", command="GUIDED_ARM_TAKEOFF",
                  target_altitude_m=args.takeoff_m)
        print("[CASE 1] GCS command sent to SITL. Watch the Iris climb in Gazebo.")
        log_event("GCS_COMMAND_MONITORING", gps=gps, position=pos)
    elif args.case in ("case2-gcs-loss", "gcs-loss"):
        run_gcs_loss(master, max(1.0, args.timeout_s), args.response)
    elif args.case in ("case3-critical-hijack", "critical-hijack"):
        run_critical(master)
    elif args.case == "gps-spoof":
        run_gps_spoof(master, max(0.0, args.offset_m), args.response)


if __name__ == "__main__":
    main()
