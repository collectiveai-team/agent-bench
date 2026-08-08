from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.config import JobStatus, JobType


class JobCreate(BaseModel):
    type: JobType
    payload: dict[str, Any]


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: JobType
    status: JobStatus
    payload: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


class JobStatsCounts(BaseModel):
    pending: int
    running: int
    succeeded: int
    failed: int
    total: int


class JobTypeCounts(BaseModel):
    word_count: int
    reverse: int
    summary_stats: int


class StatsResponse(BaseModel):
    jobs: JobStatsCounts
    by_type: JobTypeCounts
    avg_duration_s: float | None
