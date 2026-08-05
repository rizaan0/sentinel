"""
Phase 0 smoke tests: the FastAPI app boots and can reach PostgreSQL.
"""


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db(client):
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    assert response.json()["database"] == "reachable"
