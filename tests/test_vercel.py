"""Test all Vercel API endpoints using FastAPI TestClient.

This proves the API works correctly before deployment.
Run: python -m pytest tests/test_vercel.py -v
"""

import json
import os
import sys

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)


def test_health():
    """Test GET /health"""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.9.0"


def test_root():
    """Test GET / returns HTML"""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_templates():
    """Test GET /api/v1/templates"""
    resp = client.get("/api/v1/templates")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert "task_manager_api" in data


def test_mutations():
    """Test GET /api/v1/mutations"""
    resp = client.get("/api/v1/mutations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_generate_world():
    """Test POST /api/v1/worlds/generate"""
    resp = client.post("/api/v1/worlds/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert "world_id" in data
    assert data["template"] == "task_manager_api"


def test_experiments():
    """Test GET /api/v1/experiments"""
    resp = client.get("/api/v1/experiments")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 7


def test_benchmark():
    """Test GET /api/v1/benchmark"""
    resp = client.get("/api/v1/benchmark")
    assert resp.status_code == 200
    data = resp.json()
    assert data["templates"] == 14
    assert data["mutations"] == 37


def test_api_docs():
    """Test GET /api/v1/docs"""
    resp = client.get("/api/v1/docs")
    assert resp.status_code == 200
    data = resp.json()
    assert "endpoints" in data
    assert len(data["endpoints"]) > 0


def test_404():
    """Test 404 for unknown route"""
    resp = client.get("/api/v1/unknown")
    assert resp.status_code == 404


def test_openapi():
    """Test OpenAPI schema is available"""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "paths" in data


def test_cors_preflight():
    """Test that OPTIONS returns a valid response"""
    resp = client.options("/health", headers={"origin": "http://localhost"})
    assert resp.status_code in (200, 204, 405)


def main():
    print("=" * 60)
    print("ForgeLab Vercel API Test Suite")
    print("=" * 60)
    print()

    tests = [
        ("Health Check", test_health),
        ("Root Page", test_root),
        ("Templates List", test_templates),
        ("Mutations List", test_mutations),
        ("Generate World", test_generate_world),
        ("Experiments", test_experiments),
        ("Benchmark", test_benchmark),
        ("API Docs", test_api_docs),
        ("404 Handling", test_404),
        ("OpenAPI Schema", test_openapi),
        ("CORS Preflight", test_cors_preflight),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  ✓ {name}")
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
    print("\n✅ All Vercel API endpoints verified!")


if __name__ == "__main__":
    main()
