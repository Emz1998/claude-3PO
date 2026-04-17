"""Pydantic model for a parsed story/task item from backlog.md."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class StoryItem(BaseModel):
    """One ``### ID: Title`` block under ``## Stories`` in backlog.md."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    line: int
    description: str = ""
    priority: str = ""
    milestone: str = ""
    is_blocking: str = ""
    blocked_by: str = ""
    acceptance_criteria: list[str] = []
    blockquotes: list[str] = []

    @classmethod
    def empty(cls, sid: str, title: str, line_num: int) -> dict[str, Any]:
        """Build the dict shape used by SpecsValidator._parse_item_line.

        Returned as a dict (not the model instance) because downstream code
        mutates fields imperatively. Validation happens at the boundary if needed.
        """
        return cls(id=sid, title=title, line=line_num).model_dump()
