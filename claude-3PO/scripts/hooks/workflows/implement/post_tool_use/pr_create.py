import subprocess
from config.config import Config  # type: ignore
from utils.hook import Hook  # type: ignore
from typing import Any


def create_pr(title: str, body: str) -> None:
    subprocess.run(["gh", "pr", "create", "--title", title, "--body", body], check=True)


def get_file_path(hook_input: dict[str, Any]) -> str:
    return hook_input.get("tool_input", {}).get("file_path", "")


def is_report_file_path(file_path: str, config: Config) -> bool:
    report_file_path = config.get_file_path("report")
    return file_path == report_file_path


def get_content(hook_input: dict[str, Any]) -> str:
    return hook_input.get("tool_input", {}).get("content", "")


def parse_report(content: str) -> tuple[str, str]:
    title, body = content.split("\n", 1)
    return title.strip(), body.strip()


def main() -> None:
    hook_input = Hook.read_stdin()
    config = Config()
    file_path = get_file_path(hook_input)
    content = get_content(hook_input)

    if not is_report_file_path(file_path, config):
        Hook.system_message("Not a report file. Skipping")
        return

    if not content.strip():
        Hook.system_message("Report is empty. Skipping")
        return

    title, body = parse_report(content)
    create_pr(title, body)


if __name__ == "__main__":
    main()
