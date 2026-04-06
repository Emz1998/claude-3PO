import subprocess


def get_pr_number() -> int | None:
    pr_number = subprocess.run(
        ["gh", "pr", "view", "--json", "number", "--jq", ".number"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    return int(pr_number) if pr_number else None


def pr_exists() -> bool:
    return get_pr_number() is not None
