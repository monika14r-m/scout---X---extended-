"""
detection/trust_score.py

Core of SCOUT-X: a per-sensor trust-score engine that cross-checks GPS,
IMU, barometer, and the command channel against each other and against
physically-plausible limits, without relying on the ground-truth attack
label (which only exists for offline evaluation).

Approach: each check produces a score in [0, 1] (1 = fully trusted).
Sensor trust = weighted combination of its checks. Overall system trust
= min() across sensors (a single compromised sensor should be enough to
raise an alert, not get averaged away). Below `alert_threshold`, the
sample is flagged and the response engine is notified with which
component(s) are untrusted.
"""

import math
from collections import deque


class TrustScoreEngine:
    def __init__(self, window: int = 15, alert_threshold: float = 0.55):
        self.window = window
        self.alert_threshold = alert_threshold
        self.gps_speed_hist = deque(maxlen=window)
        self.baro_alt_hist = deque(maxlen=window)
        self.prev_sample = None

    # ---- individual checks -------------------------------------------------

    def _check_gps_kinematics(self, sample) -> float:
        """GPS-derived speed must not exceed platform max velocity by much."""
        if sample.gps_speed <= sample.cmd_max_velocity * 1.3:
            return 1.0
        excess = sample.gps_speed - sample.cmd_max_velocity * 1.3
        return max(0.0, 1.0 - excess / 20.0)

    def _check_gps_imu_consistency(self, sample) -> float:
        """Sudden GPS position jump with no corresponding IMU acceleration
        spike is a classic spoofing signature."""
        if self.prev_sample is None:
            return 1.0
        dt = max(sample.timestamp - self.prev_sample.timestamp, 1e-3)
        dlat = sample.gps_lat - self.prev_sample.gps_lat
        dlon = sample.gps_lon - self.prev_sample.gps_lon
        # rough meters conversion
        dx = dlon * 111320 * math.cos(math.radians(sample.gps_lat))
        dy = dlat * 111320
        implied_speed = math.hypot(dx, dy) / dt

        ax, ay, _ = sample.imu_accel
        imu_lateral_accel = math.hypot(ax, ay)

        # If implied GPS speed is high but IMU shows near-zero lateral
        # acceleration, GPS is likely spoofed rather than the vehicle
        # actually moving.
        if implied_speed > sample.cmd_max_velocity * 1.5 and imu_lateral_accel < 2.0:
            return 0.1
        return 1.0

    def _check_imu_bounds(self, sample) -> float:
        ax, ay, az = sample.imu_accel
        lateral = math.hypot(ax, ay)
        if lateral <= 4.0:
            return 1.0
        return max(0.0, 1.0 - (lateral - 4.0) / 15.0)

    def _check_baro_gps_consistency(self, sample) -> float:
        """Barometric altitude should track GPS altitude within tolerance."""
        diff = abs(sample.baro_alt - sample.gps_alt)
        if diff <= 5.0:
            return 1.0
        return max(0.0, 1.0 - (diff - 5.0) / 40.0)

    def _check_command_integrity(self, sample) -> float:
        """Commanded waypoint must be reachable within max velocity given
        elapsed time since last sample -- catches injected/hijacked
        commands that imply teleportation."""
        if self.prev_sample is None:
            return 1.0
        dt = max(sample.timestamp - self.prev_sample.timestamp, 1e-3)
        plat, plon, palt = self.prev_sample.cmd_waypoint
        clat, clon, calt = sample.cmd_waypoint
        dx = (clon - plon) * 111320 * math.cos(math.radians(clat))
        dy = (clat - plat) * 111320
        dz = calt - palt
        dist = math.sqrt(dx**2 + dy**2 + dz**2)
        max_reachable = sample.cmd_max_velocity * dt * 5  # generous slack per tick
        if dist <= max_reachable or dist < 1.0:
            return 1.0
        excess_ratio = dist / max(max_reachable, 1e-3)
        return max(0.0, 1.0 - (excess_ratio - 1.0) / 5.0)

    # ---- aggregate -----------------------------------------------------------

    def evaluate(self, sample) -> dict:
        checks = {
            "gps_kinematics": self._check_gps_kinematics(sample),
            "gps_imu_consistency": self._check_gps_imu_consistency(sample),
            "imu_bounds": self._check_imu_bounds(sample),
            "baro_gps_consistency": self._check_baro_gps_consistency(sample),
            "command_integrity": self._check_command_integrity(sample),
        }

        # Map each check to the sensor/component it implicates most directly
        component_map = {
            "gps_kinematics": "gps",
            "gps_imu_consistency": "gps",
            "imu_bounds": "imu",
            "baro_gps_consistency": "barometer",
            "command_integrity": "command_channel",
        }
        component_scores = {}
        for check_name, score in checks.items():
            comp = component_map[check_name]
            component_scores[comp] = min(component_scores.get(comp, 1.0), score)

        overall_trust = min(component_scores.values())
        is_anomaly = overall_trust < self.alert_threshold
        untrusted_components = [c for c, s in component_scores.items() if s < self.alert_threshold]

        self.prev_sample = sample
        self.gps_speed_hist.append(sample.gps_speed)
        self.baro_alt_hist.append(sample.baro_alt)

        return {
            "timestamp": sample.timestamp,
            "seq": sample.seq,
            "checks": checks,
            "component_scores": component_scores,
            "overall_trust": overall_trust,
            "is_anomaly": is_anomaly,
            "untrusted_components": untrusted_components,
        }
