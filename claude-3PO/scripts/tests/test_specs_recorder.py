"""Tests for recorder — vision/decision Write events recording to docs state."""

import pytest
from utils.recorder import Recorder
from helpers import make_hook_input


def _init_specs_docs(state) -> None:
    state.set("docs", {
        "product_vision": {"written": False, "path": ""},
        "decisions": {"written": False, "path": ""},
        "architecture": {"written": False, "path": ""},
        "backlog": {"written": False, "md_path": "", "json_path": ""},
    })


class TestRecordVisionWrite:
    def test_records_product_vision_write(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("vision")
        # Initialize docs state
        state.set("docs", {
            "product_vision": {"written": False, "path": ""},
            "decisions": {"written": False, "path": ""},
            "architecture": {"written": False, "path": ""},
            "backlog": {"written": False, "md_path": "", "json_path": ""},
        })

        recorder = Recorder(state)
        recorder.record_write(
            "vision",
            "projects/docs/product-vision.md",
            is_plan_file=False,
        )

        docs = state.get("docs", {})
        assert docs["product_vision"]["written"] is True
        assert docs["product_vision"]["path"] == "projects/docs/product-vision.md"


class TestRecordDecisionWrite:
    def test_records_decisions_write(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("decision")
        state.set("docs", {
            "product_vision": {"written": True, "path": "projects/docs/product-vision.md"},
            "decisions": {"written": False, "path": ""},
            "architecture": {"written": False, "path": ""},
            "backlog": {"written": False, "md_path": "", "json_path": ""},
        })

        recorder = Recorder(state)
        recorder.record_write(
            "decision",
            "projects/docs/decisions.md",
            is_plan_file=False,
        )

        docs = state.get("docs", {})
        assert docs["decisions"]["written"] is True
        assert docs["decisions"]["path"] == "projects/docs/decisions.md"


class TestRecordNonSpecsWriteUnchanged:
    """Existing write recording for build/implement should still work."""

    def test_plan_write_still_works(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("plan")

        recorder = Recorder(state)
        recorder.record_write("plan", ".claude/plans/latest-plan.md", is_plan_file=True)

        assert state.plan["written"] is True
        assert state.plan["file_path"] == ".claude/plans/latest-plan.md"

    def test_report_write_still_works(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("write-report")

        recorder = Recorder(state)
        recorder.record_write("write-report", ".claude/reports/report.md", is_plan_file=False)

        assert state.report_written is True


class TestSpecsDocPathIsolation:
    """Bug #3: unrelated writes in vision/decision must not overwrite docs.*.path."""

    def test_vision_path_not_overwritten_by_unrelated_write(self, config, state):
        state.set("workflow_type", "specs")
        state.set("test_mode", True)
        state.add_phase("vision")
        _init_specs_docs(state)

        recorder = Recorder(state)
        hook = make_hook_input("Write", {"file_path": "E2E_SPECS_TEST_REPORT.md"})
        recorder.record(hook, config)

        docs = state.get("docs", {})
        assert docs["product_vision"]["written"] is False
        assert docs["product_vision"]["path"] == ""

    def test_decision_path_not_overwritten_by_unrelated_write(self, config, state):
        state.set("workflow_type", "specs")
        state.set("test_mode", True)
        state.add_phase("decision")
        _init_specs_docs(state)

        recorder = Recorder(state)
        hook = make_hook_input("Write", {"file_path": "E2E_SPECS_TEST_REPORT.md"})
        recorder.record(hook, config)

        docs = state.get("docs", {})
        assert docs["decisions"]["written"] is False
        assert docs["decisions"]["path"] == ""

    def test_vision_path_recorded_for_canonical_write(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("vision")
        _init_specs_docs(state)

        recorder = Recorder(state)
        expected = config.product_vision_file_path
        hook = make_hook_input("Write", {"file_path": expected, "content": "# vision"})
        recorder.record(hook, config)

        docs = state.get("docs", {})
        assert docs["product_vision"]["written"] is True
        assert docs["product_vision"]["path"] == expected

    def test_vision_absolute_write_stored_as_config_relative(self, config, state):
        """Bug: product_vision.path was stored as absolute, breaking parity with architecture.path."""
        state.set("workflow_type", "specs")
        state.add_phase("vision")
        _init_specs_docs(state)

        recorder = Recorder(state)
        absolute = "/home/user/project/" + config.product_vision_file_path
        hook = make_hook_input("Write", {"file_path": absolute, "content": "# vision"})
        recorder.record(hook, config)

        docs = state.get("docs", {})
        assert docs["product_vision"]["path"] == config.product_vision_file_path

    def test_decision_absolute_write_stored_as_config_relative(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("decision")
        _init_specs_docs(state)

        recorder = Recorder(state)
        absolute = "/home/user/project/" + config.decisions_file_path
        hook = make_hook_input("Write", {"file_path": absolute, "content": "# decisions"})
        recorder.record(hook, config)

        docs = state.get("docs", {})
        assert docs["decisions"]["path"] == config.decisions_file_path
