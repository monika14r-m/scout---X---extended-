"""Unit tests for the Case 1 MAVLink command acknowledgement gate."""

import sys
import types
import unittest
from unittest.mock import patch

try:
    from pymavlink import mavutil  # noqa: F401
except ModuleNotFoundError:
    # The command helper only needs MAV_RESULT_ACCEPTED. Keep these focused
    # tests runnable without installing the SITL dependency.
    pymavlink_stub = types.ModuleType("pymavlink")
    pymavlink_stub.mavutil = types.SimpleNamespace(
        mavlink=types.SimpleNamespace(MAV_RESULT_ACCEPTED=0)
    )
    sys.modules["pymavlink"] = pymavlink_stub

from scoutx_live.__main__ import send_command_and_confirm


class FakeAck:
    def __init__(self, command, result):
        self.command = command
        self.result = result


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

    def test_accepts_matching_success_ack_and_sends_command(self):
        master = FakeMaster([FakeAck(self.COMMAND, 0)])
        with patch("scoutx_live.__main__.log_event") as log_event:
            send_command_and_confirm(master, self.COMMAND, self.PARAMS, "ARM")

        self.assertEqual(
            master.mav.sent,
            (1, 1, self.COMMAND, 0, *self.PARAMS),
        )
        self.assertEqual(master.recv_filters, [("COMMAND_ACK", True)])
        log_event.assert_called_once_with(
            "GCS_COMMAND_ACKNOWLEDGED",
            command="ARM",
            command_id=self.COMMAND,
            ack_result=0,
        )

    def test_rejects_matching_negative_ack(self):
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

    def test_ignores_unrelated_ack_until_matching_ack_arrives(self):
        master = FakeMaster([
            FakeAck(self.COMMAND + 1, 0),
            FakeAck(self.COMMAND, 0),
        ])
        with patch("scoutx_live.__main__.log_event") as log_event:
            send_command_and_confirm(master, self.COMMAND, self.PARAMS, "ARM")

        self.assertEqual(master.acknowledgements, [])
        self.assertEqual(
            master.recv_filters,
            [("COMMAND_ACK", True), ("COMMAND_ACK", True)],
        )
        log_event.assert_called_once_with(
            "GCS_COMMAND_ACKNOWLEDGED",
            command="ARM",
            command_id=self.COMMAND,
            ack_result=0,
        )

    def test_times_out_when_no_ack_is_received(self):
        master = FakeMaster()
        with patch("scoutx_live.__main__.log_event") as log_event:
            with self.assertRaisesRegex(TimeoutError, "No COMMAND_ACK received"):
                send_command_and_confirm(
                    master, self.COMMAND, self.PARAMS, "ARM", timeout=0
                )

        self.assertEqual(master.recv_filters, [])
        log_event.assert_called_once_with(
            "GCS_COMMAND_ACK_TIMEOUT",
            command="ARM",
            command_id=self.COMMAND,
            timeout_s=0,
        )


if __name__ == "__main__":
    unittest.main()
