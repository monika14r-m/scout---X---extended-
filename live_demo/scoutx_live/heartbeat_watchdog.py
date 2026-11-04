"""Timeout detection for MAVLink heartbeats emitted by a ground-control station."""

import math
import time

# MAVLink common.xml: MAV_TYPE_GCS.
MAV_TYPE_GCS = 6


class HeartbeatWatchdog:
    """Track the last valid GCS heartbeat using a monotonic clock."""

    def __init__(self, timeout_s):
        try:
            timeout = float(timeout_s)
        except (TypeError, ValueError) as exc:
            raise ValueError("heartbeat timeout must be a finite positive number") from exc
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("heartbeat timeout must be a finite positive number")
        self.timeout_s = timeout
        self.last_heartbeat_at = None

    @property
    def has_seen_heartbeat(self):
        return self.last_heartbeat_at is not None

    @staticmethod
    def _clock_value(now):
        value = time.monotonic() if now is None else float(now)
        if not math.isfinite(value):
            raise ValueError("heartbeat timestamp must be finite")
        return value

    def observe(self, message, now=None):
        """Record a GCS HEARTBEAT; ignore other MAVLink message/source types."""
        if message is None:
            return False
        get_type = getattr(message, "get_type", None)
        if not callable(get_type) or get_type() != "HEARTBEAT":
            return False
        if getattr(message, "type", None) != MAV_TYPE_GCS:
            return False

        observed_at = self._clock_value(now)
        if self.last_heartbeat_at is not None and observed_at < self.last_heartbeat_at:
            raise ValueError("monotonic heartbeat time cannot move backwards")
        self.last_heartbeat_at = observed_at
        return True

    def seconds_until_timeout(self, now=None):
        if self.last_heartbeat_at is None:
            return None
        current = self._clock_value(now)
        if current < self.last_heartbeat_at:
            raise ValueError("monotonic heartbeat time cannot move backwards")
        elapsed = current - self.last_heartbeat_at
        return max(0.0, self.timeout_s - elapsed)

    def is_lost(self, now=None):
        remaining = self.seconds_until_timeout(now)
        return remaining is not None and remaining <= 0.0
