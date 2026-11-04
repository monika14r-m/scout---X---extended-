# SCOUT-X live simulation add-on

See [`README.md`](README.md) for setup and case commands. This add-on targets the existing Gazebo Sim 8 + ArduPilot SITL workflow and does not require ROS. Case 1 sends ARM/TAKEOFF only after explicit `--confirm-sitl` confirmation. Case 2 monitors GCS-originated MAVLink `HEARTBEAT` messages on a dedicated UDP listener; it requires an initial heartbeat and a separate working SITL link for the selected response. It detects loss of that configured heartbeat stream, not a physical radio outage. GPS spoofing remains a shadow-telemetry anomaly test.
