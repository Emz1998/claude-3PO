"""Pydantic model for an auto-commit batch ledger entry."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


BatchStatus = Literal["pending", "committed", "failed"]


class BatchEntry(BaseModel):
    """One row in commit_batch.json["batches"]."""

    model_config = ConfigDict(extra="allow")

    batch_id: str
    task_id: str
    task_subject: str
    files: list[str]
    status: BatchStatus = "pending"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    commit_message: str | None = None
