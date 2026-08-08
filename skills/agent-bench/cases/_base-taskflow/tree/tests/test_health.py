from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import APP_VERSION


def test_root(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"service": "taskflow", "version": APP_VERSION}


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_startup_creates_database(client: TestClient, db_path: Path) -> None:
    assert client.app.state.settings.db_path == str(db_path)
    assert db_path.is_file()
