from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "test_data"
LOG_FILE = LOG_DIR / "security_events.log"

# Change this if your SITL MAVLink endpoint is different.
MAVLINK_ENDPOINT = "tcp:127.0.0.1:5760"

HEARTBEAT_TIMEOUT = 5
TELEMETRY_INTERVAL = 1.0
