from .security_middleware import secure_wipe_simulation

class ResponseManager:
    def respond(self, threat):
        threat_type = threat.get("type")

        if threat_type == "GPS_ANOMALY":
            print("[SCOUT-X] RESPONSE: REJECT SUSPICIOUS GPS DATA")

        elif threat_type == "ALTITUDE_ANOMALY":
            print("[SCOUT-X] RESPONSE: SAFE FLIGHT RESPONSE")

        elif threat_type == "COMMAND_INJECTION":
            print("[SCOUT-X] RESPONSE: COMMAND REJECTED")

        elif threat_type == "COMMUNICATION_LOSS":
            print("[SCOUT-X] RESPONSE: AUTONOMOUS / SAFE MODE")

        elif threat_type == "CRITICAL_HIJACK":
            print("[SCOUT-X] RESPONSE: UAV LOCKDOWN")
            secure_wipe_simulation()

        else:
            print("[SCOUT-X] RESPONSE: LOG ONLY")
