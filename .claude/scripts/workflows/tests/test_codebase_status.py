"""Tests for codebase_status.py — parallel multi-agent codebase exploration."""
import json
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import codebase_status


def make_proc(stdout: str, returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    lines = [line + "\n" for line in stdout.splitlines() if line.strip()]
    proc.stdout = iter(lines)
    proc.returncode = returncode
    proc.wait.return_value = returncode
    return proc


def valid_output(text: str) -> str:
    return json.dumps({"type": "result", "subtype": "success", "result": text})


def test_success(capsys):
    procs = [
        make_proc(valid_output("Structure report")),
        make_proc(valid_output("Git report")),
        make_proc(valid_output("Implementation report")),
    ]
    with patch("codebase_status.Popen", side_effect=procs):
        codebase_status.main(["--plain"])

    out = capsys.readouterr().out
    assert "Structure & Configuration" in out
    assert "Structure report" in out
    assert "Git & Dependencies" in out
    assert "Git report" in out
    assert "Implementation State" in out
    assert "Implementation report" in out


def test_one_focus_fails(capsys):
    procs = [
        make_proc(valid_output("Structure report")),
        make_proc("", returncode=1),
        make_proc(valid_output("Implementation report")),
    ]
    with patch("codebase_status.Popen", side_effect=procs):
        codebase_status.main(["--plain"])

    out = capsys.readouterr().out
    assert "Structure report" in out
    assert "Implementation report" in out
    assert "Error" in out


def test_all_focus_fail(capsys):
    procs = [make_proc("", returncode=1) for _ in range(3)]
    with patch("codebase_status.Popen", side_effect=procs):
        codebase_status.main(["--plain"])

    out = capsys.readouterr().out
    assert "Codebase Status Report" in out
    assert out.count("Error") >= 3


def test_parallel_launch():
    procs = [make_proc(valid_output(f"Report {i}")) for i in range(3)]
    with patch("codebase_status.Popen", side_effect=procs) as mock_popen:
        codebase_status.main(["--plain"])

    assert mock_popen.call_count == len(codebase_status.FOCUS_AREAS)


def test_custom_cwd():
    procs = [make_proc(valid_output(f"Report {i}")) for i in range(3)]
    with patch("codebase_status.Popen", side_effect=procs) as mock_popen:
        codebase_status.main(["--plain", "--cwd", "/tmp"])

    for c in mock_popen.call_args_list:
        assert c.kwargs.get("cwd") == "/tmp"


def test_timeout(capsys):
    good_proc = make_proc(valid_output("Good report"))
    good_proc2 = make_proc(valid_output("Another report"))

    # stdout blocks until kill() sets the stop event
    stop_event = threading.Event()

    def hanging_stdout():
        stop_event.wait(timeout=2)  # unblocks via kill() or at most 2s
        return
        yield  # makes this a generator

    timeout_proc = MagicMock()
    timeout_proc.stdout = hanging_stdout()
    timeout_proc.returncode = 1
    timeout_proc.kill.side_effect = stop_event.set
    timeout_proc.wait.return_value = 1

    with patch("codebase_status.Popen", side_effect=[good_proc, timeout_proc, good_proc2]):
        with patch("codebase_status.TIMEOUT", 0.05):
            codebase_status.main(["--plain"])

    timeout_proc.kill.assert_called_once()
    out = capsys.readouterr().out
    assert "Good report" in out
    assert "Another report" in out
    assert "timed out" in out.lower()


def test_no_result_line(capsys):
    no_result = '{"type": "assistant", "message": "thinking..."}\n{"type": "assistant", "message": "done"}'
    procs = [
        make_proc(valid_output("Structure report")),
        make_proc(no_result),
        make_proc(valid_output("Implementation report")),
    ]
    with patch("codebase_status.Popen", side_effect=procs):
        codebase_status.main(["--plain"])

    out = capsys.readouterr().out
    assert "Structure report" in out
    assert "Implementation report" in out
    assert "Error" in out
