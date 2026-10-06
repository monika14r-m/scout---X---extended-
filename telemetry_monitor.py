import time
from pymavlink import mavutil

class TelemetryMonitor:
    def __init__(self, endpoint, heartbeat_timeout=5):
        self.endpoint = endpoint
        self.heartbeat_timeout = heartbeat_timeout
        self.connection = None

    def connect(self):
        print(f"[SCOUT-X] Connecting to {self.endpoint}")
        self.connection = mavutil.mavlink_connection(self.endpoint)
        msg = self.connection.wait_heartbeat(timeout=self.heartbeat_timeout)
        if msg is None:
            raise TimeoutError(
                f"No MAVLink heartbeat received from {self.endpoint}"
            )
        print(
            f"[SCOUT-X] HEARTBEAT RECEIVED "
            f"system={self.connection.target_system} "
            f"component={self.connection.target_component}"
        )

    def read_once(self):
        if self.connection is None:
            return {}

        result = {}

        msg = self.connection.recv_match(
            type=["GLOBAL_POSITION_INT", "GPS_RAW_INT", "SYS_STATUS"],
            blocking=False
        )

        if msg is None:
            return result

        msg_type = msg.get_type()

        if msg_type == "GLOBAL_POSITION_INT":
            result["lat"] = msg.lat / 1e7
            result["lon"] = msg.lon / 1e7
            result["altitude"] = msg.relative_alt / 1000.0
            result["velocity"] = (
                (msg.vx ** 2 + msg.vy ** 2 + msg.vz ** 2) ** 0.5
            ) / 100.0

        elif msg_type == "GPS_RAW_INT":
            result["gps_fix"] = msg.fix_type
            result["satellites"] = msg.satellites_visible

        elif msg_type == "SYS_STATUS":
            result["battery"] = msg.battery_remaining

        return result

    def stream(self, seconds=10):
        start = time.time()

        while time.time() - start < seconds:
            data = self.read_once()

            if data:
                print("[TELEMETRY]", data)

            time.sleep(0.2)
