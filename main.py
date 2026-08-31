"""
main.py

SCOUT-X end-to-end run:

  simulation -> attacks -> telemetry -> detection -> response -> results

Runs a fixed-duration UAV session, injects a scheduled sequence of
attacks, feeds every sample through the trust-score detector and the
response engine, and writes evaluation metrics + a run log to results/.

Usage:
    python3 main.py [--duration SECONDS] [--hz HZ] [--seed SEED]
"""

import argparse
import json
import os

from simulation.uav_simulator import UAVSimulator
from attacks.attack_injector import AttackInjector, default_schedule
from telemetry.telemetry_stream import TelemetryStream
from detection.trust_score import TrustScoreEngine
from response.response_engine import ResponseEngine


def run(duration: float, hz: float, seed: int, results_dir: str):
    sim = UAVSimulator(seed=seed, hz=hz)
    schedule = default_schedule(duration)
    injector = AttackInjector(schedule)
    stream = TelemetryStream(maxlen=int(duration * hz) + 10)
    detector = TrustScoreEngine(window=15, alert_threshold=0.55)
    responder = ResponseEngine(escalate_after=3)

    n_steps = int(duration * hz)
    detections = []

    # For latency measurement: time each attack window started, and the
    # first timestamp the detector flagged an anomaly within that window.
    attack_windows = {a.attack_type: {"start": a.start_t, "end": a.end_t, "first_detected_at": None}
                       for a in schedule}

    tp = fp = tn = fn = 0

    for _ in range(n_steps):
        clean_sample = sim.step()
        sample = injector.apply(clean_sample)
        stream.append(sample)

        result = detector.evaluate(sample)
        responder.handle(result)
        result["ground_truth_attack"] = sample.ground_truth_attack
        detections.append(result)

        is_attack = sample.ground_truth_attack is not None
        flagged = result["is_anomaly"]

        if is_attack and flagged:
            tp += 1
            aw = attack_windows[sample.ground_truth_attack]
            if aw["first_detected_at"] is None:
                aw["first_detected_at"] = sample.timestamp
        elif is_attack and not flagged:
            fn += 1
        elif (not is_attack) and flagged:
            fp += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    false_positive_rate = fp / (fp + tn) if (fp + tn) else 0.0

    latencies = []
    for attack_type, aw in attack_windows.items():
        if aw["first_detected_at"] is not None:
            latencies.append(round(aw["first_detected_at"] - aw["start"], 3))
    avg_latency = sum(latencies) / len(latencies) if latencies else None

    metrics = {
        "run_config": {"duration_s": duration, "hz": hz, "seed": seed, "n_samples": n_steps},
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "precision": round(precision, 4),
        "recall_detection_rate": round(recall, 4),
        "f1_score": round(f1, 4),
        "false_positive_rate": round(false_positive_rate, 4),
        "avg_detection_latency_seconds": round(avg_latency, 3) if avg_latency is not None else None,
        "per_attack_detection": {
            atype: {
                "start_s": aw["start"],
                "end_s": aw["end"],
                "first_detected_at_s": aw["first_detected_at"],
                "detected": aw["first_detected_at"] is not None,
                "latency_s": round(aw["first_detected_at"] - aw["start"], 3) if aw["first_detected_at"] is not None else None,
            }
            for atype, aw in attack_windows.items()
        },
        "response_actions": responder.log,
    }

    os.makedirs(results_dir, exist_ok=True)
    with open(os.path.join(results_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    with open(os.path.join(results_dir, "run_log.json"), "w") as f:
        json.dump(detections, f, indent=2)

    stream.dump_json(os.path.join(results_dir, "telemetry_dump.json"))

    return metrics


def print_summary(metrics: dict):
    print("=" * 60)
    print("SCOUT-X run summary")
    print("=" * 60)
    print(f"Samples processed:      {metrics['run_config']['n_samples']}")
    print(f"Detection rate (recall): {metrics['recall_detection_rate'] * 100:.1f}%")
    print(f"Precision:               {metrics['precision'] * 100:.1f}%")
    print(f"F1 score:                {metrics['f1_score']:.3f}")
    print(f"False positive rate:     {metrics['false_positive_rate'] * 100:.2f}%")
    if metrics["avg_detection_latency_seconds"] is not None:
        print(f"Avg detection latency:   {metrics['avg_detection_latency_seconds']:.2f}s")
    print()
    print("Per-attack breakdown:")
    for atype, info in metrics["per_attack_detection"].items():
        status = "DETECTED" if info["detected"] else "MISSED"
        lat = f", latency {info['latency_s']}s" if info["latency_s"] is not None else ""
        print(f"  - {atype:20s} {status}{lat}")
    print()
    print(f"Response actions logged: {len(metrics['response_actions'])}")
    print("Full metrics written to results/metrics.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a SCOUT-X simulation session.")
    parser.add_argument("--duration", type=float, default=60.0, help="Session duration in seconds")
    parser.add_argument("--hz", type=float, default=10.0, help="Telemetry sample rate in Hz")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--results-dir", type=str, default="results", help="Output directory")
    args = parser.parse_args()

    metrics = run(args.duration, args.hz, args.seed, args.results_dir)
    print_summary(metrics)
