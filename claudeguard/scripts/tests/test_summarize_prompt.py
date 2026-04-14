"""Tests for summarize_prompt.py — build instruction extraction."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from summarize_prompt import extract_build_instructions


class TestExtractBuildInstructions:
    def test_simple_build(self):
        assert extract_build_instructions("/build create a login form") == "create a login form"

    def test_namespaced_build(self):
        assert extract_build_instructions("/claudeguard:build create a login form") == "create a login form"

    def test_strips_flags(self):
        result = extract_build_instructions("/build --tdd --skip-explore create a form")
        assert result == "create a form"

    def test_strips_story_id(self):
        result = extract_build_instructions("/build SK-001 create a form")
        assert result == "create a form"

    def test_strips_all(self):
        result = extract_build_instructions("/build --tdd --reset SK-001 create a form")
        assert result == "create a form"

    def test_not_build_returns_none(self):
        assert extract_build_instructions("/implement SK-001") is None

    def test_random_prompt_returns_none(self):
        assert extract_build_instructions("what is the weather?") is None

    def test_empty_instructions_returns_none(self):
        assert extract_build_instructions("/build --tdd") is None

    def test_multiline_prompt(self):
        result = extract_build_instructions("/build create a login form\nwith OAuth support")
        assert "create a login form" in result
        assert "OAuth support" in result
