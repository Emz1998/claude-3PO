from pathlib import Path

LOG_FILE = Path("DEBUG.log")


def log(message: str) -> None:
    if not LOG_FILE.parent.exists():
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not LOG_FILE.exists():
        LOG_FILE.touch()

    LOG_FILE.write_text(message)
