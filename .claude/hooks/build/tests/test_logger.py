"""Tests for logger module — JSONL file writing."""

import json
from pathlib import Path

from build.logger import log, LOG_FILE


class TestLog:
    def test_writes_jsonl_entry(self, tmp_path, monkeypatch):
        """log() appends a valid JSONL line to the log file."""
        log_file = tmp_path / "workflow.log"
        monkeypatch.setattr("workflow.logger.LOG_FILE", log_file)

        log("TestEvent", tool="Bash", decision="allow")

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["event"] == "TestEvent"
        assert entry["tool"] == "Bash"
        assert entry["decision"] == "allow"
        assert "ts" in entry

    def test_appends_multiple_entries(self, tmp_path, monkeypatch):
        """Multiple log() calls append separate lines."""
        log_file = tmp_path / "workflow.log"
        monkeypatch.setattr("workflow.logger.LOG_FILE", log_file)

        log("First", a=1)
        log("Second", b=2)
        log("Third", c=3)

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 3
        assert json.loads(lines[0])["event"] == "First"
        assert json.loads(lines[1])["event"] == "Second"
        assert json.loads(lines[2])["event"] == "Third"

    def test_timestamp_format(self, tmp_path, monkeypatch):
        """Timestamp is ISO format with milliseconds."""
        log_file = tmp_path / "workflow.log"
        monkeypatch.setattr("workflow.logger.LOG_FILE", log_file)

        log("TimestampTest")

        entry = json.loads(log_file.read_text().strip())
        ts = entry["ts"]
        # Should match pattern like 2026-04-01T15:30:00.123
        assert "T" in ts
        assert "." in ts

    def test_extra_kwargs_included(self, tmp_path, monkeypatch):
        """Arbitrary kwargs are included in the log entry."""
        log_file = tmp_path / "workflow.log"
        monkeypatch.setattr("workflow.logger.LOG_FILE", log_file)

        log("Custom", agent_type="Explore", reminder="Do something", phase="plan")

        entry = json.loads(log_file.read_text().strip())
        assert entry["agent_type"] == "Explore"
        assert entry["reminder"] == "Do something"
        assert entry["phase"] == "plan"

    def test_log_file_default_path(self):
        """LOG_FILE points to workflow.log in the workflow directory."""
        assert LOG_FILE.name == "workflow.log"
        assert LOG_FILE.parent.name == "workflow"
