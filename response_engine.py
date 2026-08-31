"""
response/response_engine.py

Acts on detection output. Implements graduated response, not just an
alarm:

  1. ISOLATE  - a single untrusted component is dropped from the fusion
                solution (e.g. stop trusting GPS, fall back to IMU dead-
                reckoning + barometer for altitude).
  2. ESCALATE - if a component stays untrusted for `escalate_after`
                consecutive detections, or if multiple components are
                untrusted simultaneously, escalate to emergency response.
  3. EMERGENCY - trigger RTL (return-to-launch) fallback and a simulated
                secure wipe of mission-sensitive data.

This module simulates the response actions (logs what it would do) --
it does not implement autopilot control or real data destruction. Wire
`_execute_rtl` / `_execute_secure_wipe` to real ArduPilot MAVLink calls
and real storage APIs respectively when integrating with hardware.
"""


class ResponseEngine:
    def __init__(self, escalate_after: int = 3):
        self.escalate_after = escalate_after
        self.untrusted_streak = {}   # component -> consecutive detection count
        self.isolated_components = set()
        self.emergency_triggered = False
        self.log = []

    def _record(self, entry: dict):
        self.log.append(entry)

    def handle(self, detection: dict):
        if not detection["is_anomaly"]:
            # Decay streaks on clean samples
            for comp in list(self.untrusted_streak.keys()):
                self.untrusted_streak[comp] = max(0, self.untrusted_streak[comp] - 1)
                if self.untrusted_streak[comp] == 0:
                    self.untrusted_streak.pop(comp)
                    if comp in self.isolated_components:
                        self.isolated_components.discard(comp)
                        self._record({
                            "timestamp": detection["timestamp"],
                            "action": "RESTORE",
                            "component": comp,
                        })
            return

        for comp in detection["untrusted_components"]:
            self.untrusted_streak[comp] = self.untrusted_streak.get(comp, 0) + 1

            if comp not in self.isolated_components:
                self.isolated_components.add(comp)
                self._record({
                    "timestamp": detection["timestamp"],
                    "action": "ISOLATE",
                    "component": comp,
                    "trust_score": detection["component_scores"][comp],
                })

        multi_component_compromise = len(detection["untrusted_components"]) >= 2
        sustained_compromise = any(
            streak >= self.escalate_after for streak in self.untrusted_streak.values()
        )

        if (multi_component_compromise or sustained_compromise) and not self.emergency_triggered:
            self.emergency_triggered = True
            self._record({
                "timestamp": detection["timestamp"],
                "action": "EMERGENCY_ESCALATION",
                "reason": "multi_component_compromise" if multi_component_compromise else "sustained_compromise",
                "components": detection["untrusted_components"],
            })
            self._execute_rtl(detection)
            self._execute_secure_wipe(detection)

    def _execute_rtl(self, detection: dict):
        self._record({
            "timestamp": detection["timestamp"],
            "action": "RTL_TRIGGERED",
            "note": "Falling back to last known-good waypoint / return-to-launch.",
        })

    def _execute_secure_wipe(self, detection: dict):
        self._record({
            "timestamp": detection["timestamp"],
            "action": "SECURE_WIPE_TRIGGERED",
            "note": "Simulated wipe of mission-sensitive telemetry/config from onboard storage.",
        })

    def reset_emergency(self):
        """Call after human/ground-station confirms the threat has cleared."""
        self.emergency_triggered = False
