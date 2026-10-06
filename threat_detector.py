class ThreatDetector:
    def __init__(self):
        self.last_altitude = None
        self.last_position = None

    def check_altitude(self, altitude):
        if altitude is None:
            return None

        if self.last_altitude is not None:
            delta = abs(altitude - self.last_altitude)

            # Large instantaneous jump is treated as an anomaly
            if delta > 20:
                return {
                    "type": "ALTITUDE_ANOMALY",
                    "severity": "HIGH",
                    "message": f"Altitude changed by {delta:.2f} m"
                }

        self.last_altitude = altitude
        return None

    def check_gps(self, lat, lon):
        if lat is None or lon is None:
            return None

        if self.last_position is not None:
            old_lat, old_lon = self.last_position
            delta = abs(lat - old_lat) + abs(lon - old_lon)

            if delta > 0.01:
                return {
                    "type": "GPS_ANOMALY",
                    "severity": "HIGH",
                    "message": "Unexpected GPS position change"
                }

        self.last_position = (lat, lon)
        return None
