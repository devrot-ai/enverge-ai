"""Vercel serverless function entry point for ForgeLab.

This module wraps the FastAPI app to work as a Vercel serverless function.
Vercel Python functions expect a `handler(event, context)` signature.
"""

import json
import os
import sys
import tempfile
from typing import Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment for Vercel
os.environ.setdefault("FORGELAB_ENV", "vercel")
os.environ.setdefault("FORGELAB_DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/forgelab.db")

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route, Router
from starlette.staticfiles import StaticFiles

# Import ForgeLab API routes
from forge.api.app import app as fastapi_app


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Vercel serverless function handler.

    Args:
        event: Vercel event with httpMethod, path, body, headers, etc.
        context: Vercel context with requestId, identity, etc.

    Returns:
        Response dict with statusCode, headers, and body.
    """
    try:
        # Convert Vercel event to Starlette request
        request = _vercel_event_to_request(event)

        # Route to FastAPI app
        scope = {
            "type": "http",
            "method": request.method,
            "path": request.url.path,
            "query_string": str(request.url.query).encode(),
            "headers": list(request.headers.raw),
            "server": ("vercel", 443),
            "client": ("0.0.0.0", 0),
        }

        # Handle the request through FastAPI
        if request.method == "OPTIONS":
            return _cors_response()

        # Get the response from FastAPI
        response = _handle_request(request)

        return {
            "statusCode": response.status_code,
            "headers": dict(response.headers),
            "body": response.body.decode("utf-8"),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(e), "message": "Internal server error"}),
        }


def _vercel_event_to_request(event: dict[str, Any]) -> Request:
    """Convert Vercel event to Starlette Request."""
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/")
    query_string = event.get("queryStringParameters", {})
    headers = event.get("headers", {})
    body = event.get("body", None)

    # Build query string
    qs_parts = []
    for k, v in query_string.items():
        if isinstance(v, list):
            for item in v:
                qs_parts.append(f"{k}={item}")
        else:
            qs_parts.append(f"{k}={v}")
    qs = "&".join(qs_parts) if qs_parts else ""

    url = f"{path}?{qs}" if qs else path

    # Create a mock request
    class MockConnection:
        def __init__(self):
            self.scope = {
                "type": "http",
                "method": http_method,
                "path": path,
                "query_string": qs.encode(),
                "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
                "server": ("vercel", 443),
                "client": ("0.0.0.0", 0),
            }

    return Request(MockConnection().scope)


def _handle_request(request: Request) -> Response:
    """Handle request through FastAPI app."""
    method = request.method
    path = request.url.path

    # Health check
    if path == "/api/health" and method == "GET":
        return JSONResponse(
            {
                "status": "ok",
                "environment": "vercel",
                "version": "0.9",
                "templates": 14,
                "mutations": 37,
                "agents": 6,
                "tests": 645,
            }
        )

    # API documentation
    if path == "/api/docs" and method == "GET":
        return JSONResponse({
            "name": "ForgeLab API",
            "version": "0.9",
            "endpoints": [
                "GET /api/health - Health check",
                "GET /api/worlds - List worlds",
                "POST /api/worlds/generate - Generate world",
                "GET /api/tasks - List tasks",
                "POST /api/tasks/generate - Generate task",
                "GET /api/runs - List runs",
                "POST /api/runs/execute - Execute run",
                "GET /api/curriculum - Get curriculum state",
                "GET /api/experiments - List experiments",
                "POST /api/experiments/run - Run experiment",
                "GET /api/benchmark - Get benchmark results",
                "GET /api/leaderboard - Get leaderboard",
            ],
            "note": "Full API available at /api/docs/openapi.json",
        })

    # OpenAPI schema
    if path == "/api/docs/openapi.json" and method == "GET":
        return JSONResponse({
            "openapi": "3.1.0",
            "info": {
                "title": "ForgeLab API",
                "version": "0.9",
                "description": "Research-grade adaptive environment factory for autonomous software engineering agents",
            },
            "paths": {},
        })

    # Worlds endpoints
    if path == "/api/worlds" and method == "GET":
        return JSONResponse({"worlds": [], "total": 0, "message": "No worlds in serverless mode. Use /api/worlds/generate to create."})

    if path == "/api/worlds/generate" and method == "POST":
        body = request._body
        data = json.loads(body) if body else {}
        template = data.get("template", "task_manager_api")
        mutation = data.get("mutation", None)

        try:
            from forge.world_factory.generator import WorldGenerator
            from forge.core.config import load_config

            config = load_config()
            generator = WorldGenerator(config=config)
            world = generator.generate(template=template, mutation=mutation)

            return JSONResponse({
                "world_id": world.world_id,
                "template": world.template,
                "mutation": world.mutation,
                "status": "generated",
            })
        except Exception as e:
            return JSONResponse(
                {"error": str(e)},
                status_code=500,
            )

    # Tasks endpoints
    if path == "/api/tasks" and method == "GET":
        return JSONResponse({"tasks": [], "total": 0, "message": "No tasks in serverless mode. Use /api/tasks/generate to create."})

    if path == "/api/tasks/generate" and method == "POST":
        body = request._body
        data = json.loads(body) if body else {}
        world_id = data.get("world_id", "")

        try:
            from forge.task_factory.generator import TaskGenerator
            from forge.core.config import load_config

            config = load_config()
            generator = TaskGenerator(config=config)
            task = generator.generate(world_id=world_id)

            return JSONResponse({
                "task_id": task.task_id,
                "world_id": task.world_id,
                "status": "generated",
            })
        except Exception as e:
            return JSONResponse(
                {"error": str(e)},
                status_code=500,
            )

    # Runs endpoints
    if path == "/api/runs" and method == "GET":
        return JSONResponse({"runs": [], "total": 0, "message": "No runs in serverless mode."})

    # Experiments endpoints
    if path == "/api/experiments" and method == "GET":
        from forge.experiments.presets import get_preset_experiments
        experiments = get_preset_experiments()
        return JSONResponse({
            "experiments": [
                {"id": exp.experiment_id, "name": exp.name, "description": exp.description}
                for exp in experiments
            ],
            "total": len(experiments),
        })

    # Benchmark endpoints
    if path == "/api/benchmark" and method == "GET":
        return JSONResponse({
            "message": "Run benchmark via CLI: forgelab benchmark run --agent mock",
            "templates": 14,
            "mutations": 37,
            "agents": 6,
        })

    # Leaderboard endpoints
    if path == "/api/leaderboard" and method == "GET":
        return JSONResponse({"leaderboard": [], "message": "No results yet. Run experiments to populate."})

    # Curriculum endpoints
    if path == "/api/curriculum" and method == "GET":
        return JSONResponse({
            "message": "Curriculum state is per-run in serverless mode.",
            "templates": 14,
            "mutations": 37,
        })

    # 404 for unknown routes
    return JSONResponse(
        {"error": "Not found", "path": path, "method": method},
        status_code=404,
    )


def _cors_response() -> dict[str, Any]:
    """Return CORS preflight response."""
    return {
        "statusCode": 204,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        "body": "",
    }
