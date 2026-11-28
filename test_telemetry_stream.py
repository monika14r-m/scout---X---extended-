import unittest

from telemetry_stream import TelemetrySample, TelemetryStream


def sample(seq):
    return TelemetrySample(
        timestamp=float(seq),
        seq=seq,
        gps_lat=0.0,
        gps_lon=0.0,
        gps_alt=10.0,
        gps_speed=0.0,
        imu_accel=(0.0, 0.0, 0.0),
        imu_gyro=(0.0, 0.0, 0.0),
        baro_alt=10.0,
        cmd_waypoint=(0.0, 0.0, 10.0),
        cmd_max_velocity=5.0,
    )


class TelemetryStreamRecentTests(unittest.TestCase):
    def setUp(self):
        self.stream = TelemetryStream()
        for seq in range(1, 4):
            self.stream.append(sample(seq))

    def test_recent_zero_returns_empty(self):
        self.assertEqual(self.stream.recent(0), [])

    def test_recent_returns_latest_samples_in_order(self):
        self.assertEqual([s.seq for s in self.stream.recent(2)], [2, 3])

    def test_recent_larger_than_buffer_returns_all_samples(self):
        self.assertEqual([s.seq for s in self.stream.recent(10)], [1, 2, 3])

    def test_recent_negative_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self.stream.recent(-1)

    def test_recent_non_integer_count_is_rejected(self):
        for value in (1.5, True, "2"):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    self.stream.recent(value)

    def test_buffer_keeps_only_maxlen_samples(self):
        stream = TelemetryStream(maxlen=2)
        for seq in range(1, 4):
            stream.append(sample(seq))
        self.assertEqual([s.seq for s in stream.recent(10)], [2, 3])

    def test_maxlen_must_be_positive(self):
        for value in (0, -1):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "positive"):
                    TelemetryStream(maxlen=value)

    def test_maxlen_must_be_integer(self):
        for value in (1.5, True, "2"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "positive integer"):
                    TelemetryStream(maxlen=value)


if __name__ == "__main__":
    unittest.main()
