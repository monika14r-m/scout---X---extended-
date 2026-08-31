# SCOUT-X
**Secure Commands and Operations for UAV Telemetry — eXtended**

Secure and resilient UAV operations under simulated control-channel manipulation, navigation interference, and hijacking attempts — built around a multi-sensor trust-score anti-hijacking framework.

## Architecture

```
SCOUT-X/
├── simulation/     # Standalone UAV telemetry generator (GPS, IMU, barometer, commands)
├── attacks/        # Scheduled attack injection: GPS spoofing, IMU manipulation,
│                   # control-channel hijack, barometer interference
├── telemetry/      # Shared TelemetrySample data structure + rolling stream buffer
├── detection/      # Trust-score engine: cross-sensor consistency checks -> per-component trust
├── response/       # Isolation, escalation, RTL fallback, simulated secure wipe
└── results/        # Generated per-run: metrics.json, run_log.json, telemetry_dump.json
```

Data flows one direction only: `simulation -> attacks -> telemetry -> detection -> response -> results`.
Every stage only depends on `TelemetrySample`, so `simulation/uav_simulator.py` can be swapped
for a real ROS2/ArduPilot MAVLink bridge later without touching detection or response code.

## How detection works

`detection/trust_score.py` runs five independent checks per telemetry sample:

| Check | Catches |
|---|---|
| GPS kinematics | GPS speed exceeding platform's declared max velocity |
| GPS/IMU consistency | GPS position jump with no matching IMU acceleration (spoofing signature) |
| IMU bounds | Physically implausible acceleration/gyro spikes |
| Barometer/GPS consistency | Barometer altitude diverging from GPS altitude |
| Command integrity | Commanded waypoint unreachable within max velocity and elapsed time (injected commands) |

Each check outputs a trust score in `[0, 1]`. Per-component trust is the **minimum** across its
checks (a single failed check is enough to distrust that sensor — checks aren't averaged away).
Overall system trust is the minimum across all components. Below `alert_threshold` (default 0.55),
the sample is flagged and handed to the response engine with which component(s) are untrusted.

The detector never reads `ground_truth_attack` — that field exists only so `main.py` can
compute evaluation metrics afterward.

## How response works

`response/response_engine.py` implements graduated response, not just an alarm:

1. **ISOLATE** — an untrusted component is dropped from the fusion solution (e.g. stop
   trusting GPS, fall back to IMU dead-reckoning + barometer).
2. **ESCALATE** — triggered by either multiple simultaneously-untrusted components, or
   one component staying untrusted for `escalate_after` consecutive detections (default 3).
3. **EMERGENCY** — simulated RTL (return-to-launch) fallback + simulated secure wipe of
   mission-sensitive telemetry/config.

`_execute_rtl` and `_execute_secure_wipe` are stubbed to log the action — wire them to real
ArduPilot MAVLink commands and real storage APIs when integrating with hardware.

## Running it

No external dependencies — pure Python 3 standard library.

```bash
python3 main.py --duration 60 --hz 10 --seed 42
```

| Flag | Default | Meaning |
|---|---|---|
| `--duration` | 60 | Session length in simulated seconds |
| `--hz` | 10 | Telemetry sample rate |
| `--seed` | 42 | Random seed (reproducibility) |
| `--results-dir` | `results` | Output directory |

## Output

Each run writes to `results/`:

- **`metrics.json`** — precision, recall (detection rate), F1, false positive rate, per-attack
  detection status and latency, and the full response action log.
- **`run_log.json`** — per-sample detection output (trust scores, flags) for the whole session.
- **`telemetry_dump.json`** — the raw telemetry stream, ground-truth labels stripped.

A 60s / 10Hz run against 4 scheduled attack types currently achieves (`results/metrics.json`,
seed 42): **95% precision, 66% recall, 0.82% false positive rate, all 4 attack types detected**.
Rerun after tuning `alert_threshold` or the check weightings in `trust_score.py` — recall vs.
false-positive-rate is the main tradeoff to report on.

## Next steps

- Replace `simulation/uav_simulator.py` with a real ROS2/ArduPilot telemetry bridge.
- Add a rolling-window statistical anomaly check (z-score against recent history) alongside
  the current rule-based checks, for attacks that stay within individual sensor bounds but
  are statistically inconsistent with recent flight behavior.
- Sweep `alert_threshold` and `escalate_after` and report the precision/recall curve — this
  is the kind of quantified result that turns this from an ongoing project into a finished one.
