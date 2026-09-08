"""Health endpoint tests."""

import pytest

from app import app, db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    database_path = tmp_path / "test.db"
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
    with app.test_client() as test_client:
        yield test_client
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_health_returns_service_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy", "service": "skillsync-core"}
