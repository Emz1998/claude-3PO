import subprocess


def parallel_sessions(prompts: list[str]) -> None:
    """Start a new session with parallel prompts."""
    subprocess.Popen(
        [
            "cmd.exe",
            "/c",
            "start",
            "",
            "wsl.exe",
            "bash",
            "-lic",
            f"python3 ~/avaris-ai/.claude/scripts/launch-claudes.py{prompts}; exec bash",
        ]
    )
