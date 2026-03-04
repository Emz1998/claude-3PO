import shlex
import subprocess

SCRIPT = "~/avaris-ai/scripts/claude_hooks/lib/launch-claude.py"


def parallel_sessions(prompts: list[str]) -> None:
    """Start a new session with parallel prompts."""
    quoted = " ".join(shlex.quote(p) for p in prompts)
    subprocess.Popen(
        [
            "cmd.exe",
            "/c",
            "start",
            "",
            "wsl.exe",
            "bash",
            "-lic",
            f"python3 {SCRIPT} {quoted}; exec bash",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
