import math
import unittest
from types import SimpleNamespace

from trust_score import TrustScoreEngine


class GPSOffsetTests(unittest.TestCase):
    def test_offset_conversion_is_finite(self):
        lat = 12.9716
        offset_m = 35.0
        dlat = offset_m / 111320.0
        dlon = offset_m / (111320.0 * math.cos(math.radians(lat)))
        distance = math.hypot(dlat * 111320.0, dlon * 111320.0 * math.cos(math.radians(lat)))
        self.assertTrue(math.isfinite(distance))
        self.assertGreater(distance, 40.0)


if __name__ == "__main__":
    unittest.main()


class TrustScoreNonFiniteTests(unittest.TestCase):
    def test_non_finite_scores_fail_closed(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                self.assertEqual(TrustScoreEngine._clamp(value), 0.0)

    def test_finite_scores_remain_bounded(self):
        for value, expected in ((-1.0, 0.0), (0.4, 0.4), (2.0, 1.0)):
            with self.subTest(value=value):
                self.assertAlmostEqual(
                    TrustScoreEngine._clamp(value),
                    expected,
                )

    def test_nan_gps_speed_is_marked_untrusted(self):
        sample = SimpleNamespace(
            timestamp=0.0,
            seq=1,
            gps_lat=12.9716,
            gps_lon=77.5946,
            gps_alt=10.0,
            gps_speed=math.nan,
            imu_accel=(0.0, 0.0, 0.0),
            baro_alt=10.0,
            cmd_max_velocity=10.0,
            cmd_waypoint=(12.9716, 77.5946, 10.0),
        )

        result = TrustScoreEngine().evaluate(sample)

        self.assertEqual(result["checks"]["gps_kinematics"], 0.0)
        self.assertIn("gps", result["untrusted_components"])
        self.assertLess(result["overall_trust"], 1.0)
