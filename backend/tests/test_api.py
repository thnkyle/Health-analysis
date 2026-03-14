from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app

# Test database
engine = create_engine("sqlite:///./test_health.db", connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def register_and_login(username="user1", password="testpass123"):
    """Helper to register a user and return an auth header."""
    client.post("/api/v1/auth/register", json={"username": username, "password": password})
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_check():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_register_and_login():
    resp = client.post("/api/v1/auth/register", json={"username": "newuser", "password": "pass123"})
    assert resp.status_code == 201
    assert resp.json()["username"] == "newuser"

    resp = client.post("/api/v1/auth/login", json={"username": "newuser", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_duplicate_register():
    client.post("/api/v1/auth/register", json={"username": "dup", "password": "pass"})
    resp = client.post("/api/v1/auth/register", json={"username": "dup", "password": "pass"})
    assert resp.status_code == 400


def test_bad_login():
    resp = client.post("/api/v1/auth/login", json={"username": "noone", "password": "wrong"})
    assert resp.status_code == 401


def test_sync_requires_auth():
    now = datetime.utcnow()
    payload = {
        "records": [
            {"data_type": "steps", "value": 8500, "unit": "count", "recorded_at": now.isoformat()},
        ]
    }
    resp = client.post("/api/v1/sync", json=payload)
    assert resp.status_code == 401


def test_sync_and_query():
    headers = register_and_login()
    now = datetime.utcnow()
    payload = {
        "records": [
            {"data_type": "steps", "value": 8500, "unit": "count", "recorded_at": now.isoformat()},
            {"data_type": "heart_rate", "value": 72, "unit": "bpm", "recorded_at": now.isoformat()},
        ]
    }
    resp = client.post("/api/v1/sync", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] == 2

    # Query records
    resp = client.get("/api/v1/records", headers=headers)
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 2


def test_query_by_type():
    headers = register_and_login()
    now = datetime.utcnow()
    payload = {
        "records": [
            {"data_type": "steps", "value": 5000, "unit": "count", "recorded_at": now.isoformat()},
            {"data_type": "weight", "value": 75.5, "unit": "kg", "recorded_at": now.isoformat()},
        ]
    }
    client.post("/api/v1/sync", json=payload, headers=headers)

    resp = client.get("/api/v1/records", params={"data_type": "steps"}, headers=headers)
    records = resp.json()
    assert len(records) == 1
    assert records[0]["data_type"] == "steps"


def test_trends():
    headers = register_and_login()
    now = datetime.utcnow()
    records = []
    for i in range(7):
        records.append({
            "data_type": "steps",
            "value": 5000 + i * 1000,
            "unit": "count",
            "recorded_at": (now - timedelta(days=6 - i)).isoformat(),
        })
    client.post("/api/v1/sync", json={"records": records}, headers=headers)

    resp = client.get("/api/v1/trends/steps", params={"granularity": "daily"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_type"] == "steps"
    assert len(data["trends"]) >= 1


def test_anomalies():
    headers = register_and_login()
    now = datetime.utcnow()
    records = []
    for i in range(10):
        records.append({
            "data_type": "heart_rate",
            "value": 70 + (i % 3),
            "unit": "bpm",
            "recorded_at": (now - timedelta(hours=10 - i)).isoformat(),
        })
    # Anomalous value
    records.append({
        "data_type": "heart_rate",
        "value": 180,
        "unit": "bpm",
        "recorded_at": now.isoformat(),
    })
    client.post("/api/v1/sync", json={"records": records}, headers=headers)

    resp = client.get("/api/v1/anomalies", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["anomalies"][0]["value"] == 180


def test_empty_records():
    headers = register_and_login()
    resp = client.get("/api/v1/records", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_empty_trends():
    headers = register_and_login()
    resp = client.get("/api/v1/trends/steps", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["trends"] == []


def test_validation_rejects_out_of_range():
    headers = register_and_login()
    now = datetime.utcnow()
    payload = {
        "records": [
            {"data_type": "heart_rate", "value": 500, "unit": "bpm", "recorded_at": now.isoformat()},
        ]
    }
    resp = client.post("/api/v1/sync", json=payload, headers=headers)
    assert resp.status_code == 422


def test_validation_accepts_valid_range():
    headers = register_and_login()
    now = datetime.utcnow()
    payload = {
        "records": [
            {"data_type": "heart_rate", "value": 72, "unit": "bpm", "recorded_at": now.isoformat()},
            {"data_type": "steps", "value": 10000, "unit": "count", "recorded_at": now.isoformat()},
            {"data_type": "weight", "value": 80.5, "unit": "kg", "recorded_at": now.isoformat()},
        ]
    }
    resp = client.post("/api/v1/sync", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["inserted"] == 3
