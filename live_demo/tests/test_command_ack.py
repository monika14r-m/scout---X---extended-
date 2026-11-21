"""Unit tests for the Case 1 MAVLink command acknowledgement gate."""

import sys
import types
import unittest
from unittest.mock import call, patch

try:
    from pymavlink import mavutil  # noqa: F401
except ModuleNotFoundError:
    # The command helper only needs MAV_RESULT_ACCEPTED. Keep these focused
    # tests runnable without installing the SITL dependency.
    pymavlink_stub = types.ModuleType("pymavlink")
    pymavlink_stub.mavutil = types.SimpleNamespace(
        mavlink=types.SimpleNamespace(MAV_RESULT_ACCEPTED=0, MAV_RESULT_IN_PROGRESS=5)
    )
    sys.modules["pymavlink"] = pymavlink_stub

from scoutx_live.__main__ import (
    run_gps_spoof,
    send_command_and_confirm,
    validate_gps_spoof_offset,
)


class FakeAck:
    def __init__(self, command, result, source_system=1, source_component=1, progress=255):
        self.command = command
        self.result = result
        self.source_system = source_system
        self.source_component = source_component
        self.progress = progress

    def get_srcSystem(self):
        return self.source_system

    def get_srcComponent(self):
        return self.source_component


class FakeMav:
    def __init__(self):
        self.sent = None

    def command_long_send(self, *args):
        self.sent = args


class FakeMaster:
    target_system = 1
    target_component = 1

    def __init__(self, acknowledgements=()):
        self.mav = FakeMav()
        self.acknowledgements = list(acknowledgements)
        self.recv_filters = []

    def recv_match(self, *, type, blocking, timeout):
        self.recv_filters.append((type, blocking))
        if self.acknowledgements:
            return self.acknowledgements.pop(0)
        return None


