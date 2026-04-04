#!/usr/bin/env python3

import shutil
import sys
from pathlib import Path

SANDBOX_ARTIFACTS = [
    ".bash_profile",
    ".bashrc",
    ".idea",
    ".profile",
    ".ripgreprc",
    ".zprofile",
    ".zshrc",
]


def main() -> None:
    project_root = Path.cwd()
    removed = []
    skipped = []

    for name in SANDBOX_ARTIFACTS:
        path = project_root / name
        if not path.exists():
            skipped.append(name)
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(name)

    if removed:
        print(f"Removed: {', '.join(removed)}")
    if skipped:
        print(f"Not found (skipped): {', '.join(skipped)}")


if __name__ == "__main__":
    main()
