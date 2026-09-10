"""
Focused tests for USB discovery via findmnt JSON parsing.

Tests cover:
- Top-level "filesystems" array traversal
- Nested "children" array traversal
- Label matching (exact match required)
- Filesystem type matching (exfat only)
- Error handling (malformed JSON, non-zero exit)
- No match returns None
- Matching target returns correct path
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Import the function being tested
from tools.influx_powerbi_export.main import discover_usb


class TestUSBDiscoveryFilesystemsArray:
    """Test top-level 'filesystems' array traversal."""

    def test_top_level_filesystems_array_with_matching_mount(self):
        """Should find Lexar in top-level filesystems array."""
        mock_output = json.dumps({
            "filesystems": [
                {
                    "fstype": "ext4",
                    "label": None,
                    "target": "/",
                    "children": []
                },
                {
                    "fstype": "exfat",
                    "label": "Lexar",
                    "target": "/media/aneto/Lexar"
                }
            ]
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            result = discover_usb(label="Lexar")
            assert result == Path("/media/aneto/Lexar")

    def test_top_level_filesystems_no_match_returns_none(self):
        """Should return None when no matching Lexar mount in filesystems."""
        mock_output = json.dumps({
            "filesystems": [
                {
                    "fstype": "ext4",
                    "label": None,
                    "target": "/"
                },
                {
                    "fstype": "vfat",
                    "label": "BOOT",
                    "target": "/boot"
                }
            ]
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            result = discover_usb(label="Lexar")
            assert result is None


class TestUSBDiscoveryChildrenArray:
    """Test nested 'children' array traversal."""

    def test_nested_children_array_with_matching_mount(self):
        """Should find Lexar nested under children array."""
        mock_output = json.dumps({
            "filesystems": [
                {
                    "fstype": "tmpfs",
                    "target": "/dev",
                    "children": [
                        {
                            "fstype": "devtmpfs",
                            "target": "/dev/shm"
                        },
                        {
                            "fstype": "exfat",
                            "label": "Lexar",
                            "target": "/media/aneto/Lexar"
                        }
                    ]
                }
            ]
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            result = discover_usb(label="Lexar")
            assert result == Path("/media/aneto/Lexar")

    def test_deeply_nested_children(self):
        """Should find Lexar in deeply nested children."""
        mock_output = json.dumps({
            "filesystems": [
                {
                    "fstype": "tmpfs",
                    "target": "/sys",
                    "children": [
                        {
                            "fstype": "sysfs",
                            "target": "/sys/fs",
                            "children": [
                                {
                                    "fstype": "exfat",
                                    "label": "Lexar",
                                    "target": "/media/aneto/Lexar"
                                }
                            ]
                        }
                    ]
                }
            ]
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            result = discover_usb(label="Lexar")
            assert result == Path("/media/aneto/Lexar")


class TestUSBDiscoveryLabelMatching:
    """Test label matching strictness."""

    def test_exact_label_match_required(self):
        """Should require exact label match."""
        mock_output = json.dumps({
            "filesystems": [
                {
                    "fstype": "exfat",
                    "label": "Lexar_Backup",
                    "target": "/media/aneto/Lexar_Backup"
                }
            ]
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            result = discover_usb(label="Lexar")
            assert result is None

    def test_case_sensitive_label_match(self):
        """Should require case-sensitive label match."""
        mock_output = json.dumps({
            "filesystems": [
                {
                    "fstype": "exfat",
                    "label": "lexar",
                    "target": "/media/aneto/lexar"
                }
            ]
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            result = discover_usb(label="Lexar")
            assert result is None


class TestUSBDiscoveryFilesystemType:
    """Test filesystem type matching."""

    def test_only_exfat_matches(self):
        """Should only match exfat filesystem type."""
        mock_output = json.dumps({
            "filesystems": [
                {
                    "fstype": "vfat",
                    "label": "Lexar",
                    "target": "/media/aneto/Lexar"
                }
            ]
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            result = discover_usb(label="Lexar")
            assert result is None

    def test_ntfs_not_matched(self):
        """Should not match NTFS filesystem."""
        mock_output = json.dumps({
            "filesystems": [
                {
                    "fstype": "ntfs",
                    "label": "Lexar",
                    "target": "/media/aneto/Lexar"
                }
            ]
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            result = discover_usb(label="Lexar")
            assert result is None


class TestUSBDiscoveryErrorHandling:
    """Test error handling."""

    def test_non_zero_exit_status_returns_none(self):
        """Should return None on non-zero findmnt exit."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = discover_usb(label="Lexar")
            assert result is None

    def test_malformed_json_returns_none(self):
        """Should return None on malformed JSON output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="invalid json {")
            result = discover_usb(label="Lexar")
            assert result is None

    def test_exception_during_parsing_returns_none(self):
        """Should return None on exception during parsing."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            mock_run.side_effect = Exception("Test exception")
            result = discover_usb(label="Lexar")
            assert result is None

    def test_findmnt_timeout_returns_none(self):
        """Should return None if findmnt times out."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = TimeoutError("findmnt timed out")
            result = discover_usb(label="Lexar")
            assert result is None


class TestUSBDiscoveryRealWorldJSON:
    """Test with realistic findmnt JSON structures."""

    def test_real_rpi_mount_structure(self):
        """Should find Lexar in realistic RPi mount structure."""
        # Simulates actual findmnt -J output structure
        mock_output = json.dumps({
            "filesystems": [
                {
                    "fstype": "ext4",
                    "target": "/",
                    "children": [
                        {
                            "fstype": "tmpfs",
                            "target": "/dev"
                        },
                        {
                            "fstype": "devtmpfs",
                            "target": "/dev/shm"
                        }
                    ]
                },
                {
                    "fstype": "vfat",
                    "label": None,
                    "target": "/boot/firmware"
                },
                {
                    "fstype": "exfat",
                    "label": "Lexar",
                    "target": "/media/aneto/Lexar"
                }
            ]
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            result = discover_usb(label="Lexar")
            assert result == Path("/media/aneto/Lexar")


class TestUSBDiscoveryDefaultLabel:
    """Test default label parameter."""

    def test_default_label_is_lexar(self):
        """Should use 'Lexar' as default label."""
        mock_output = json.dumps({
            "filesystems": [
                {
                    "fstype": "exfat",
                    "label": "Lexar",
                    "target": "/media/aneto/Lexar"
                }
            ]
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            # Call without specifying label
            result = discover_usb()
            assert result == Path("/media/aneto/Lexar")

    def test_custom_label_parameter(self):
        """Should accept custom label parameter."""
        mock_output = json.dumps({
            "filesystems": [
                {
                    "fstype": "exfat",
                    "label": "Custom",
                    "target": "/media/aneto/Custom"
                }
            ]
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
            result = discover_usb(label="Custom")
            assert result == Path("/media/aneto/Custom")
