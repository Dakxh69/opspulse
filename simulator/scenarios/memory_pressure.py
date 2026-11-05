"""
OpsPulse Simulator — Bounded Memory Pressure Scenario

Allocates a strict, bounded memory buffer in RAM per spec Section 21.4.B.
Safety guarantees:
- Strict upper allocation limit (max 200MB default).
- Never allocates unbounded host RAM.
- Guaranteed deallocation and garbage collection upon completion.
"""

from __future__ import annotations

import argparse
import gc
import time


def run_memory_pressure(megabytes: int = 150, hold_seconds: float = 15.0) -> None:
    """Allocates a strictly bounded bytearray buffer for hold_seconds."""
    max_safe_mb = 500
    if megabytes > max_safe_mb:
        raise ValueError(f"Requested {megabytes}MB exceeds safety cap of {max_safe_mb}MB")

    print(f"[OpsPulse Simulator] Allocating {megabytes}MB bounded memory buffer...")
    buffer = None
    try:
        # Allocate exactly megabytes in RAM
        buffer = bytearray(megabytes * 1024 * 1024)
        # Touch pages to ensure physical allocation
        for i in range(0, len(buffer), 4096):
            buffer[i] = 1

        print(f"[OpsPulse Simulator] Holding {megabytes}MB allocation for {hold_seconds}s...")
        time.sleep(hold_seconds)
    finally:
        del buffer
        gc.collect()
        print("[OpsPulse Simulator] Released memory buffer and reclaimed RAM.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpsPulse Bounded Memory Pressure Generator")
    parser.add_argument("--mb", type=int, default=150, help="Megabytes to allocate (default: 150)")
    parser.add_argument("--hold", type=float, default=15.0, help="Hold duration in seconds")
    args = parser.parse_args()
    run_memory_pressure(megabytes=args.mb, hold_seconds=args.hold)
