"""Pydantic model for a parsed story/task item from backlog.md."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class StoryItem(BaseModel):
    """One ``### ID: Title`` block under ``## Stories`` in backlog.md.

    Mirrors the metadata fields the SpecsValidator extracts from each story
    block (description, priority, milestone, blocking links, acceptance
    criteria, blockquotes). ``extra="allow"`` lets new optional fields ship
    without breaking older parses.

    Example:
        >>> StoryItem(id="US-001", title="Login flow", line=42).priority
        ''
    """

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
        """
        Build the dict shape used by ``SpecsValidator._parse_item_line``.

        Returned as a dict (not the model instance) because downstream code
        mutates fields imperatively as the parser walks subsequent lines of
        the story block — Pydantic validation would fight that incremental
        construction. Validation can happen at the boundary if/when the dict
        is finally fed back through ``StoryItem(**...)``.

        Args:
            sid (str): Story/task ID (e.g. ``"US-001"``).
            title (str): Heading text after the ID and colon.
            line_num (int): 1-indexed line number where the heading lives.

        Returns:
            dict[str, Any]: Story dict with empty defaults for every optional
            field, ready for incremental mutation.

        Example:
            >>> item = StoryItem.empty("US-001", "Login flow", 42)
            >>> item["id"], item["title"], item["line"]
            ('US-001', 'Login flow', 42)
            >>> item["acceptance_criteria"]
            []
        """
        return cls(id=sid, title=title, line=line_num).model_dump()
