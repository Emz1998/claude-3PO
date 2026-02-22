#!/usr/bin/env python3
import argparse
import subprocess
import sys
import json
from typing import Optional


def build_codex_command(args: argparse.Namespace, prompt: str) -> list[str]:
    cmd = ["codex", "exec"]
    if args.image:
        for img in args.image:
            cmd.extend(["--image", img])
    if args.model:
        cmd.extend(["--model", args.model])
    if args.oss:
        cmd.append("--oss")
    if args.profile:
        cmd.extend(["--profile", args.profile])
    if args.sandbox:
        cmd.extend(["--sandbox", args.sandbox])
    if args.full_auto:
        cmd.append("--full-auto")
    if args.yolo:
        cmd.append("--yolo")
    if args.cd:
        cmd.extend(["--cd", args.cd])
    if args.skip_git_repo_check:
        cmd.append("--skip-git-repo-check")
    if args.output_schema:
        cmd.extend(["--output-schema", args.output_schema])
    if args.color:
        cmd.extend(["--color", args.color])
    if args.json_output:
        cmd.append("--json")
    if args.output_last_message:
        cmd.extend(["--output-last-message", args.output_last_message])
    if args.search:
        cmd.append("--search")
    if args.add_dir:
        for dir_path in args.add_dir:
            cmd.extend(["--add-dir", dir_path])
    if args.config:
        for cfg in args.config:
            cmd.extend(["--config", cfg])
    cmd.append(prompt)
    return cmd


def run_codex(cmd: list[str], stream: bool = False) -> tuple[int, str, str]:
    if stream:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        stdout_lines = []
        for line in process.stdout:
            print(line, end="", flush=True)
            stdout_lines.append(line)
        process.wait()
        stderr = process.stderr.read()
        return process.returncode, "".join(stdout_lines), stderr
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def parse_jsonl_response(output: str) -> list[dict]:
    events = []
    for line in output.strip().split("\n"):
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def extract_final_message(events: list[dict]) -> Optional[str]:
    for event in reversed(events):
        if event.get("type") == "message" and event.get("role") == "assistant":
            return event.get("content", "")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Codex CLI (GPT) headless mode wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -p "What is machine learning?"
  %(prog)s -p "Analyze this code" --model gpt-5-codex
  %(prog)s -p "Review code" --json --full-auto
  %(prog)s -p "Fix bug" --yolo --search
  echo "Explain this" | %(prog)s --stdin
        """,
    )
    parser.add_argument("-p", "--prompt", type=str, help="The prompt to send to Codex")
    parser.add_argument(
        "-i",
        "--image",
        type=str,
        action="append",
        help="Attach image file(s) to the prompt (repeatable)",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        help="Override the configured model (e.g., gpt-5-codex)",
    )
    parser.add_argument(
        "--oss",
        action="store_true",
        help="Use local open source model provider (requires Ollama)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        help="Configuration profile name from ~/.codex/config.toml",
    )
    parser.add_argument(
        "-s",
        "--sandbox",
        choices=["read-only", "workspace-write", "danger-full-access"],
        help="Sandbox policy for model-generated commands",
    )
    parser.add_argument(
        "--full-auto",
        action="store_true",
        help="Low-friction automation (workspace-write sandbox, approvals on failure)",
    )
    parser.add_argument(
        "-y",
        "--yolo",
        action="store_true",
        help="Bypass approval prompts and sandboxing (dangerous)",
    )
    parser.add_argument(
        "-C", "--cd", type=str, help="Set working directory before executing"
    )
    parser.add_argument(
        "--skip-git-repo-check",
        action="store_true",
        help="Allow running outside a Git repository",
    )
    parser.add_argument(
        "--output-schema", type=str, help="JSON Schema file for expected response shape"
    )
    parser.add_argument(
        "--color",
        choices=["always", "never", "auto"],
        help="Control ANSI color in stdout",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output newline-delimited JSON events",
    )
    parser.add_argument(
        "-o",
        "--output-last-message",
        type=str,
        help="Write assistant's final message to file",
    )
    parser.add_argument(
        "--search", action="store_true", help="Enable web search capability"
    )
    parser.add_argument(
        "--add-dir",
        type=str,
        action="append",
        help="Grant additional directories write access (repeatable)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        action="append",
        help="Configuration override key=value (repeatable)",
    )
    parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    parser.add_argument(
        "--stream", action="store_true", help="Stream output in real-time"
    )
    parser.add_argument(
        "--extract-response",
        action="store_true",
        help="Extract only the final assistant message from JSON output",
    )
    args = parser.parse_args()
    prompt = args.prompt
    if args.stdin or (not args.prompt and not sys.stdin.isatty()):
        stdin_content = sys.stdin.read().strip()
        if args.prompt:
            prompt = f"{args.prompt}\n\n{stdin_content}"
        else:
            prompt = stdin_content
    if not prompt:
        parser.error("Either --prompt or stdin input is required")
    cmd = build_codex_command(args, prompt)
    stream = args.stream or args.json_output
    returncode, stdout, stderr = run_codex(cmd, stream and not args.json_output)
    if returncode != 0:
        print(f"Error: {stderr}", file=sys.stderr)
        return returncode
    if not stream:
        if args.extract_response and args.json_output:
            events = parse_jsonl_response(stdout)
            final_msg = extract_final_message(events)
            if final_msg:
                print(final_msg)
            else:
                print(stdout)
        else:
            print(stdout)
    return returncode


if __name__ == "__main__":
    sys.exit(main())
