"""Run parallel headless Claude sessions to explore the codebase from multiple angles."""

import argparse
import json
import logging
import threading
from dataclasses import dataclass
from subprocess import DEVNULL, PIPE, Popen

logger = logging.getLogger(__name__)

STRUCTURE_PROMPT = """\
Analyze the project structure and configuration.

Report on:
- Directory organization and key folders
- Configuration files and their purposes
- Build and development tooling
- Entry points and main modules

Return a concise markdown report.
"""

GIT_DEPS_PROMPT = """\
Analyze git activity and project dependencies.

Report on:
- Current branch and staging state
- Recent commits (last 10-15) with authors and messages
- Modified, added, and deleted files
- Core and dev dependencies with versions
- Potential version conflicts or outdated packages

Return a concise markdown report.
"""

IMPLEMENTATION_PROMPT = """\
Analyze the current implementation state and technical health.

Report on:
- Work-in-progress features and incomplete changes
- Technical debt indicators
- Configuration constraints and integration points
- Identified issues, warnings, or TODOs

Return a concise markdown report.
"""


@dataclass
class FocusArea:
    name: str
    heading: str
    prompt: str


FOCUS_AREAS = [
    FocusArea("structure", "Structure & Configuration", STRUCTURE_PROMPT),
    FocusArea("git_and_deps", "Git & Dependencies", GIT_DEPS_PROMPT),
    FocusArea("implementation", "Implementation State", IMPLEMENTATION_PROMPT),
]

TIMEOUT = 300  # seconds per focus area

# Read-only permission rules — no write or destructive Bash commands allowed
ALLOWED_TOOLS = ",".join(
    [
        "Read",
        "Glob",
        "Grep",
        "Bash(git log *)",
        "Bash(git status *)",
        "Bash(git diff *)",
        "Bash(git branch *)",
        "Bash(ls *)",
        "Bash(find *)",
        "Bash(cat *)",
    ]
)

# Tool name → colour for the UI log
_TOOL_COLOURS = {
    "Read": "cyan",
    "Glob": "green",
    "Grep": "yellow",
    "Bash": "magenta",
    "Agent": "blue",
}


def _build_command(prompt: str) -> list[str]:
    return [
        "claude",
        "-p",
        prompt,
        "--allowedTools",
        ALLOWED_TOOLS,
        "--output-format",
        "stream-json",
        "--verbose",
    ]


def _log_event(area_name: str, data: dict) -> None:
    """Log a single stream-json event (plain-mode only)."""
    event_type = data.get("type")

    if event_type == "system" and data.get("subtype") == "init":
        logger.info(
            "%s session started — model=%s tools=%s",
            area_name,
            data.get("model"),
            data.get("tools"),
        )
    elif event_type == "assistant":
        msg = data.get("message")
        if not isinstance(msg, dict):
            return
        for block in msg.get("content", []):
            if block.get("type") == "tool_use":
                tool = block["name"]
                inp = block.get("input", {})
                inp_str = ", ".join(f"{k}={v}" for k, v in inp.items())[:120]
                logger.info("%s  → [%s] %s", area_name, tool, inp_str)
            elif block.get("type") == "text" and block.get("text", "").strip():
                logger.debug("%s  text: %s", area_name, block["text"][:120])
    elif event_type == "result":
        turns = data.get("num_turns", 0)
        duration_s = data.get("duration_ms", 0) / 1000
        cost = data.get("total_cost_usd", 0)
        is_error = data.get("is_error", False)
        logger.info(
            "%s done — turns=%d  %.1fs  $%.4f%s",
            area_name,
            turns,
            duration_s,
            cost,
            "  [is_error=true]" if is_error else "",
        )


def _collect(area: FocusArea, proc: Popen, on_event=None) -> str:
    """Read stdout line by line; call on_event(data) for each parsed line."""
    lines = []
    for raw_line in proc.stdout:
        line = raw_line.strip()
        if not line:
            continue
        lines.append(line)
        try:
            data = json.loads(line)
            if on_event:
                on_event(data)
            else:
                _log_event(area.name, data)
        except json.JSONDecodeError:
            logger.debug("%s unparseable line: %s", area.name, line[:80])
    proc.wait()
    return "\n".join(lines)


