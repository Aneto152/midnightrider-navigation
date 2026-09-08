"""
Unit tests for CLI argument validation.
"""
import pytest
from pathlib import Path
from tools.influx_powerbi_export import cli

def test_parse_args_valid():
    """Valid arguments parse correctly."""
    args = cli.parse_args([
        "--start", "2026-08-31T19:43:24Z",
        "--stop", "2026-09-07T19:43:24Z"
    ])
    assert args.start == "2026-08-31T19:43:24Z"
    assert args.stop == "2026-09-07T19:43:24Z"
    assert args.dry_run == False

def test_parse_args_dry_run():
    """--dry-run flag sets correctly."""
    args = cli.parse_args([
        "--start", "2026-08-31T19:43:24Z",
        "--stop", "2026-09-07T19:43:24Z",
        "--dry-run"
    ])
    assert args.dry_run == True

def test_output_dir_validation_on_usb():
    """Output dir on USB is accepted."""
    usb_mount = "/media/aneto/Lexar"
    output_dir = "/media/aneto/Lexar/MidnightRider_Influx_Export/test_run"
    
    # Should not raise
    result = cli.validate_output_dir(output_dir, usb_mount)
    assert str(result).startswith(usb_mount)

def test_output_dir_validation_rejects_tmp():
    """/tmp output dir is rejected."""
    with pytest.raises(ValueError):
        cli.validate_output_dir("/tmp/export", "/media/aneto/Lexar")

def test_output_dir_validation_rejects_home():
    """/home/aneto output dir is rejected."""
    with pytest.raises(ValueError):
        cli.validate_output_dir("/home/aneto/export", "/media/aneto/Lexar")

def test_output_dir_validation_rejects_symlink_escape():
    """Symlink escape attempts are rejected."""
    with pytest.raises(ValueError):
        cli.validate_output_dir("/media/aneto/Lexar/../../../home/aneto", "/media/aneto/Lexar")

def test_output_dir_validation_rejects_outside_usb():
    """Path outside USB mount is rejected."""
    with pytest.raises(ValueError):
        cli.validate_output_dir("/var/tmp/export", "/media/aneto/Lexar")
