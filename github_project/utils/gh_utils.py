"""Shared utilities for GitHub CLI wrappers."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


def run(cmd: list[str], *, check: bool = True) -> str:
    """Run a command and return stdout."""
    p = subprocess.run(cmd, text=True, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError(
            f"Command failed ({p.returncode}): {' '.join(cmd)}\n\nSTDERR:\n{p.stderr}"
        )
    return p.stdout.strip()


def gh_json(cmd: list[str]) -> Any:
    """Run a command and parse JSON output."""
    out = run(cmd)
    if not out:
        return None
    return json.loads(out)


def load_config() -> dict[str, Any]:
    """Load config.yaml from the github_project directory."""
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)
