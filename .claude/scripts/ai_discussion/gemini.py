#!/usr/bin/env python3
import argparse
import subprocess
import sys
import json
from typing import Optional


def build_gemini_command(args: argparse.Namespace) -> list[str]:
    cmd = ["gemini"]
    if args.prompt:
        cmd.extend(["--prompt", args.prompt])
    if args.output_format:
        cmd.extend(["--output-format", args.output_format])
    if args.model:
        cmd.extend(["--model", args.model])
    if args.debug:
        cmd.append("--debug")
    if args.yolo:
        cmd.append("--yolo")
    if args.approval_mode:
        cmd.extend(["--approval-mode", args.approval_mode])
    if args.include_directories:
        cmd.extend(["--include-directories", args.include_directories])
    return cmd


def run_gemini(
    cmd: list[str], stdin_input: Optional[str] = None, stream: bool = False
) -> tuple[int, str, str]:
    if stream:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if stdin_input else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout_lines = []
        if stdin_input:
            process.stdin.write(stdin_input)
            process.stdin.close()
        for line in process.stdout:
            print(line, end="", flush=True)
            stdout_lines.append(line)
        process.wait()
        stderr = process.stderr.read()
        return process.returncode, "".join(stdout_lines), stderr
    result = subprocess.run(cmd, input=stdin_input, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def parse_json_response(output: str) -> Optional[dict]:
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gemini CLI headless mode wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -p "What is machine learning?"
  %(prog)s -p "Summarize this" --stdin < README.md
  %(prog)s -p "Review code" -o json --model gemini-2.5-flash
  cat file.py | %(prog)s -p "Explain this code"
        """,
    )
    parser.add_argument("-p", "--prompt", type=str, help="The prompt to send to Gemini")
    parser.add_argument(
        "-o",
        "--output-format",
        choices=["text", "json", "stream-json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        help="Gemini model to use (e.g., gemini-2.5-flash, gemini-2.5-pro)",
    )
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "-y", "--yolo", action="store_true", help="Auto-approve all actions"
    )
    parser.add_argument(
        "--approval-mode", choices=["auto_edit", "full"], help="Set approval mode"
    )
    parser.add_argument(
        "--include-directories",
        type=str,
        help="Include additional directories (comma-separated)",
    )
    parser.add_argument(
        "--stdin", action="store_true", help="Read input from stdin and pipe to gemini"
    )
    parser.add_argument(
        "--extract-response",
        action="store_true",
        help="Extract only the response field from JSON output",
    )
    args = parser.parse_args()
    stdin_input = None
    if args.stdin or not sys.stdin.isatty():
        stdin_input = sys.stdin.read()
    if not args.prompt and not stdin_input:
        parser.error("Either --prompt or stdin input is required")
    cmd = build_gemini_command(args)
    stream = args.output_format == "stream-json"
    returncode, stdout, stderr = run_gemini(cmd, stdin_input, stream)
    if returncode != 0:
        print(f"Error: {stderr}", file=sys.stderr)
        return returncode
    if not stream:
        if args.extract_response and args.output_format == "json":
            parsed = parse_json_response(stdout)
            if parsed and "response" in parsed:
                print(parsed["response"])
            else:
                print(stdout)
        else:
            print(stdout)
    return returncode


if __name__ == "__main__":
    sys.exit(main())
