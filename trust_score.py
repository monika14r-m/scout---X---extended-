"""
SCOUT-X Trust Score Engine

Evaluates UAV telemetry using basic physical and consistency checks.
The trust score decreases when abnormal behaviour is detected and
recovers gradually when normal telemetry is received.

Score:
    1.0  -> normal / trusted
    0.0  -> highly suspicious

The engine does not use attack labels during detection.
"""

import math


class TrustScoreEngine:
    def __init__(
        self,
        alert_threshold: float = 0.55,
        recovery_rate: float = 0.05,
    ):
        self.alert_threshold = alert_threshold
        self.recovery_rate = recovery_rate
        self.trust_score = 1.0
        self.prev_sample = None

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

    # ------------------------------------------------------------------
    # Telemetry checks
    # ------------------------------------------------------------------

    def _check_gps_kinematics(self, sample) -> float:
        """Check whether reported GPS speed is physically reasonable."""

        limit = sample.cmd_max_velocity * 1.3

        if sample.gps_speed <= limit:
            return 1.0

        excess = sample.gps_speed - limit
        return self._clamp(1.0 - excess / 20.0)

    def _check_gps_imu_consistency(self, sample) -> float:
        """
        Compare GPS-derived movement with IMU acceleration.
        A large GPS jump without corresponding movement is suspicious.
        """

        if self.prev_sample is None:
            return 1.0

        dt = max(
            sample.timestamp - self.prev_sample.timestamp,
            0.001
        )

        dlat = sample.gps_lat - self.prev_sample.gps_lat
        dlon = sample.gps_lon - self.prev_sample.gps_lon

        dx = (
            dlon
            * 111320
            * math.cos(math.radians(sample.gps_lat))
        )
        dy = dlat * 111320

        implied_speed = math.hypot(dx, dy) / dt

        ax, ay, _ = sample.imu_accel
        lateral_accel = math.hypot(ax, ay)

        if (
            implied_speed > sample.cmd_max_velocity * 1.5
            and lateral_accel < 2.0
        ):
            return 0.1

        if implied_speed > sample.cmd_max_velocity * 1.3:
            return 0.5

        return 1.0

    def _check_imu_bounds(self, sample) -> float:
        """Check for unusually large lateral acceleration."""

        ax, ay, _ = sample.imu_accel
        lateral = math.hypot(ax, ay)

        if lateral <= 4.0:
            return 1.0

        return self._clamp(
            1.0 - (lateral - 4.0) / 15.0
        )

    def _check_baro_gps_consistency(self, sample) -> float:
        """Compare barometric and GPS altitude."""

        difference = abs(
            sample.baro_alt - sample.gps_alt
        )

        if difference <= 5.0:
            return 1.0

        return self._clamp(
            1.0 - (difference - 5.0) / 40.0
        )

    def _check_command_integrity(self, sample) -> float:
        """
        Check whether the commanded waypoint changes within a
        physically reachable distance between telemetry samples.
        """

        if self.prev_sample is None:
            return 1.0

        dt = max(
            sample.timestamp - self.prev_sample.timestamp,
            0.001
        )

        prev_lat, prev_lon, prev_alt = self.prev_sample.cmd_waypoint
        curr_lat, curr_lon, curr_alt = sample.cmd_waypoint

        dx = (
            (curr_lon - prev_lon)
            * 111320
            * math.cos(math.radians(curr_lat))
        )
        dy = (curr_lat - prev_lat) * 111320
        dz = curr_alt - prev_alt

        distance = math.sqrt(
            dx**2 + dy**2 + dz**2
        )

        max_reachable = (
            sample.cmd_max_velocity * dt * 2.0
        )

        if distance <= max_reachable or distance < 1.0:
            return 1.0

        ratio = distance / max(max_reachable, 0.001)

        return self._clamp(
            1.0 - (ratio - 1.0) / 4.0
        )

    # ------------------------------------------------------------------
    # Trust update
    # ------------------------------------------------------------------

    def _update_trust(self, checks: dict) -> float:
        """
        Update the running trust score.

        Severe anomalies cause a stronger decrease.
        Normal telemetry allows gradual recovery.
        """

        current_score = min(checks.values())

        if current_score < self.alert_threshold:
            # Stronger penalty for more severe anomalies
            penalty = (1.0 - current_score) * 0.20
            self.trust_score -= penalty
        else:
            # Gradual recovery during normal operation
            self.trust_score += self.recovery_rate

        self.trust_score = self._clamp(self.trust_score)

        return self.trust_score

    # ------------------------------------------------------------------
    # Main evaluation
    # ------------------------------------------------------------------

    def evaluate(self, sample) -> dict:

        checks = {
            "gps_kinematics":
                self._check_gps_kinematics(sample),

            "gps_imu_consistency":
                self._check_gps_imu_consistency(sample),

            "imu_bounds":
                self._check_imu_bounds(sample),

            "baro_gps_consistency":
                self._check_baro_gps_consistency(sample),

            "command_integrity":
                self._check_command_integrity(sample),
        }

        component_map = {
            "gps_kinematics": "gps",
            "gps_imu_consistency": "gps",
            "imu_bounds": "imu",
            "baro_gps_consistency": "barometer",
            "command_integrity": "command_channel",
        }

        component_scores = {}

        for check_name, score in checks.items():
            component = component_map[check_name]

            if component not in component_scores:
                component_scores[component] = score
            else:
                component_scores[component] = min(
                    component_scores[component],
                    score
                )

        self.trust_score = self._update_trust(checks)

        is_anomaly = (
            self.trust_score < self.alert_threshold
        )

        untrusted_components = [
            component
            for component, score in component_scores.items()
            if score < self.alert_threshold
        ]

        self.prev_sample = sample

        return {
            "timestamp": sample.timestamp,
            "seq": sample.seq,
            "checks": checks,
            "component_scores": component_scores,
            "overall_trust": round(self.trust_score, 3),
            "is_anomaly": is_anomaly,
            "untrusted_components": untrusted_components,
        }
