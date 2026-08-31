"""
simulation/uav_simulator.py

Generates synthetic but physically-plausible UAV telemetry: GPS, IMU,
barometer, and the active flight command. This is a standalone Python
model (no ROS2/ArduPilot dependency) so the pipeline runs anywhere --
swap this module for a real ROS2/ArduPilot bridge later without touching
detection or response code, since both only depend on TelemetrySample.

Flight profile: takeoff -> cruise along a waypoint path -> loiter.
"""

import math
import random
from telemetry.telemetry_stream import TelemetrySample

EARTH_RADIUS_M = 6371000.0


def meters_to_latlon_offset(lat0, lon0, dx, dy):
    """Convert a local ENU offset (meters) to lat/lon near (lat0, lon0)."""
    dlat = dy / EARTH_RADIUS_M
    dlon = dx / (EARTH_RADIUS_M * math.cos(math.radians(lat0)))
    return lat0 + math.degrees(dlat), lon0 + math.degrees(dlon)


class UAVSimulator:
    def __init__(self, seed: int = 42, hz: float = 10.0):
        random.seed(seed)
        self.hz = hz
        self.dt = 1.0 / hz
        self.t = 0.0
        self.seq = 0

        # Home / origin
        self.home_lat = 12.9716
        self.home_lon = 77.5946
        self.cruise_alt = 60.0       # meters
        self.max_velocity = 15.0     # m/s, platform limit

        # Local position state (meters, ENU from home)
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0

        # Simple square patrol path (local meters)
        self.waypoints = [(0, 0), (200, 0), (200, 200), (0, 200), (0, 0)]
        self.wp_idx = 1

    def _current_waypoint(self):
        return self.waypoints[self.wp_idx]

    def _advance_waypoint_if_reached(self):
        wx, wy = self._current_waypoint()
        if math.hypot(wx - self.x, wy - self.y) < 5.0:
            self.wp_idx = (self.wp_idx + 1) % len(self.waypoints)

    def step(self) -> TelemetrySample:
        self._advance_waypoint_if_reached()
        wx, wy = self._current_waypoint()

        # Steer toward current waypoint at up to max_velocity, with noise
        dx, dy = wx - self.x, wy - self.y
        dist = math.hypot(dx, dy) or 1e-6
        speed = min(self.max_velocity * 0.6, dist)  # cruise at 60% of max
        self.vx = (dx / dist) * speed + random.gauss(0, 0.05)
        self.vy = (dy / dist) * speed + random.gauss(0, 0.05)
        self.vz = random.gauss(0, 0.02)

        self.x += self.vx * self.dt
        self.y += self.vy * self.dt
        self.z = self.cruise_alt + random.gauss(0, 0.1)

        gps_lat, gps_lon = meters_to_latlon_offset(self.home_lat, self.home_lon, self.x, self.y)
        gps_speed = math.hypot(self.vx, self.vy) + random.gauss(0, 0.03)

        accel = (
            random.gauss(0, 0.15),
            random.gauss(0, 0.15),
            9.81 + random.gauss(0, 0.05),
        )
        gyro = (random.gauss(0, 0.01), random.gauss(0, 0.01), random.gauss(0, 0.01))

        baro_alt = self.z + random.gauss(0, 0.3)

        cmd_wp_lat, cmd_wp_lon = meters_to_latlon_offset(self.home_lat, self.home_lon, wx, wy)

        sample = TelemetrySample(
            timestamp=round(self.t, 3),
            seq=self.seq,
            gps_lat=gps_lat,
            gps_lon=gps_lon,
            gps_alt=self.z,
            gps_speed=gps_speed,
            imu_accel=accel,
            imu_gyro=gyro,
            baro_alt=baro_alt,
            cmd_waypoint=(cmd_wp_lat, cmd_wp_lon, self.cruise_alt),
            cmd_max_velocity=self.max_velocity,
            ground_truth_attack=None,
        )

        self.t += self.dt
        self.seq += 1
        return sample
