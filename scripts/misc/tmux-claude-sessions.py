#!/usr/bin/env python3
"""
Tmux Multi-Claude Session Spawner

Spawns multiple tmux terminals for running parallel Claude Code sessions.
"""

import subprocess
import argparse
import sys
import shutil
import time

SESSION_NAME = "claude-multi"
LAYOUTS = [
    "tiled",
    "even-horizontal",
    "even-vertical",
    "main-horizontal",
    "main-vertical",
]


def check_dependencies() -> bool:
    """Check if tmux is installed."""
    if not shutil.which("tmux"):
        print("Error: tmux is not installed. Install it with: sudo apt install tmux")
        return False
    return True


def session_exists(session_name: str) -> bool:
    """Check if a tmux session already exists."""
    result = subprocess.run(
        ["tmux", "has-session", "-t", session_name], capture_output=True
    )
    return result.returncode == 0


def kill_session(session_name: str) -> None:
    """Kill an existing tmux session."""
    subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True)
    print(f"Killed existing session: {session_name}")


def create_session(
    num_panes: int,
    session_name: str,
    layout: str,
    working_dir: str,
    command: str,
    no_run: bool = False,
    use_windows: bool = False,
    prefix: str = "",
) -> None:
    """Create a tmux session with multiple panes or windows running Claude."""

    # Create new session with first pane/window
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", session_name, "-c", working_dir]  # detached
    )

    # Enable mouse support for clicking between panes/windows
    subprocess.run(["tmux", "set-option", "-t", session_name, "mouse", "on"])

    # Enable status bar with clickable window tabs
    subprocess.run(["tmux", "set-option", "-t", session_name, "status", "on"])
    subprocess.run(["tmux", "set-option", "-t", session_name, "status-position", "top"])

    # Style the status bar for better visibility
    subprocess.run(
        ["tmux", "set-option", "-t", session_name, "status-style", "bg=blue,fg=white"]
    )
    subprocess.run(
        [
            "tmux",
            "set-option",
            "-t",
            session_name,
            "window-status-current-style",
            "bg=white,fg=blue,bold",
        ]
    )

    # Set custom prefix key if specified
    if prefix:
        subprocess.run(["tmux", "set-option", "-t", session_name, "prefix", prefix])
        subprocess.run(["tmux", "set-option", "-t", session_name, "prefix2", "None"])

    # Bind Shift+arrow keys for window switching (no prefix needed)
    subprocess.run(["tmux", "bind-key", "-n", "S-Left", "previous-window"])
    subprocess.run(["tmux", "bind-key", "-n", "S-Right", "next-window"])

    # Small delay to ensure session is ready
    time.sleep(0.2)

    if use_windows:
        # Rename first window
        subprocess.run(["tmux", "rename-window", "-t", f"{session_name}:0", "Claude-1"])

        # Create separate windows
        for i in range(1, num_panes):
            subprocess.run(
                [
                    "tmux",
                    "new-window",
                    "-t",
                    session_name,
                    "-n",
                    f"Claude-{i + 1}",
                    "-c",
                    working_dir,
                ]
            )
            time.sleep(0.1)

        # Select first window
        subprocess.run(
            ["tmux", "select-window", "-t", f"{session_name}:0"],
            capture_output=True,
            text=True,
        )

        # Also select the pane within the window to ensure focus
        subprocess.run(
            ["tmux", "select-pane", "-t", f"{session_name}:0.0"],
            capture_output=True,
            text=True,
        )

        # Send commands to all windows if not no_run
        if not no_run:
            time.sleep(0.3)
            for i in range(num_panes):
                subprocess.run(
                    ["tmux", "send-keys", "-t", f"{session_name}:{i}", command, "Enter"]
                )
                time.sleep(0.1)

        print(f"Created session '{session_name}' with {num_panes} windows")
        print("Switch windows: Shift+Left/Right arrows (or click tabs)")
    else:
        # Create panes within single window
        for i in range(1, num_panes):
            subprocess.run(
                ["tmux", "split-window", "-t", session_name, "-c", working_dir]
            )

            subprocess.run(["tmux", "select-layout", "-t", session_name, layout])

            time.sleep(0.1)

        # Apply final layout
        subprocess.run(["tmux", "select-layout", "-t", session_name, layout])

        # Select first pane
        subprocess.run(["tmux", "select-pane", "-t", f"{session_name}:0.0"])

        # Send commands to all panes if not no_run
        if not no_run:
            time.sleep(0.3)
            for i in range(num_panes):
                subprocess.run(
                    [
                        "tmux",
                        "send-keys",
                        "-t",
                        f"{session_name}:0.{i}",
                        command,
                        "Enter",
                    ]
                )
                time.sleep(0.1)

        print(f"Created session '{session_name}' with {num_panes} panes")
        print(f"Layout: {layout}")

    print(f"Working directory: {working_dir}")
    if no_run:
        print("Command: (none - empty shells)")
    else:
        print(f"Command: {command}")


