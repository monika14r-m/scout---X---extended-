"""
telemetry/telemetry_stream.py

Defines the core telemetry sample structure used across SCOUT-X, and a
rolling stream buffer that detection modules read from.

Each TelemetrySample carries multi-sensor data (GPS, IMU, barometer) plus
metadata. `ground_truth_attack` is carried ONLY for offline evaluation
(computing detection metrics) -- the detection engine must never read it.
"""

from dataclasses import dataclass, field
from typing import Optional, List
import json
import time


@dataclass
class TelemetrySample:
    timestamp: float                 # seconds since sim start
    seq: int                         # monotonic sequence number

    # GPS
    gps_lat: float
    gps_lon: float
    gps_alt: float                   # meters
    gps_speed: float                 # m/s, GPS-derived ground speed

    # IMU
    imu_accel: tuple                 # (ax, ay, az) m/s^2
    imu_gyro: tuple                  # (gx, gy, gz) rad/s

    # Barometer
    baro_alt: float                  # meters, independent altitude estimate

    # Command channel (what the flight controller was told to do)
    cmd_waypoint: tuple              # (lat, lon, alt) commanded target
    cmd_max_velocity: float          # m/s, platform's declared max velocity

    # Evaluation-only field. Detection code must not read this.
    ground_truth_attack: Optional[str] = None

    def to_dict(self):
        d = self.__dict__.copy()
        return d


class TelemetryStream:
    """Rolling buffer of telemetry samples for a single UAV session."""

    def __init__(self, maxlen: int = 5000):
        if isinstance(maxlen, bool) or not isinstance(maxlen, int):
            raise TypeError("maxlen must be a positive integer")
        if maxlen <= 0:
            raise ValueError("maxlen must be positive")
        self.maxlen = maxlen
        self.samples: List[TelemetrySample] = []

    def append(self, sample: TelemetrySample):
        self.samples.append(sample)
        if len(self.samples) > self.maxlen:
            self.samples.pop(0)

    def recent(self, n: int) -> List[TelemetrySample]:
        """Return the latest n samples; n must be a non-negative integer."""
        if isinstance(n, bool) or not isinstance(n, int):
            raise TypeError("n must be an integer")
        if n < 0:
            raise ValueError("n must be non-negative")
        if n == 0:
            return []
        return self.samples[-n:]

    def dump_json(self, path: str, strip_ground_truth: bool = False):
        rows = []
        for s in self.samples:
            d = s.to_dict()
            if strip_ground_truth:
                d.pop("ground_truth_attack", None)
            rows.append(d)
        with open(path, "w") as f:
            json.dump(rows, f, indent=2)
