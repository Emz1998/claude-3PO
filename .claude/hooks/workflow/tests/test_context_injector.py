"""Tests for ContextInjector — template loading and rendering."""

from pathlib import Path

import pytest

from workflow.lib.context_injector import ContextInjector


@pytest.fixture
def template_dir(tmp_path):
    """Create a temp directory with a sample template."""
    tpl = tmp_path / "greeting.md"
    tpl.write_text("Hello {name}, welcome to {project}!")
    return tmp_path


@pytest.fixture
def injector(template_dir):
    return ContextInjector(template_dir=template_dir)


class TestRenderTemplate:
    def test_render_template(self, injector):
        """Load file and fill placeholders."""
        result = injector.render("greeting.md", name="Alice", project="Avaris")
        assert result == "Hello Alice, welcome to Avaris!"


class TestRenderString:
    def test_render_string(self, injector):
        """Inline template rendering."""
        result = injector.render_string("Hi {who}!", who="Bob")
        assert result == "Hi Bob!"


class TestTemplateExists:
    def test_template_exists_true(self, injector, template_dir):
        assert injector.template_exists("greeting.md") is True

    def test_template_exists_false(self, injector):
        assert injector.template_exists("nonexistent.md") is False


class TestPlaceholderExists:
    def test_placeholder_exists_true(self, injector):
        assert injector.placeholder_exists("Hello {name}!") is True

    def test_placeholder_exists_false(self, injector):
        assert injector.placeholder_exists("No placeholders here") is False
