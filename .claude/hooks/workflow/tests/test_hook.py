"""Tests for Hook class — stdin reading, exit codes, output formatting."""

import json
import sys
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest
from pydantic import BaseModel

from workflow.hook import Hook


class TestReadStdin:
    def test_read_stdin(self):
        """Mock sys.stdin and verify JSON parse."""
        payload = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
        with patch("sys.stdin", StringIO(json.dumps(payload))):
            result = Hook.read_stdin()
        assert result == payload

    def test_read_stdin_invalid_json(self):
        """Invalid JSON exits with code 1."""
        with patch("sys.stdin", StringIO("not json")):
            with pytest.raises(SystemExit) as exc:
                Hook.read_stdin()
            assert exc.value.code == 1

    def test_read_stdin_empty(self):
        """Empty stdin exits with code 1."""
        with patch("sys.stdin", StringIO("")):
            with pytest.raises(SystemExit) as exc:
                Hook.read_stdin()
            assert exc.value.code == 1


class TestBlock:
    def test_block_exits_with_2(self, capsys):
        """block() prints message and exits with code 2."""
        with pytest.raises(SystemExit) as exc:
            Hook.block("blocked!")
        assert exc.value.code == 2
        assert capsys.readouterr().err.strip() == "blocked!"


class TestSuccessResponse:
    def test_success_response_exits_with_0(self, capsys):
        """success_response() prints message and exits with code 0."""
        with pytest.raises(SystemExit) as exc:
            Hook.success_response("ok")
        assert exc.value.code == 0
        assert capsys.readouterr().out.strip() == "ok"


class TestDebug:
    def test_debug_exits_with_1(self, capsys):
        """debug() prints message and exits with code 1."""
        with pytest.raises(SystemExit) as exc:
            Hook.debug("debug info")
        assert exc.value.code == 1
        assert capsys.readouterr().err.strip() == "debug info"


class TestAdvancedOutput:
    def test_advanced_output_dumps_pydantic_model(self, capsys):
        """advanced_output() serializes pydantic model and exits with 0."""

        class FakeModel(BaseModel):
            key: str = "value"

        with pytest.raises(SystemExit) as exc:
            Hook.advanced_output(FakeModel().model_dump())
        assert exc.value.code == 0
        output = json.loads(capsys.readouterr().out.strip())
        assert output == {"key": "value"}
