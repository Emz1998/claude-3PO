"""Shared test fixtures for claude_hooks tests."""

import sys
from pathlib import Path

# Ensure project root is on sys.path so `scripts.claude_hooks` is importable
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
