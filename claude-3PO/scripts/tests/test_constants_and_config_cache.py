"""Tests for centralized constants and cached Config()."""

import pytest


def test_review_phases_is_empty_stub():
    from constants.phases import REVIEW_PHASES

    assert REVIEW_PHASES == frozenset()


def test_e2e_test_report_path():
    from constants.paths import E2E_TEST_REPORT

    assert E2E_TEST_REPORT == ".claude/reports/E2E_TEST_REPORT.md"


def test_commit_batch_path_is_pathlike():
    from constants.paths import COMMIT_BATCH_PATH

    assert str(COMMIT_BATCH_PATH).endswith("commit_batch.json")


def test_stale_threshold_minutes_default():
    from constants.paths import STALE_THRESHOLD_MINUTES

    assert STALE_THRESHOLD_MINUTES == 10


def test_get_config_returns_cached_instance():
    from config import get_config

    a = get_config()
    b = get_config()
    assert a is b


def test_get_config_cache_clear_returns_fresh_instance():
    from config import get_config

    a = get_config()
    get_config.cache_clear()
    b = get_config()
    assert a is not b