class SendCommandAndConfirmTests(unittest.TestCase):
    COMMAND = 400
    PARAMS = [1, 0, 0, 0, 0, 0, 0]

    def test_accepts_matching_success_ack_from_target(self):
        master = FakeMaster([FakeAck(self.COMMAND, 0)])
        with patch("scoutx_live.__main__.log_event") as log_event:
            send_command_and_confirm(master, self.COMMAND, self.PARAMS, "ARM")

        self.assertEqual(
            master.mav.sent,
            (1, 1, self.COMMAND, 0, *self.PARAMS),
        )
        log_event.assert_called_once_with(
            "GCS_COMMAND_ACKNOWLEDGED",
            command="ARM",
            command_id=self.COMMAND,
            ack_result=0,
        )

    def test_rejects_matching_negative_ack_from_target(self):
        master = FakeMaster([FakeAck(self.COMMAND, 2)])
        with patch("scoutx_live.__main__.log_event") as log_event:
            with self.assertRaisesRegex(RuntimeError, "SITL rejected ARM"):
                send_command_and_confirm(master, self.COMMAND, self.PARAMS, "ARM")

        log_event.assert_called_once_with(
            "GCS_COMMAND_REJECTED",
            command="ARM",
            command_id=self.COMMAND,
            ack_result=2,
        )

    def test_ignores_unrelated_command_ack(self):
        master = FakeMaster([
            FakeAck(self.COMMAND + 1, 0),
            FakeAck(self.COMMAND, 0),
        ])
        with patch("scoutx_live.__main__.log_event") as log_event:
            send_command_and_confirm(master, self.COMMAND, self.PARAMS, "ARM")

        self.assertEqual(master.acknowledgements, [])
        log_event.assert_called_once_with(
            "GCS_COMMAND_ACKNOWLEDGED",
            command="ARM",
            command_id=self.COMMAND,
            ack_result=0,
        )

    def test_ignores_matching_ack_from_unexpected_system(self):
        master = FakeMaster([
            FakeAck(self.COMMAND, 0, source_system=42),
            FakeAck(self.COMMAND, 0),
        ])
        with patch("scoutx_live.__main__.log_event") as log_event:
            send_command_and_confirm(master, self.COMMAND, self.PARAMS, "ARM")

        self.assertEqual(log_event.call_args_list, [
            call(
                "GCS_COMMAND_ACK_IGNORED",
                reason="unexpected_source",
                command="ARM",
                command_id=self.COMMAND,
                source_system=42,
                source_component=1,
                expected_system=1,
                expected_component=1,
            ),
            call(
                "GCS_COMMAND_ACKNOWLEDGED",
                command="ARM",
                command_id=self.COMMAND,
                ack_result=0,
            ),
        ])

    def test_ignores_matching_ack_from_unexpected_component(self):
        master = FakeMaster([
            FakeAck(self.COMMAND, 0, source_component=190),
            FakeAck(self.COMMAND, 0),
        ])
        with patch("scoutx_live.__main__.log_event") as log_event:
            send_command_and_confirm(master, self.COMMAND, self.PARAMS, "ARM")

        self.assertEqual(log_event.call_count, 2)
        self.assertEqual(
            log_event.call_args_list[0].args[0],
            "GCS_COMMAND_ACK_IGNORED",
        )
        self.assertEqual(
            log_event.call_args_list[1].args[0],
            "GCS_COMMAND_ACKNOWLEDGED",
        )

    def test_waits_for_final_ack_after_in_progress(self):
        master = FakeMaster([
            FakeAck(self.COMMAND, 5, progress=35),
            FakeAck(self.COMMAND, 0),
        ])
        with patch("scoutx_live.__main__.log_event") as log_event:
            send_command_and_confirm(master, self.COMMAND, self.PARAMS, "ARM")

        self.assertEqual(log_event.call_args_list, [
            call(
                "GCS_COMMAND_ACK_IN_PROGRESS",
                command="ARM",
                command_id=self.COMMAND,
                progress=35,
            ),
            call(
                "GCS_COMMAND_ACKNOWLEDGED",
                command="ARM",
                command_id=self.COMMAND,
                ack_result=0,
            ),
        ])

    def test_rejects_final_negative_ack_after_in_progress(self):
        master = FakeMaster([
            FakeAck(self.COMMAND, 5, progress=60),
            FakeAck(self.COMMAND, 2),
        ])
        with patch("scoutx_live.__main__.log_event") as log_event:
            with self.assertRaisesRegex(RuntimeError, "SITL rejected ARM"):
                send_command_and_confirm(master, self.COMMAND, self.PARAMS, "ARM")

        self.assertEqual(
            [event.args[0] for event in log_event.call_args_list],
            ["GCS_COMMAND_ACK_IN_PROGRESS", "GCS_COMMAND_REJECTED"],
        )

    def test_times_out_after_in_progress_without_final_ack(self):
        master = FakeMaster([FakeAck(self.COMMAND, 5, progress=20)])
        with patch("scoutx_live.__main__.log_event") as log_event:
            with self.assertRaisesRegex(TimeoutError, "No COMMAND_ACK received"):
                send_command_and_confirm(
                    master, self.COMMAND, self.PARAMS, "ARM", timeout=0.01
                )

        self.assertEqual(
            [event.args[0] for event in log_event.call_args_list],
            ["GCS_COMMAND_ACK_IN_PROGRESS", "GCS_COMMAND_ACK_TIMEOUT"],
        )

    def test_times_out_after_waiting_without_ack(self):
        master = FakeMaster()
        with (
            patch("scoutx_live.__main__.log_event") as log_event,
            patch(
                "scoutx_live.__main__.time.monotonic",
                side_effect=[100.0, 100.0, 100.0, 101.0],
            ),
        ):
            with self.assertRaisesRegex(TimeoutError, "No COMMAND_ACK received"):
                send_command_and_confirm(
                    master, self.COMMAND, self.PARAMS, "ARM", timeout=1
                )

        self.assertEqual(master.recv_filters, [("COMMAND_ACK", True)])
        log_event.assert_called_once_with(
            "GCS_COMMAND_ACK_TIMEOUT",
            command="ARM",
            command_id=self.COMMAND,
            timeout_s=1,
        )


class GPSOffsetValidationTests(unittest.TestCase):
    def test_accepts_zero_and_positive_offsets(self):
        self.assertEqual(validate_gps_spoof_offset(0), 0.0)
        self.assertEqual(validate_gps_spoof_offset(35), 35.0)
        self.assertEqual(validate_gps_spoof_offset("12.5"), 12.5)

    def test_rejects_negative_nonfinite_boolean_and_non_numeric_offsets(self):
        cases = [
            ("negative", -1),
            ("nan", float("nan")),
            ("positive infinity", float("inf")),
            ("negative infinity", float("-inf")),
            ("boolean", True),
            ("text", "bad"),
            ("null", None),
        ]
        for label, value in cases:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    validate_gps_spoof_offset(value)

    def test_invalid_offsets_fail_before_reading_telemetry(self):
        invalid_offsets = (-1, float("nan"), float("inf"), True, "bad", None)
        with patch("scoutx_live.__main__.read_position") as read_position:
            for offset in invalid_offsets:
                with self.subTest(offset=repr(offset)):
                    with self.assertRaises(ValueError):
                        run_gps_spoof(None, offset, "NONE")
        read_position.assert_not_called()


if __name__ == "__main__":
    unittest.main()
