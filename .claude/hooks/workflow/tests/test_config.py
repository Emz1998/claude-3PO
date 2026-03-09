"""Tests for config module — YAML loading, caching, dot-notation access."""

from pathlib import Path
from unittest.mock import patch, mock_open

import pytest
import yaml

import workflow.config as config


@pytest.fixture(autouse=True)
def reset_config_cache():
    """Clear config cache before each test."""
    config._cache = None
    yield
    config._cache = None


SAMPLE_CONFIG = {
    "paths": {"base": "project", "state": "project/state.json"},
    "agents": {"reviewers": ["code-reviewer", "test-reviewer"]},
    "phases": {"workflow": ["explore", "plan"]},
}


class TestLoad:
    def test_load_returns_dict(self):
        """load() returns a dict from YAML."""
        yaml_str = yaml.dump(SAMPLE_CONFIG)
        with patch("builtins.open", mock_open(read_data=yaml_str)):
            result = config.load()
        assert isinstance(result, dict)
        assert result["paths"]["base"] == "project"

    def test_load_caches(self):
        """Second call returns the same cached object."""
        yaml_str = yaml.dump(SAMPLE_CONFIG)
        with patch("builtins.open", mock_open(read_data=yaml_str)):
            first = config.load()
            second = config.load()
        assert first is second


class TestGet:
    def test_get_dotted_key(self):
        """get('agents.reviewers') returns nested value."""
        config._cache = SAMPLE_CONFIG
        result = config.get("agents.reviewers")
        assert result == ["code-reviewer", "test-reviewer"]

    def test_get_missing_key_returns_default(self):
        """Missing key returns the provided default."""
        config._cache = SAMPLE_CONFIG
        result = config.get("nonexistent.key", "fallback")
        assert result == "fallback"

    def test_get_nested_non_dict_returns_default(self):
        """Traversing through a non-dict value returns default."""
        config._cache = {"a": "string_value"}
        result = config.get("a.b.c", "default")
        assert result == "default"


class TestLoadValidation:
    def test_load_non_dict_raises(self):
        """config.yaml that isn't a dict raises ValueError."""
        yaml_str = yaml.dump(["a", "b"])
        with patch("builtins.open", mock_open(read_data=yaml_str)):
            with pytest.raises(ValueError, match="must be a dict"):
                config.load()

    def test_load_missing_keys_raises(self):
        """config.yaml missing required keys raises ValueError."""
        incomplete = {"paths": {}}
        yaml_str = yaml.dump(incomplete)
        with patch("builtins.open", mock_open(read_data=yaml_str)):
            with pytest.raises(ValueError, match="missing required keys"):
                config.load()


class TestReload:
    def test_reload_clears_cache(self):
        """reload() clears the cache and reloads from disk."""
        config._cache = {"old": True}
        new_config = {"paths": {}, "phases": {}, "agents": {}, "new": True}
        yaml_str = yaml.dump(new_config)
        with patch("builtins.open", mock_open(read_data=yaml_str)):
            result = config.reload()
        assert result == new_config
        assert config._cache == new_config