def _parse_result(area: FocusArea, returncode: int, stdout: str) -> tuple[str, str]:
    if returncode != 0:
        logger.warning("%s exited with code %d", area.name, returncode)
        return area.heading, f"_Error: process exited with code {returncode}_"

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("type") == "result" and "result" in data:
            if data.get("is_error"):
                logger.warning(
                    "%s result has is_error=true: %s", area.name, data["result"][:200]
                )
            return area.heading, data["result"]

    logger.warning("%s: no result line found in stream output", area.name)
    return area.heading, "_Error: no result found in stream-json output_"


# ---------------------------------------------------------------------------
# Plain (non-UI) mode
# ---------------------------------------------------------------------------


def run(cwd: str | None = None, out=None) -> None:
    """Launch all explorers in parallel and stream each section to `out`."""
    import sys

    if out is None:
        out = sys.stdout

    procs = []
    for area in FOCUS_AREAS:
        cmd = _build_command(area.prompt)
        logger.info("Launching %s explorer", area.name)
        logger.debug("Command: %s", cmd)
        procs.append(
            (area, Popen(cmd, stdout=PIPE, stderr=DEVNULL, text=True, cwd=cwd))
        )

    results: dict[str, str] = {}

    def collect_one(area: FocusArea, proc: Popen) -> None:
        results[area.name] = _collect(area, proc)

    threads = [
        (
            area,
            proc,
            threading.Thread(target=collect_one, args=(area, proc), daemon=True),
        )
        for area, proc in procs
    ]
    for _, _, t in threads:
        t.start()

    print("# Codebase Status Report\n", file=out, flush=True)
    for area, proc, t in threads:
        t.join(timeout=TIMEOUT)
        if t.is_alive():
            proc.kill()
            t.join(timeout=5)  # give thread time to notice the kill
            logger.warning("%s timed out — killed", area.name)
            heading, content = area.heading, "_Error: exploration timed out_"
        else:
            stdout = results.get(area.name, "")
            heading, content = _parse_result(area, proc.returncode, stdout)
        print(f"## {heading}\n\n{content}\n", file=out, flush=True)


# ---------------------------------------------------------------------------
# Textual UI
# ---------------------------------------------------------------------------


