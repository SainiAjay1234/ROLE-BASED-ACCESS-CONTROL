"""
Test authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_login_success_alice():
    resp = client.post("/auth/login", json={"username": "alice", "password": "alice123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "hr"
    assert data["username"] == "alice"


def test_login_success_admin():
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_login_wrong_password():
    resp = client.post("/auth/login", json={"username": "alice", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_user():
    resp = client.post("/auth/login", json={"username": "ghost", "password": "ghost123"})
    assert resp.status_code == 401


def test_query_with_invalid_token():
    resp = client.post("/query", json={"query": "What is leave policy?", "token": "bad_token"})
    assert resp.status_code == 401


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
