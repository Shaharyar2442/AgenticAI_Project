"""
Phase 4 Unit Tests — FastAPI backend endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


class TestRootEndpoint:
    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_generate_requires_prompt(self):
        response = client.post("/api/generate", json={})
        assert response.status_code == 422  # Pydantic validation error