def run_ui(cwd: str | None = None) -> None:
    from rich.markdown import Markdown as RichMarkdown
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Footer, Header, Label, RichLog

    class ExplorerPanel(Vertical):
        DEFAULT_CSS = """
        ExplorerPanel {
            border: round $primary;
            width: 1fr;
            height: 1fr;
            padding: 0 1;
        }
        ExplorerPanel .panel-title {
            text-style: bold;
            color: $accent;
            height: 1;
            margin-bottom: 0;
        }
        ExplorerPanel .panel-status {
            height: 1;
            margin-bottom: 1;
        }
        ExplorerPanel RichLog {
            height: 1fr;
        }
        """

        def __init__(self, area: FocusArea) -> None:
            super().__init__(id=f"panel-{area.name}")
            self.area = area

        def compose(self) -> ComposeResult:
            yield Label(self.area.heading, classes="panel-title")
            yield Label(
                "[yellow]⟳ Launching…[/yellow]",
                classes="panel-status",
                id=f"status-{self.area.name}",
            )
            yield RichLog(wrap=True, markup=True, id=f"log-{self.area.name}")

        # --- called from worker thread via call_from_thread ---

        def add_tool_call(self, tool: str, args: str) -> None:
            colour = _TOOL_COLOURS.get(tool, "white")
            log = self.query_one(RichLog)
            log.write(f"[{colour}]→ [{tool}][/{colour}] {args}")

        def set_running(self) -> None:
            self.query_one(f"#status-{self.area.name}", Label).update(
                "[yellow]⟳ Running…[/yellow]"
            )

        def set_result(
            self, content: str, turns: int, duration_s: float, cost: float
        ) -> None:
            self.query_one(f"#status-{self.area.name}", Label).update(
                f"[green]✓ Done[/green]  [dim]{turns} turns · {duration_s:.0f}s · ${cost:.4f}[/dim]"
            )
            log = self.query_one(RichLog)
            log.clear()
            log.write(RichMarkdown(content))

        def set_error(self, message: str) -> None:
            self.query_one(f"#status-{self.area.name}", Label).update(
                "[red]✗ Error[/red]"
            )
            self.query_one(RichLog).write(f"[red]{message}[/red]")

        def set_timeout(self) -> None:
            self.query_one(f"#status-{self.area.name}", Label).update(
                "[red]✗ Timed out[/red]"
            )

    class CodebaseStatusApp(App):
        TITLE = "Codebase Status Report"

        def __init__(self, cwd: str | None = None) -> None:
            super().__init__()
            self.cwd = cwd
            self._panels: dict[str, ExplorerPanel] = {}
            self._done_count = 0

        def compose(self) -> ComposeResult:
            yield Header(show_clock=False)
            with Horizontal():
                for area in FOCUS_AREAS:
                    panel = ExplorerPanel(area)
                    self._panels[area.name] = panel
                    yield panel
            yield Footer()

        def on_mount(self) -> None:
            for area in FOCUS_AREAS:
                self.run_worker(lambda a=area: self._explore(a), thread=True)

        def _explore(self, area: FocusArea) -> None:
            """Worker — runs in a background thread."""
            panel = self._panels[area.name]
            self.call_from_thread(panel.set_running)

            cmd = _build_command(area.prompt)
            proc = Popen(cmd, stdout=PIPE, stderr=DEVNULL, text=True, cwd=self.cwd)

            stats: dict = {}

            def on_event(data: dict) -> None:
                event_type = data.get("type")
                if event_type == "assistant":
                    msg = data.get("message")
                    if not isinstance(msg, dict):
                        return
                    for block in msg.get("content", []):
                        if block.get("type") == "tool_use":
                            tool = block["name"]
                            inp = block.get("input", {})
                            args_str = ", ".join(f"{k}={v}" for k, v in inp.items())[
                                :80
                            ]
                            self.call_from_thread(panel.add_tool_call, tool, args_str)
                elif event_type == "result":
                    stats["turns"] = data.get("num_turns", 0)
                    stats["duration_s"] = data.get("duration_ms", 0) / 1000
                    stats["cost"] = data.get("total_cost_usd", 0.0)

            # Use a worker-level thread join for timeout
            result_holder: list[str] = []
            done_event = threading.Event()

            def do_collect() -> None:
                stdout = _collect(area, proc, on_event=on_event)
                result_holder.append(stdout)
                done_event.set()

            t = threading.Thread(target=do_collect, daemon=True)
            t.start()
            timed_out = not done_event.wait(timeout=TIMEOUT)

            if timed_out:
                proc.kill()
                t.join()
                self.call_from_thread(panel.set_timeout)
            else:
                stdout = result_holder[0] if result_holder else ""
                _, content = _parse_result(area, proc.returncode, stdout)
                if content.startswith("_Error:"):
                    self.call_from_thread(panel.set_error, content)
                else:
                    self.call_from_thread(
                        panel.set_result,
                        content,
                        stats.get("turns", 0),
                        stats.get("duration_s", 0.0),
                        stats.get("cost", 0.0),
                    )

            self.call_from_thread(self._on_area_done)

        def _on_area_done(self) -> None:
            self._done_count += 1

    CodebaseStatusApp(cwd=cwd).run()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Explore the codebase using parallel Claude sessions."
    )
    parser.add_argument(
        "--cwd", default=None, help="Working directory (default: current)"
    )
    parser.add_argument(
        "--plain", action="store_true", help="Plain text output (no TUI)"
    )
    parsed = parser.parse_args(args)

    if parsed.plain:
        logging.basicConfig(
            level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
        )
        run(cwd=parsed.cwd)
    else:
        run_ui(cwd=parsed.cwd)


if __name__ == "__main__":
    main()
