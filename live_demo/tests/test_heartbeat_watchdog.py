import math
import unittest

from scoutx_live.heartbeat_watchdog import HeartbeatWatchdog, MAV_TYPE_GCS


class FakeMavlinkMessage:
    def __init__(self, message_type="HEARTBEAT", vehicle_type=MAV_TYPE_GCS):
        self.message_type = message_type
        self.type = vehicle_type

    def get_type(self):
        return self.message_type


class HeartbeatWatchdogTests(unittest.TestCase):
    def test_does_not_report_loss_before_first_gcs_heartbeat(self):
        watchdog = HeartbeatWatchdog(3)
        self.assertFalse(watchdog.has_seen_heartbeat)
        self.assertFalse(watchdog.is_lost(now=100))
        self.assertIsNone(watchdog.seconds_until_timeout(now=100))

    def test_ignores_vehicle_heartbeats_and_non_heartbeat_messages(self):
        watchdog = HeartbeatWatchdog(3)
        vehicle_heartbeat = FakeMavlinkMessage(vehicle_type=2)
        gps_message = FakeMavlinkMessage(message_type="GPS_RAW_INT")
        self.assertFalse(watchdog.observe(vehicle_heartbeat, now=10))
        self.assertFalse(watchdog.observe(gps_message, now=10))
        self.assertFalse(watchdog.has_seen_heartbeat)

    def test_reports_loss_at_timeout_boundary(self):
        watchdog = HeartbeatWatchdog(3)
        self.assertTrue(watchdog.observe(FakeMavlinkMessage(), now=10))
        self.assertFalse(watchdog.is_lost(now=12.999))
        self.assertTrue(watchdog.is_lost(now=13))

    def test_new_gcs_heartbeat_resets_deadline(self):
        watchdog = HeartbeatWatchdog(3)
        watchdog.observe(FakeMavlinkMessage(), now=10)
        watchdog.observe(FakeMavlinkMessage(), now=12)
        self.assertFalse(watchdog.is_lost(now=14.9))
        self.assertTrue(watchdog.is_lost(now=15))

    def test_rejects_invalid_timeouts(self):
        for value in (0, -1, math.nan, math.inf, -math.inf, "bad"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    HeartbeatWatchdog(value)

    def test_rejects_clock_regression(self):
        watchdog = HeartbeatWatchdog(3)
        watchdog.observe(FakeMavlinkMessage(), now=10)
        with self.assertRaises(ValueError):
            watchdog.is_lost(now=9)
        with self.assertRaises(ValueError):
            watchdog.observe(FakeMavlinkMessage(), now=9)


if __name__ == "__main__":
    unittest.main()
