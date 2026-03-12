import shlex
import subprocess

SCRIPT = "~/avaris-ai/.claude/hooks/workflow/lib/launch-claude.py"


def parallel_sessions(prompts: list[str]) -> None:
    """Start a new session with parallel prompts."""
    quoted = " ".join(shlex.quote(p) for p in prompts)
    subprocess.Popen(
        [
            "wt.exe",
            "-w", "0",
            "nt",
            "wsl.exe",
            "bash",
            "-lic",
            f"python3 {SCRIPT} {quoted}",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
