"""Test all Vercel API endpoints by simulating Vercel events.

This script proves the API works correctly before deployment.
Run: python tests/test_vercel.py
"""

import json
import sys
import os

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.index import handler


def event(method, path, body=None):
    """Create a Vercel-style event."""
    return {
        "httpMethod": method,
        "path": path,
        "body": json.dumps(body) if body else None,
        "headers": {"content-type": "application/json"},
    }


def test_health():
    """Test GET /api/health"""
    result = handler(event("GET", "/api/health"), None)
    assert result["statusCode"] == 200
    data = json.loads(result["body"])
    assert data["status"] == "ok"
    assert data["templates"] == 14
    assert data["mutations"] == 37
    assert data["agents"] == 6
    print(f"  ✓ Health: {data['status']} ({data['templates']} templates, {data['mutations']} mutations)")


def test_templates():
    """Test GET /api/templates"""
    result = handler(event("GET", "/api/templates"), None)
    assert result["statusCode"] == 200
    data = json.loads(result["body"])
    assert "task_manager_api" in data["templates"]
    assert "flask_app" in data["templates"]
    assert data["total"] == 14
    print(f"  ✓ Templates: {data['total']} templates loaded")


def test_mutations():
    """Test GET /api/mutations"""
    result = handler(event("GET", "/api/mutations"), None)
    assert result["statusCode"] == 200
    data = json.loads(result["body"])
    assert data["total"] > 0
    print(f"  ✓ Mutations: {data['total']} mutations loaded")


def test_generate_world():
    """Test POST /api/worlds/generate"""
    result = handler(event("POST", "/api/worlds/generate", {
        "template": "task_manager_api",
        "mutation": "pagination_boundary"
    }), None)
    assert result["statusCode"] == 200
    data = json.loads(result["body"])
    assert data["status"] == "generated"
    assert data["template"] == "task_manager_api"
    print(f"  ✓ World: {data['world_id']} ({data['template']})")


def test_generate_world_auto():
    """Test POST /api/worlds/generate with auto mutation"""
    result = handler(event("POST", "/api/worlds/generate", {
        "template": "flask_app"
    }), None)
    assert result["statusCode"] == 200
    data = json.loads(result["body"])
    assert data["status"] == "generated"
    print(f"  ✓ World (auto): {data['world_id']} ({data['template']}/{data['mutation']})")


def test_experiments():
    """Test GET /api/experiments"""
    result = handler(event("GET", "/api/experiments"), None)
    assert result["statusCode"] == 200
    data = json.loads(result["body"])
    # In serverless mode, experiments may be empty (no DB)
    assert "experiments" in data or "total" in data
    print(f"  ✓ Experiments: endpoint works (total: {data.get('total', 0)})")


def test_docs():
    """Test GET /api/docs"""
    result = handler(event("GET", "/api/docs"), None)
    assert result["statusCode"] == 200
    data = json.loads(result["body"])
    assert data["name"] == "ForgeLab API"
    assert len(data["endpoints"]) > 0
    print(f"  ✓ Docs: {len(data['endpoints'])} endpoints documented")


def test_benchmark():
    """Test GET /api/benchmark"""
    result = handler(event("GET", "/api/benchmark"), None)
    assert result["statusCode"] == 200
    data = json.loads(result["body"])
    assert data["templates"] == 14
    print(f"  ✓ Benchmark: {data['templates']} templates, {data['mutations']} mutations")


def test_404():
    """Test 404 for unknown route"""
    result = handler(event("GET", "/api/unknown"), None)
    assert result["statusCode"] == 404
    data = json.loads(result["body"])
    assert "error" in data
    print(f"  ✓ 404: Unknown routes return 404")


def test_cors():
    """Test CORS preflight"""
    result = handler(event("OPTIONS", "/api/health"), None)
    assert result["statusCode"] == 204
    assert "Access-Control-Allow-Origin" in result["headers"]
    print(f"  ✓ CORS: Preflight returns 204 with CORS headers")


def test_invalid_json():
    """Test invalid JSON body"""
    ev = event("POST", "/api/worlds/generate", None)
    ev["body"] = "not json"
    result = handler(ev, None)
    assert result["statusCode"] == 400
    print(f"  ✓ Invalid JSON: Returns 400")


def main():
    print("=" * 60)
    print("ForgeLab Vercel API Test Suite")
    print("=" * 60)
    print()

    tests = [
        ("Health Check", test_health),
        ("Templates List", test_templates),
        ("Mutations List", test_mutations),
        ("Generate World", test_generate_world),
        ("Generate World (Auto)", test_generate_world_auto),
        ("Experiments", test_experiments),
        ("API Docs", test_docs),
        ("Benchmark", test_benchmark),
        ("404 Handling", test_404),
        ("CORS Preflight", test_cors),
        ("Invalid JSON", test_invalid_json),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
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
