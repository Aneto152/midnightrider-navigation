"""Pytest configuration for Midnight Rider."""
import os, sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
for module_dir in ['', 'ais', 'regatta', 'mcp/servers', 'portal', 'plugins']:
    path = str(REPO_ROOT / module_dir)
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault('MR_ROOT', str(REPO_ROOT))
