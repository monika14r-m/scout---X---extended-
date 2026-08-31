"""
attacks/attack_injector.py

Injects simulated attack conditions into an otherwise-clean telemetry
stream, for evaluating the detection engine. This models FAULT/ATTACK
CONDITIONS AT THE SENSOR-DATA LEVEL for anomaly-detection testing -- it
does not implement any real RF/GPS signal attack; it perturbs the
simulated telemetry values the same way those attacks would corrupt them
downstream, which is the standard way to evaluate anomaly detectors
against attack classes you can't safely reproduce on real hardware.

Attack classes implemented:
  - gps_spoofing        : GPS position jumps to a false location
  - imu_manipulation    : IMU acceleration/gyro readings are corrupted
  - control_hijack      : commanded waypoint is overwritten (unauthorized command)
  - baro_interference   : barometer altitude reading is corrupted
"""

import random
from dataclasses import replace
from telemetry.telemetry_stream import TelemetrySample


class AttackSchedule:
    """A single scheduled attack window: [start_t, end_t) with a type."""

    def __init__(self, attack_type: str, start_t: float, end_t: float):
        self.attack_type = attack_type
        self.start_t = start_t
        self.end_t = end_t

    def active_at(self, t: float) -> bool:
        return self.start_t <= t < self.end_t


class AttackInjector:
    def __init__(self, schedule):
        self.schedule: list = schedule

    def _active_attack(self, t: float):
        for a in self.schedule:
            if a.active_at(t):
                return a.attack_type
        return None

    def apply(self, sample: TelemetrySample) -> TelemetrySample:
        attack = self._active_attack(sample.timestamp)
        if attack is None:
            return sample

        if attack == "gps_spoofing":
            # Jump GPS to a false position ~150m away, inconsistent with
            # platform's max velocity -> should trip cross-sensor checks.
            sample = replace(
                sample,
                gps_lat=sample.gps_lat + 0.0014,
                gps_lon=sample.gps_lon + 0.0014,
                gps_speed=sample.gps_speed + random.uniform(20, 40),
                ground_truth_attack=attack,
            )

        elif attack == "imu_manipulation":
            ax, ay, az = sample.imu_accel
            sample = replace(
                sample,
                imu_accel=(ax + random.uniform(8, 15), ay + random.uniform(8, 15), az),
                imu_gyro=(random.uniform(2, 4), random.uniform(2, 4), random.uniform(2, 4)),
                ground_truth_attack=attack,
            )

        elif attack == "control_hijack":
            # Unauthorized waypoint far outside the declared patrol area,
            # requiring an implied velocity beyond cmd_max_velocity.
            lat, lon, alt = sample.cmd_waypoint
            sample = replace(
                sample,
                cmd_waypoint=(lat + 0.01, lon + 0.01, alt + 200),
                ground_truth_attack=attack,
            )

        elif attack == "baro_interference":
            sample = replace(
                sample,
                baro_alt=sample.baro_alt + random.uniform(30, 60),
                ground_truth_attack=attack,
            )

        return sample


def default_schedule(total_duration: float) -> list:
    """A reasonable default schedule spreading 4 attack types across the run."""
    quarter = total_duration / 5.0
    return [
        AttackSchedule("gps_spoofing", quarter * 1, quarter * 1 + 3.0),
        AttackSchedule("imu_manipulation", quarter * 2, quarter * 2 + 2.0),
        AttackSchedule("control_hijack", quarter * 3, quarter * 3 + 4.0),
        AttackSchedule("baro_interference", quarter * 4, quarter * 4 + 2.5),
    ]
