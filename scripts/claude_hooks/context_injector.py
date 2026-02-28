"""ContextInjector — loads markdown templates and renders them with data."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.claude_hooks.file_manager import FileManager


@dataclass
class ContextInjector:
    """Loads markdown templates and renders them with provided data."""

    template_dir: Path

    def render(self, template_name: str, **kwargs: Any) -> str:
        """Load a template file and fill placeholders with kwargs."""
        template = FileManager(self.template_dir / template_name, lock=False).load() or ""
        return template.format(**kwargs)

    def render_string(self, template: str, **kwargs: Any) -> str:
        """Render an inline template string with kwargs."""
        return template.format(**kwargs)

    def template_exists(self, template_name: str) -> bool:
        """Check if a template file exists."""
        return (self.template_dir / template_name).exists()
