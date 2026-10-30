import math
import unittest


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
