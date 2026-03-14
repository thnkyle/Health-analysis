from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

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


# --- AI Analysis Tests ---


def _mock_claude_response(text: str):
    """Create a mock Anthropic API response."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def _seed_health_data(headers):
    """Insert sample health data for AI analysis tests."""
    now = datetime.utcnow()
    records = []
    for i in range(10):
        records.append({
            "data_type": "heart_rate",
            "value": 70 + (i % 3),
            "unit": "bpm",
            "recorded_at": (now - timedelta(hours=10 - i)).isoformat(),
        })
        records.append({
            "data_type": "steps",
            "value": 5000 + i * 500,
            "unit": "count",
            "recorded_at": (now - timedelta(hours=10 - i)).isoformat(),
        })
    # Add an anomalous heart rate
    records.append({
        "data_type": "heart_rate",
        "value": 180,
        "unit": "bpm",
        "recorded_at": now.isoformat(),
    })
    client.post("/api/v1/sync", json={"records": records}, headers=headers)


@patch("services.ai_analysis._get_client")
def test_ai_insights(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.messages.create.return_value = _mock_claude_response(
        '{"summary": "Your health data shows consistent patterns.", '
        '"insights": ["Heart rate is stable around 70-72 bpm."], '
        '"recommendations": ["Maintain current activity levels."], '
        '"risk_factors": ["One elevated heart rate reading at 180 bpm."]}'
    )

    headers = register_and_login()
    _seed_health_data(headers)

    resp = client.get("/api/v1/ai/insights", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert isinstance(data["insights"], list)
    assert isinstance(data["recommendations"], list)
    assert isinstance(data["risk_factors"], list)

    # Verify Claude API was called
    mock_client.messages.create.assert_called_once()


@patch("services.ai_analysis._get_client")
def test_ai_insights_with_type_filter(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.messages.create.return_value = _mock_claude_response(
        '{"summary": "Step count is increasing.", '
        '"insights": ["Daily steps range from 5000 to 9500."], '
        '"recommendations": ["Keep increasing daily steps."], '
        '"risk_factors": []}'
    )

    headers = register_and_login()
    _seed_health_data(headers)

    resp = client.get("/api/v1/ai/insights", params={"data_type": "steps"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert len(data["risk_factors"]) == 0


@patch("services.ai_analysis._get_client")
def test_ai_anomalies(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.messages.create.return_value = _mock_claude_response(
        '{"anomalies": [{"data_type": "heart_rate", "value": 180, '
        '"recorded_at": "2024-01-01T00:00:00", "severity": "high", '
        '"reason": "Heart rate of 180 bpm is significantly above the baseline of 70-72 bpm."}], '
        '"analysis": "One significant anomaly detected in heart rate data.", '
        '"correlations": ["Elevated heart rate may correlate with increased step count."]}'
    )

    headers = register_and_login()
    _seed_health_data(headers)

    resp = client.get("/api/v1/ai/anomalies", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["anomalies"][0]["severity"] == "high"
    assert isinstance(data["correlations"], list)
    assert "analysis" in data


@patch("services.ai_analysis._get_client")
def test_ai_insights_empty_data(mock_get_client):
    """AI insights should handle empty datasets without calling Claude."""
    headers = register_and_login()

    resp = client.get("/api/v1/ai/insights", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "No health data" in data["summary"]

    # Claude should NOT be called when there's no data
    mock_get_client.assert_not_called()


@patch("services.ai_analysis._get_client")
def test_ai_anomalies_insufficient_data(mock_get_client):
    """AI anomaly detection should require at least 3 data points."""
    headers = register_and_login()
    now = datetime.utcnow()
    payload = {
        "records": [
            {"data_type": "heart_rate", "value": 72, "unit": "bpm", "recorded_at": now.isoformat()},
        ]
    }
    client.post("/api/v1/sync", json=payload, headers=headers)

    resp = client.get("/api/v1/ai/anomalies", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert "Not enough data" in data["analysis"]

    mock_get_client.assert_not_called()


@patch("services.ai_analysis._get_client")
def test_ai_insights_malformed_response(mock_get_client):
    """AI insights should handle non-JSON responses from Claude gracefully."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.messages.create.return_value = _mock_claude_response(
        "This is not valid JSON but a plain text response about health."
    )

    headers = register_and_login()
    _seed_health_data(headers)

    resp = client.get("/api/v1/ai/insights", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # Should fall back gracefully with the raw text as summary
    assert "summary" in data
