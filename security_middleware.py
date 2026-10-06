from pathlib import Path
from datetime import datetime
import shutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "test_data"
LOG_FILE = PROJECT_ROOT / "logs" / "security_events.log"

def log_event(message):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def secure_wipe_simulation():
    log_event("CRITICAL FAILURE / HIJACK DETECTED")
    log_event("RESPONSE: SECURE DATA WIPE INITIATED")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for item in list(DATA_DIR.iterdir()):
        if item.is_file():
            item.write_bytes(b"\x00" * item.stat().st_size)
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)

    log_event("SIMULATED DATA WIPE COMPLETED")
    log_event("SYSTEM STATUS: LOCKED")
