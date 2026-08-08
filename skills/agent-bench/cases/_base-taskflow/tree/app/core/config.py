import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Literal, get_args

from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_version() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject.open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


# Single source of truth: the version lives only in pyproject.toml.
APP_VERSION = _project_version()

JobStatus = Literal["pending", "running", "succeeded", "failed"]
JOB_STATUSES: tuple[str, ...] = get_args(JobStatus)
DEFAULT_JOB_STATUS: JobStatus = "pending"
RUNNING_JOB_STATUS: JobStatus = "running"
SUCCEEDED_JOB_STATUS: JobStatus = "succeeded"
FAILED_JOB_STATUS: JobStatus = "failed"

JobType = Literal["word_count", "reverse", "summary_stats"]
JOB_TYPES: tuple[str, ...] = get_args(JobType)
WORD_COUNT_JOB_TYPE: JobType = "word_count"
REVERSE_JOB_TYPE: JobType = "reverse"
SUMMARY_STATS_JOB_TYPE: JobType = "summary_stats"

WorkerMode = Literal["inline", "prefect"]
INLINE_WORKER_MODE: WorkerMode = "inline"
PREFECT_WORKER_MODE: WorkerMode = "prefect"

PROCESS_JOB_FLOW_NAME = "process-job"
PROCESS_JOB_DEPLOYMENT_NAME = "taskflow"
PROCESS_JOB_DEPLOYMENT_FULL_NAME = (
    f"{PROCESS_JOB_FLOW_NAME}/{PROCESS_JOB_DEPLOYMENT_NAME}"
)

JobEventName = Literal[
    "job.created", "job.started", "job.succeeded", "job.failed"
]
JOB_CREATED_EVENT: JobEventName = "job.created"
JOB_STARTED_EVENT: JobEventName = "job.started"
JOB_SUCCEEDED_EVENT: JobEventName = "job.succeeded"
JOB_FAILED_EVENT: JobEventName = "job.failed"
WS_CONNECTED_EVENT = "connected"
DEFAULT_EVENT_QUEUE_SIZE = 100
JOB_STATUS_POLL_INTERVAL_S = 0.5

MIN_JOB_LIMIT = 1
MAX_JOB_LIMIT = 100
DEFAULT_JOB_LIMIT = 20
DEFAULT_JOB_OFFSET = 0


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TASKFLOW_")

    db_path: str = ".data/taskflow.db"
    worker_mode: WorkerMode = INLINE_WORKER_MODE


@lru_cache
def get_settings() -> Settings:
    return Settings()
