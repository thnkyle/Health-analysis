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


def test_health_check():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_sync_and_query():
    now = datetime.utcnow()
    payload = {
        "records": [
            {
                "user_id": "user1",
                "data_type": "steps",
                "value": 8500,
                "unit": "count",
                "recorded_at": now.isoformat(),
            },
            {
                "user_id": "user1",
                "data_type": "heart_rate",
                "value": 72,
                "unit": "bpm",
                "recorded_at": now.isoformat(),
            },
        ]
    }
    resp = client.post("/api/v1/sync", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] == 2

    # Query records
    resp = client.get("/api/v1/records", params={"user_id": "user1"})
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 2


def test_query_by_type():
    now = datetime.utcnow()
    payload = {
        "records": [
            {"user_id": "user1", "data_type": "steps", "value": 5000, "unit": "count", "recorded_at": now.isoformat()},
            {"user_id": "user1", "data_type": "weight", "value": 75.5, "unit": "kg", "recorded_at": now.isoformat()},
        ]
    }
    client.post("/api/v1/sync", json=payload)

    resp = client.get("/api/v1/records", params={"user_id": "user1", "data_type": "steps"})
    records = resp.json()
    assert len(records) == 1
    assert records[0]["data_type"] == "steps"


def test_trends():
    now = datetime.utcnow()
    records = []
    for i in range(7):
        records.append({
            "user_id": "user1",
            "data_type": "steps",
            "value": 5000 + i * 1000,
            "unit": "count",
            "recorded_at": (now - timedelta(days=6 - i)).isoformat(),
        })
    client.post("/api/v1/sync", json={"records": records})

    resp = client.get("/api/v1/trends/steps", params={"user_id": "user1", "granularity": "daily"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_type"] == "steps"
    assert len(data["trends"]) >= 1


def test_anomalies():
    now = datetime.utcnow()
    records = []
    # Normal values
    for i in range(10):
        records.append({
            "user_id": "user1",
            "data_type": "heart_rate",
            "value": 70 + (i % 3),
            "unit": "bpm",
            "recorded_at": (now - timedelta(hours=10 - i)).isoformat(),
        })
    # Anomalous value
    records.append({
        "user_id": "user1",
        "data_type": "heart_rate",
        "value": 180,
        "unit": "bpm",
        "recorded_at": now.isoformat(),
    })
    client.post("/api/v1/sync", json={"records": records})

    resp = client.get("/api/v1/anomalies", params={"user_id": "user1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["anomalies"][0]["value"] == 180


def test_empty_records():
    resp = client.get("/api/v1/records", params={"user_id": "nonexistent"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_empty_trends():
    resp = client.get("/api/v1/trends/steps", params={"user_id": "nonexistent"})
    assert resp.status_code == 200
    assert resp.json()["trends"] == []
