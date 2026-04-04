#!/usr/bin/env python3
"""Convert sprint.md to sprint.json matching sample_structure.json format."""

import json
import re
import sys
from pathlib import Path
from typing import Any


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def parse_sprint_md(content: str) -> dict[str, Any]:
    lines = content.split("\n")

    # Top-level metadata parsed into typed variables
    project: str = ""
    sprint: int = 0
    goal: str = ""
    dates: dict[str, str] = {}
    capacity: dict[str, int] = {}
    total_points: int = 0

    for line in lines:
        if line.startswith("**Project:**"):
            project = line.split("**Project:**")[1].strip()
        elif line.startswith("**Sprint #:**"):
            sprint = _safe_int(line.split("**Sprint #:**")[1].strip())
        elif line.startswith("**Goal:**"):
            goal = line.split("**Goal:**")[1].strip()
        elif line.startswith("**Dates:**"):
            dates_raw = line.split("**Dates:**")[1].strip()
            parts = [d.strip() for d in re.split(r"→|->|to", dates_raw)]
            dates = {
                "start": parts[0] if len(parts) > 0 else "",
                "end": parts[1] if len(parts) > 1 else "",
            }
        elif line.startswith("**Capacity:**"):
            cap_raw = line.split("**Capacity:**")[1].strip()
            hours_match = re.search(r"(\d+)\s*hours", cap_raw)
            weeks_match = re.search(r"(\d+)\s*weeks", cap_raw)
            hours: int = int(hours_match.group(1)) if hours_match is not None else 0
            weeks: int = int(weeks_match.group(1)) if weeks_match is not None else 0
            capacity = {"hours": hours, "weeks": weeks}
        elif line.startswith("**Total Points:**"):
            total_points = _safe_int(line.split("**Total Points:**")[1].strip())

    # Parse overview table for basic item info
    table_items: list[dict[str, Any]] = []
    in_table: bool = False
    for line in lines:
        if line.startswith("| ID"):
            in_table = True
            continue
        if in_table and line.startswith("| --"):
            continue
        if in_table and line.startswith("|"):
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) >= 7:
                depends: list[str] = [
                    d.strip()
                    for d in cols[6].split(",")
                    if d.strip() and d.strip() != "-"
                ]
                blocked: list[str] = (
                    [b.strip() for b in cols[7].split(",") if b.strip()]
                    if len(cols) > 7
                    else []
                )
                entry: dict[str, Any] = {
                    "id": cols[0],
                    "type": cols[1],
                    "epic": cols[2] if cols[2] != "-" else None,
                    "title": cols[3],
                    "points": _safe_int(cols[4]),
                    "status": cols[5],
                    "dependsOn": depends,
                    "blockedBy": blocked,
                }
                table_items.append(entry)
        elif in_table and not line.startswith("|"):
            in_table = False

    # Parse detailed sections
    items: list[dict[str, Any]] = []
    for table_item in table_items:
        item: dict[str, Any] = dict(table_item)
        item_id: str = str(item["id"])
        if item["type"] == "Spike":
            item.update(_parse_spike(content, item_id))
        else:
            item.update(_parse_story(content, item_id))
        items.append(item)

    # Compute progress
    done_points: int = sum(
        _safe_int(i["points"]) for i in items if i["status"] in ("Done", "Complete")
    )
    effective_total: int = total_points if total_points > 0 else 1

    result: dict[str, Any] = {
        "project": project,
        "sprint": sprint,
        "goal": goal,
        "dates": dates,
        "capacity": capacity,
        "totalPoints": total_points,
        "items": items,
        "completedPoints": done_points,
        "progress": round(done_points / effective_total * 100) if total_points else 0,
    }
    return result


def _parse_spike(content: str, spike_id: str) -> dict[str, Any]:
    pattern = rf"#### {re.escape(spike_id)}:.*?\n(.*?)(?=\n---|\n####|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return {}

    block = match.group(1)
    result: dict[str, Any] = {}

    # Timebox
    tb = re.search(r"\*\*Timebox:\*\*\s*(.+)", block)
    if tb:
        result["timebox"] = tb.group(1).strip()

    # Deliverables
    deliverables = re.findall(r"- \[[ x]\] (.+)", block)
    if deliverables:
        result["deliverables"] = deliverables

    return result


def _parse_story(content: str, story_id: str) -> dict[str, Any]:
    pattern = (
        rf"#### {re.escape(story_id)}:.*?\n(.*?)(?=\n---|\n#### [A-Z]{{2,}}-\d|\Z)"
    )
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return {}

    block = match.group(1)
    result: dict[str, Any] = {}

    # Priority
    pri = re.search(r"\*\*Priority:\*\*\s*(.+)", block)
    if pri:
        result["priority"] = pri.group(1).strip()

    # Tasks
    tasks: list[dict[str, Any]] = []
    task_blocks = re.split(r"- \*\*T-(\d+):\*\*", block)
    for i in range(1, len(task_blocks), 2):
        task_id = f"T-{task_blocks[i]}"
        task_body = task_blocks[i + 1]

        title_match = re.match(r"\s*(.+?)(?:\n|$)", task_body)
        title = title_match.group(1).strip() if title_match else ""

        status_match = re.search(r"\*\*Status:\*\*\s*(.+)", task_body)
        status = status_match.group(1).strip() if status_match else "Todo"

        complexity_match = re.search(r"\*\*Complexity:\*\*\s*(.+)", task_body)
        complexity = complexity_match.group(1).strip() if complexity_match else ""

        depends_match = re.search(r"\*\*Depends on:\*\*\s*(.+)", task_body)
        task_depends: list[str] = []
        if depends_match:
            raw = depends_match.group(1).strip()
            if raw != "-":
                task_depends = [d.strip() for d in raw.split(",") if d.strip()]

        qa_match = re.search(r"\*\*QA loops:\*\*\s*(\d+)/(\d+)", task_body)
        qa_loops: list[int] = (
            [int(qa_match.group(1)), int(qa_match.group(2))]
            if qa_match is not None
            else [0, 3]
        )

        cr_match = re.search(r"\*\*Code Review loops:\*\*\s*(\d+)/(\d+)", task_body)
        cr_loops: list[int] = (
            [int(cr_match.group(1)), int(cr_match.group(2))]
            if cr_match is not None
            else [0, 2]
        )

        tasks.append(
            {
                "id": task_id,
                "title": title,
                "status": status,
                "complexity": complexity,
                "dependsOn": task_depends,
                "qaLoops": qa_loops,
                "codeReviewLoops": cr_loops,
            }
        )

    if tasks:
        result["tasks"] = tasks

    return result


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python sprint_md_to_json.py <path/to/sprint.md>")
        sys.exit(1)

    md_path = Path(sys.argv[1]).resolve()
    if not md_path.exists():
        print(f"Error: {md_path} not found")
        sys.exit(1)

    content = md_path.read_text(encoding="utf-8")
    data = parse_sprint_md(content)

    out_path = md_path.parent / "sprint.json"
    out_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
