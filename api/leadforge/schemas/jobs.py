import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from leadforge.models.enums import JobQueue, JobStatus


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    queue: JobQueue
    kind: str
    status: JobStatus
    attempts: int
    max_attempts: int
    payload: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
