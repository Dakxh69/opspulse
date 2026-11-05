"""
OpsPulse Simulator — Bounded Disk Pressure Scenario

Creates a temporary bounded file in an isolated directory per spec Section 21.4.C.
Safety guarantees:
- Dedicated subfolder (`/tmp/opspulse_disk_sim`).
- Hard maximum file size cap (default 50MB).
- Guaranteed cleanup in a finally block. Never fills the root filesystem.
"""

from __future__ import annotations

import argparse
import os
import shutil
import time


def run_disk_pressure(megabytes: int = 50, hold_seconds: float = 15.0) -> None:
    """Creates a temporary file of megabytes size and holds it before cleaning up."""
    max_safe_mb = 200
    if megabytes > max_safe_mb:
        raise ValueError(f"Requested {megabytes}MB exceeds safety cap of {max_safe_mb}MB")

    sim_dir = "/tmp/opspulse_disk_sim"
    os.makedirs(sim_dir, exist_ok=True)
    temp_file = os.path.join(sim_dir, "fill.dat")

    print(f"[OpsPulse Simulator] Writing {megabytes}MB bounded test file to {temp_file}...")
    try:
        with open(temp_file, "wb") as f:
            chunk = b"\0" * (1024 * 1024)  # 1MB
            for _ in range(megabytes):
                f.write(chunk)
            f.flush()
            os.fsync(f.fileno())

        print(f"[OpsPulse Simulator] Holding disk pressure for {hold_seconds}s...")
        time.sleep(hold_seconds)
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists(sim_dir):
            shutil.rmtree(sim_dir, ignore_errors=True)
        print("[OpsPulse Simulator] Cleaned up test files and restored disk space.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpsPulse Bounded Disk Pressure Generator")
    parser.add_argument("--mb", type=int, default=50, help="Megabytes to write (default: 50)")
    parser.add_argument("--hold", type=float, default=15.0, help="Hold duration in seconds")
    args = parser.parse_args()
    run_disk_pressure(megabytes=args.mb, hold_seconds=args.hold)

