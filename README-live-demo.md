# SCOUT-X live simulation add-on

See [`README.md`](README.md) for setup and case commands.

This add-on is designed for the current Gazebo Sim 8 + ArduPilot SITL workflow. It does not require ROS. Case 1 commands SITL to arm and take off only when `--confirm-sitl` is supplied. Case 2 simulates application-layer GCS heartbeat loss and requests the selected safe mode. GPS spoofing is a shadow-telemetry anomaly test, not an EKF-input or RF spoof. These limits are explicit so the demonstration is technically honest.
