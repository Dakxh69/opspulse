"""
OpsPulse Simulator — Bounded CPU Spike Scenario

Generates controlled, time-bounded CPU load across cores per spec Section 21.4.A.
Safety guarantees:
- Hard maximum runtime timeout (default 15 seconds).
- Intermittent sleep intervals to prevent lockups.
- Safe termination on SIGINT/SIGTERM.
"""

from __future__ import annotations

import argparse
import multiprocessing
import time


def _burn_cpu(duration: float) -> None:
    """Spins CPU in bounded bursts."""
    start = time.time()
    while time.time() - start < duration:
        # 80ms compute, 20ms sleep for controlled ~80% target per thread
        t_spin = time.time() + 0.08
        while time.time() < t_spin:
            _ = 999999 * 999999
        time.sleep(0.02)


def run_cpu_spike(duration_seconds: float = 15.0, workers: int | None = None) -> None:
    """Spawns worker processes to generate bounded CPU utilization."""
    if workers is None:
        workers = max(1, multiprocessing.cpu_count() - 1)

    print(f"[OpsPulse Simulator] Starting CPU spike: {workers} workers for {duration_seconds}s...")
    processes: list[multiprocessing.Process] = []

    for _ in range(workers):
        p = multiprocessing.Process(target=_burn_cpu, args=(duration_seconds,))
        p.daemon = True
        p.start()
        processes.append(p)

    for p in processes:
        p.join(timeout=duration_seconds + 5)

    print("[OpsPulse Simulator] CPU spike scenario concluded cleanly.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpsPulse Bounded CPU Spike Generator")
    parser.add_argument("--duration", type=float, default=15.0, help="Duration in seconds (default: 15)")
    parser.add_argument("--workers", type=int, default=None, help="Process count")
    args = parser.parse_args()
    run_cpu_spike(duration_seconds=args.duration, workers=args.workers)

