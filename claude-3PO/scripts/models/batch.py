"""Pydantic model for an auto-commit batch ledger entry."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


BatchStatus = Literal["pending", "committed", "failed"]


class BatchEntry(BaseModel):
    """One row in ``commit_batch.json["batches"]``.

    Status state machine: every entry starts as ``pending`` when the batcher
    enqueues it; the async commit worker transitions it to ``committed`` on
    success or ``failed`` if the git commit raises. ``commit_message`` is set
    only after a successful commit. ``extra="allow"`` keeps older ledger
    entries readable after schema additions.

    Example:
        >>> BatchEntry(batch_id="b-1", task_id="t-1", task_subject="fix bug", files=["a.py"]).status
        'pending'
    """

    model_config = ConfigDict(extra="allow")

    batch_id: str
    task_id: str
    task_subject: str
    files: list[str]
    status: BatchStatus = "pending"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    commit_message: str | None = None
