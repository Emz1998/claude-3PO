#!/usr/bin/env python3
"""
Tmux Terminal Spawner

Opens a separate terminal in tmux - either as a new window or pane.
"""

import subprocess
import argparse
import sys
import shutil
import os
from typing import Optional

DEFAULT_SESSION = "terminal"


def check_tmux() -> bool:
    """Check if tmux is installed."""
    if not shutil.which("tmux"):
        print("Error: tmux is not installed. Install with: sudo apt install tmux")
        return False
    return True


def is_inside_tmux() -> bool:
    """Check if currently running inside a tmux session."""
    return os.environ.get("TMUX") is not None


def session_exists(session_name: str) -> bool:
    """Check if a tmux session exists."""
    result = subprocess.run(
        ["tmux", "has-session", "-t", session_name], capture_output=True
    )
    return result.returncode == 0


def get_current_session() -> Optional[str]:
    """Get the name of the current tmux session if inside one."""
    if not is_inside_tmux():
        return None
    result = subprocess.run(
        ["tmux", "display-message", "-p", "#S"], capture_output=True, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def create_session(session_name: str, working_dir: str) -> bool:
    """Create a new tmux session."""
    result = subprocess.run(
        ["tmux", "new-session", "-d", "-s", session_name, "-c", working_dir],
        capture_output=True,
    )
    if result.returncode == 0:
        # Enable mouse support
        subprocess.run(["tmux", "set-option", "-t", session_name, "mouse", "on"])
        return True
    return False


def open_window(
    session_name: str, window_name: str, working_dir: str, command: Optional[str] = None
) -> bool:
    """Open a new window in the tmux session."""
    args = ["tmux", "new-window", "-t", session_name, "-c", working_dir]
    if window_name:
        args.extend(["-n", window_name])

    result = subprocess.run(args, capture_output=True)
    if result.returncode != 0:
        return False

    if command:
        # Get the newly created window index
        target = f"{session_name}:"
        subprocess.run(
            ["tmux", "send-keys", "-t", target, command, "Enter"], capture_output=True
        )

    return True


def open_pane(
    session_name: str,
    working_dir: str,
    horizontal: bool = False,
    command: Optional[str] = None,
) -> bool:
    """Open a new pane in the tmux session."""
    args = ["tmux", "split-window", "-t", session_name, "-c", working_dir]
    if horizontal:
        args.append("-h")

    result = subprocess.run(args, capture_output=True)
    if result.returncode != 0:
        return False

    if command:
        subprocess.run(
            ["tmux", "send-keys", "-t", session_name, command, "Enter"],
            capture_output=True,
        )

    return True


def attach_session(session_name: str) -> None:
    """Attach to a tmux session."""
    if is_inside_tmux():
        subprocess.run(["tmux", "switch-client", "-t", session_name])
    else:
        subprocess.run(["tmux", "attach-session", "-t", session_name])


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Open a separate terminal in tmux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Open new window in default session
  %(prog)s -c "npm run dev"         # Open window and run command
  %(prog)s -s mysession             # Use specific session
  %(prog)s --pane                   # Open as pane instead of window
  %(prog)s --pane -H                # Open horizontal pane
  %(prog)s -n "Dev Server" -c "npm run dev"  # Named window with command
  %(prog)s -a                       # Attach to session after opening
        """,
    )

    parser.add_argument(
        "-s",
        "--session",
        type=str,
        default=DEFAULT_SESSION,
        help=f"Tmux session name (default: {DEFAULT_SESSION})",
    )

    parser.add_argument(
        "-n", "--name", type=str, default="", help="Name for the new window"
    )

    parser.add_argument(
        "-d",
        "--dir",
        type=str,
        default=os.getcwd(),
        help="Working directory (default: current directory)",
    )

    parser.add_argument(
        "-c", "--command", type=str, default=None, help="Command to run in the terminal"
    )

    parser.add_argument(
        "--pane", action="store_true", help="Open as pane instead of window"
    )

    parser.add_argument(
        "-H",
        "--horizontal",
        action="store_true",
        help="Split horizontally (only with --pane)",
    )

    parser.add_argument(
        "-a", "--attach", action="store_true", help="Attach to session after opening"
    )

    parser.add_argument(
        "--use-current",
        action="store_true",
        help="Use current tmux session if inside one",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    if not check_tmux():
        return 1

    # Determine session to use
    session_name = args.session
    if args.use_current:
        current = get_current_session()
        if current:
            session_name = current

    # Create session if it doesn't exist
    if not session_exists(session_name):
        print(f"Creating session: {session_name}")
        if not create_session(session_name, args.dir):
            print(f"Error: Failed to create session '{session_name}'")
            return 1

    # Open window or pane
    if args.pane:
        success = open_pane(
            session_name=session_name,
            working_dir=args.dir,
            horizontal=args.horizontal,
            command=args.command,
        )
        term_type = "pane"
    else:
        success = open_window(
            session_name=session_name,
            window_name=args.name,
            working_dir=args.dir,
            command=args.command,
        )
        term_type = "window"

    if not success:
        print(f"Error: Failed to open {term_type}")
        return 1

    print(f"Opened {term_type} in session '{session_name}'")
    if args.command:
        print(f"Running: {args.command}")

    # Attach if requested
    if args.attach:
        attach_session(session_name)
    else:
        print(f"\nTo attach: tmux attach -t {session_name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
