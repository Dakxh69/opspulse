"""
OpsPulse Host Monitoring Agent — Disk Metric Collector

Collects mounted filesystem telemetry per spec Section 8.3:
- Mount point (e.g. /, /home, /data)
- Device/filesystem label (e.g. /dev/sda1, /dev/nvme0n1p2)
- Filesystem type (e.g. ext4, xfs, btrfs)
- Total, used, and available/free bytes
- Utilization percentage (0.0 to 100.0)

Exclusions:
- Pseudo-filesystems and virtual mounts (proc, sysfs, devtmpfs, tmpfs, squashfs, overlay).
- Handles permission errors on restricted mounts gracefully.
"""

from __future__ import annotations

import psutil
from pydantic import BaseModel, Field

# Pseudo-filesystems and virtual mounts to exclude from physical disk telemetry
PSEUDO_FSTYPES: frozenset[str] = frozenset(
    {
        "proc",
        "sysfs",
        "devtmpfs",
        "devpts",
        "tmpfs",
        "cgroup",
        "cgroup2",
        "overlay",
        "squashfs",
        "tracefs",
        "securityfs",
        "fusectl",
        "pstore",
        "bpf",
        "autofs",
        "mqueue",
        "hugetlbfs",
        "debugfs",
        "binfmt_misc",
        "configfs",
        "ramfs",
        "efivarfs",
        "nsfs",
    }
)


class DiskItem(BaseModel):
    """Telemetry for a single mounted filesystem."""

    mount_point: str = Field(..., description="Target filesystem mount path")
    device: str = Field(..., description="Physical block device or partition path")
    fstype: str = Field(..., description="Filesystem type (e.g. ext4, xfs)")
    total_bytes: int = Field(..., gt=0, description="Total capacity in bytes")
    used_bytes: int = Field(..., ge=0, description="Used capacity in bytes")
    free_bytes: int = Field(..., ge=0, description="Available unallocated capacity in bytes")
    usage_percent: float = Field(..., ge=0.0, le=100.0, description="Disk utilization percentage")


class DiskCollector:
    """Collects disk usage across mounted physical partitions."""

    def __init__(self, excluded_fstypes: set[str] | None = None) -> None:
        self.excluded_fstypes = (
            frozenset(excluded_fstypes) if excluded_fstypes is not None else PSEUDO_FSTYPES
        )

    def collect(self) -> list[DiskItem]:
        """Inspect all mounted partitions and return usage for non-pseudo filesystems."""
        disks: list[DiskItem] = []
        partitions = psutil.disk_partitions(all=False)

        seen_mounts: set[str] = set()

        for partition in partitions:
            if partition.fstype.lower() in self.excluded_fstypes:
                continue

            # Deduplicate multiple bind-mounts of the same path
            if partition.mountpoint in seen_mounts:
                continue
            seen_mounts.add(partition.mountpoint)

            try:
                usage = psutil.disk_usage(partition.mountpoint)
                # Ignore zero-capacity virtual devices if any slipped through
                if usage.total <= 0:
                    continue

                disks.append(
                    DiskItem(
                        mount_point=partition.mountpoint,
                        device=partition.device,
                        fstype=partition.fstype,
                        total_bytes=int(usage.total),
                        used_bytes=int(usage.used),
                        free_bytes=int(usage.free),
                        usage_percent=float(usage.percent),
                    )
                )
            except (PermissionError, OSError):
                # Restricted or unmounted directory; skip safely
                continue

        return disks
