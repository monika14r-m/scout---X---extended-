"""Non-destructive security-event logging for the SCOUT-X demo.

This compatibility module records an auditable lockdown event only. It never
overwrites or deletes files; destructive data handling is outside this simulator.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_FILE = PROJECT_ROOT / "logs" / "security_events.jsonl"


def log_event(message: str, **details) -> dict:
    """Append one structured, UTC-timestamped event to the local demo log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": "SCOUT-X",
        "message": str(message),
        **details,
    }
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(json.dumps(event, ensure_ascii=False))
    return event


def secure_wipe_simulation() -> dict:
    """Record a simulated wipe request without touching user or project files."""
    log_event(
        "SIMULATED_DATA_WIPE_REQUESTED",
        response="NON_DESTRUCTIVE_DEMO_LOCKDOWN",
        destructive_actions=False,
        files_modified=0,
        files_deleted=0,
    )
    result = {
        "status": "SIMULATED_ONLY",
        "locked": True,
        "destructive_actions": False,
        "files_modified": 0,
        "files_deleted": 0,
    }
    log_event("DEMO_LOCKDOWN_COMPLETED", **result)
    return result
