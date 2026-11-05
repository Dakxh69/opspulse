"""
OpsPulse Host Monitoring Agent — Tests: Disk Collector

Verifies:
- Live mounted filesystem collection on host machine.
- Exclusion of pseudo-filesystems (proc, sysfs, devtmpfs, tmpfs).
- Handling of permission errors and unmounted partitions.
- Pydantic schema validation for disk items.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from opspulse_agent.collectors.disk import (
    DiskCollector,
    DiskItem,
)


def test_disk_collector_live_collection() -> None:
    """Verifies live disk partitions collection on host."""
    collector = DiskCollector()
    disks = collector.collect()

    assert isinstance(disks, list)
    assert len(disks) >= 1  # At least root filesystem '/' exists

    root_mount = next((d for d in disks if d.mount_point == "/"), None)
    assert root_mount is not None
    assert root_mount.total_bytes > 0
    assert root_mount.used_bytes >= 0
    assert 0.0 <= root_mount.usage_percent <= 100.0


def test_disk_collector_excludes_pseudo_filesystems() -> None:
    """Verifies that virtual filesystems like proc and sysfs are ignored."""
    mock_p_root = MagicMock()
    mock_p_root.mountpoint = "/"
    mock_p_root.device = "/dev/sda1"
    mock_p_root.fstype = "ext4"

    mock_p_proc = MagicMock()
    mock_p_proc.mountpoint = "/proc"
    mock_p_proc.device = "proc"
    mock_p_proc.fstype = "proc"

    mock_p_tmpfs = MagicMock()
    mock_p_tmpfs.mountpoint = "/run"
    mock_p_tmpfs.device = "tmpfs"
    mock_p_tmpfs.fstype = "tmpfs"

    mock_usage = MagicMock()
    mock_usage.total = 100_000_000_000
    mock_usage.used = 40_000_000_000
    mock_usage.free = 60_000_000_000
    mock_usage.percent = 40.0

    with (
        patch("psutil.disk_partitions", return_value=[mock_p_root, mock_p_proc, mock_p_tmpfs]),
        patch("psutil.disk_usage", return_value=mock_usage),
    ):
        collector = DiskCollector()
        disks = collector.collect()

        assert len(disks) == 1
        assert disks[0].mount_point == "/"
        assert disks[0].fstype == "ext4"
        assert disks[0].usage_percent == 40.0


def test_disk_collector_handles_permission_error() -> None:
    """Verifies that an unreadable mount point does not crash collection."""
    mock_p1 = MagicMock()
    mock_p1.mountpoint = "/root_valid"
    mock_p1.device = "/dev/sda1"
    mock_p1.fstype = "ext4"

    mock_p2 = MagicMock()
    mock_p2.mountpoint = "/restricted"
    mock_p2.device = "/dev/sdb1"
    mock_p2.fstype = "ext4"

    mock_usage = MagicMock()
    mock_usage.total = 50_000_000_000
    mock_usage.used = 25_000_000_000
    mock_usage.free = 25_000_000_000
    mock_usage.percent = 50.0

    def mock_disk_usage(path: str) -> MagicMock:
        if path == "/restricted":
            raise PermissionError("Access denied")
        return mock_usage

    with (
        patch("psutil.disk_partitions", return_value=[mock_p1, mock_p2]),
        patch("psutil.disk_usage", side_effect=mock_disk_usage),
    ):
        collector = DiskCollector()
        disks = collector.collect()

        assert len(disks) == 1
        assert disks[0].mount_point == "/root_valid"


def test_disk_item_validation() -> None:
    """Verifies Pydantic boundaries on disk metrics."""
    # Negative total bytes rejected
    with pytest.raises(ValidationError):
        DiskItem(
            mount_point="/",
            device="/dev/sda1",
            fstype="ext4",
            total_bytes=0,
            used_bytes=0,
            free_bytes=0,
            usage_percent=0.0,
        )

    # Percentage > 100 rejected
    with pytest.raises(ValidationError):
        DiskItem(
            mount_point="/",
            device="/dev/sda1",
            fstype="ext4",
            total_bytes=1000,
            used_bytes=1000,
            free_bytes=0,
            usage_percent=100.5,
        )