def attach_session(session_name: str) -> None:
    """Attach to the tmux session."""
    subprocess.run(["tmux", "attach-session", "-t", session_name])


def list_sessions() -> None:
    """List all tmux sessions."""
    result = subprocess.run(["tmux", "list-sessions"], capture_output=True, text=True)
    if result.returncode == 0:
        print("Active tmux sessions:")
        print(result.stdout)
    else:
        print("No active tmux sessions")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Spawn multiple tmux terminals for Claude Code sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -n 3                    # Spawn 3 Claude sessions
  %(prog)s -n 4 -l tiled           # Spawn 4 sessions with tiled layout
  %(prog)s -n 2 --attach           # Spawn 2 sessions and attach immediately
  %(prog)s --kill                  # Kill existing claude-multi session
  %(prog)s --list                  # List all tmux sessions
  %(prog)s -n 3 -c "claude --help" # Spawn 3 sessions running a custom command
        """,
    )

    parser.add_argument(
        "-n",
        "--num-panes",
        type=int,
        default=2,
        help="Number of panes/sessions to spawn (default: 2)",
    )

    parser.add_argument(
        "-s",
        "--session-name",
        type=str,
        default=SESSION_NAME,
        help=f"Tmux session name (default: {SESSION_NAME})",
    )

    parser.add_argument(
        "-l",
        "--layout",
        type=str,
        choices=LAYOUTS,
        default="tiled",
        help="Tmux pane layout (default: tiled)",
    )

    parser.add_argument(
        "-d",
        "--working-dir",
        type=str,
        default="/home/emhar/nexly-notes",
        help="Working directory for Claude sessions",
    )

    parser.add_argument(
        "-c",
        "--command",
        type=str,
        default="claude",
        help="Command to run in each pane (default: claude)",
    )

    parser.add_argument(
        "-a", "--attach", action="store_true", help="Attach to session after creating"
    )

    parser.add_argument(
        "-k",
        "--kill",
        action="store_true",
        help="Kill existing session before creating new one",
    )

    parser.add_argument("--list", action="store_true", help="List all tmux sessions")

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force create new session (kills existing if present)",
    )

    parser.add_argument(
        "--no-run",
        action="store_true",
        help="Create panes without running any command (empty shells)",
    )

    parser.add_argument(
        "-w",
        "--windows",
        action="store_true",
        help="Use separate windows instead of panes (full screen each)",
    )

    parser.add_argument(
        "-p",
        "--prefix",
        type=str,
        default="",
        help="Custom prefix key (e.g., C-a, C-Space). Default: C-b",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Check dependencies
    if not check_dependencies():
        return 1

    # Handle list command
    if args.list:
        list_sessions()
        return 0

    # Handle kill command
    if args.kill:
        if session_exists(args.session_name):
            kill_session(args.session_name)
        else:
            print(f"Session '{args.session_name}' does not exist")
        return 0

    # Check if session already exists
    if session_exists(args.session_name):
        if args.force:
            kill_session(args.session_name)
        else:
            print(f"Session '{args.session_name}' already exists")
            print("Use --force to recreate or --kill to remove it")
            if args.attach:
                print("Attaching to existing session...")
                attach_session(args.session_name)
            return 0

    # Validate num_panes
    if args.num_panes < 1:
        print("Error: Number of panes must be at least 1")
        return 1

    if args.num_panes > 9:
        print("Warning: More than 9 panes may be hard to manage")

    # Create the session
    create_session(
        num_panes=args.num_panes,
        session_name=args.session_name,
        layout=args.layout,
        working_dir=args.working_dir,
        command=args.command,
        no_run=args.no_run,
        use_windows=args.windows,
        prefix=args.prefix,
    )

    print(f"\nTo attach to the session, run:")
    print(f"  tmux attach -t {args.session_name}")

    # Attach if requested
    if args.attach:
        print("\nAttaching to session...")
        attach_session(args.session_name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
