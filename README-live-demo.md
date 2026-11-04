# SCOUT-X live simulation add-on

See [`live_demo/README.md`](live_demo/README.md) for setup and case commands.

This add-on targets the Gazebo Sim 8 + ArduPilot SITL workflow and does not require ROS. Case 1 sends ARM/TAKEOFF only after explicit `--confirm-sitl` confirmation. Case 2 monitors GCS-originated MAVLink `HEARTBEAT` messages on a dedicated UDP listener and detects when that stream goes silent; it requires an initial heartbeat and a separate working SITL link for the selected response. This is not a physical radio outage. GPS spoofing remains a shadow-telemetry anomaly test, not an EKF-input or RF spoof.
