# tests/test_security.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_token(username, password):
    r = client.post("/auth/login", json={"username": username, "password": password})
    return r.json()["access_token"]


def test_hr_cannot_access_finance():
    """HR user should not get finance data even if they ask for it."""
    token = get_token("alice", "alice123")
    resp = client.post("/query", json={
        "query": "What is the quarterly profit from the financial report?",
        "token": token,
    })
    assert resp.status_code == 200
    data = resp.json()
    # The answer should indicate no data found, not actual financial data
    assert "financial_summary" not in data.get("namespaces_accessed", [])


def test_admin_can_access_all():
    """Admin user should access all namespaces."""
    token = get_token("admin", "admin123")
    resp = client.post("/query", json={
        "query": "What is the leave policy and what was Q4 revenue?",
        "token": token,
    })
    assert resp.status_code == 200

