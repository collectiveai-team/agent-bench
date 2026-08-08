from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from prefect.testing.utilities import prefect_test_harness
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.main import create_app
from app.routes.jobs import get_job_service
from app.services.jobs import JobService


class NoOpDispatcher:
    def enqueue(self, job_id: str) -> None:
        pass


def get_test_job_service(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> JobService:
    return JobService(
        session,
        request.app.state.settings,
        NoOpDispatcher(),
        request.app.state.bus,
    )


@pytest.fixture(scope="session", autouse=True)
def prefect_harness() -> Iterator[None]:
    with prefect_test_harness():
        yield


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "taskflow.db"


@pytest.fixture
def app(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[FastAPI]:
    monkeypatch.setenv("TASKFLOW_DB_PATH", str(db_path))
    get_settings.cache_clear()
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: Settings(db_path=str(db_path))
    application.dependency_overrides[get_job_service] = get_test_job_service
    yield application
    get_settings.cache_clear()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def inline_client(app: FastAPI) -> Iterator[TestClient]:
    app.dependency_overrides.pop(get_job_service)
    with TestClient(app) as test_client:
        yield test_client
