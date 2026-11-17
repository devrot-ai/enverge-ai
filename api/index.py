"""Vercel serverless function entry point for ForgeLab.

This is a self-contained handler that doesn't import forge at module level,
avoiding cold-start failures on Vercel. All forge imports are lazy.
"""

import json
import os
import sys
import tempfile

# Add project root to path so `import forge` works
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Set environment for Vercel
os.environ.setdefault("FORGELAB_ENV", "vercel")
os.environ.setdefault("FORGELAB_DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/forgelab.db")


HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
}


def handler(event, context):
    """Vercel serverless function handler."""
    method = event.get("httpMethod", "GET")
    path = event.get("path", "/")

    # CORS preflight
    if method == "OPTIONS":
        return _cors_response()

    try:
        body = _parse_body(event.get("body"))
    except Exception as e:
        return _json_response({"error": f"Invalid JSON: {e}"}, 400)

    # Route requests
    if path == "/api/health" and method == "GET":
        return _health()
    elif path == "/api/templates" and method == "GET":
        return _templates()
    elif path == "/api/mutations" and method == "GET":
        return _mutations()
    elif path == "/api/worlds/generate" and method == "POST":
        return _generate_world(body)
    elif path == "/api/tasks/generate" and method == "POST":
        return _generate_task(body)
    elif path == "/api/experiments" and method == "GET":
        return _experiments()
    elif path == "/api/benchmark" and method == "GET":
        return _benchmark()
    elif path == "/api/leaderboard" and method == "GET":
        return _leaderboard()
    elif path == "/api/curriculum" and method == "GET":
        return _curriculum()
    elif path == "/api/docs" and method == "GET":
        return _docs()
    else:
        return _json_response({"error": "Not found", "path": path}, 404)


def _parse_body(raw):
    """Parse JSON body from Vercel event."""
    if raw is None:
        return {}
    if isinstance(raw, str):
        return json.loads(raw) if raw.strip() else {}
    return raw


def _json_response(data, status=200):
    """Return a JSON response dict."""
    return {
        "statusCode": status,
        "headers": HEADERS,
        "body": json.dumps(data),
    }


def _cors_response():
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


# --- Endpoint handlers ---

def _health():
    return _json_response({
        "status": "ok",
        "environment": "vercel",
        "version": "0.9",
        "templates": 14,
        "mutations": 37,
        "agents": 6,
        "tests": 645,
    })


def _templates():
    """List available templates with lazy import."""
    try:
        from forge.world_factory.templates import list_templates
        templates = list_templates()
        return _json_response({"templates": templates, "total": len(templates)})
    except Exception as e:
        return _json_response({"error": str(e)}, 500)


def _mutations():
    """List available mutations with lazy import."""
    try:
        from forge.world_factory.seeder import list_mutations
        mutations = list_mutations()
        return _json_response({"mutations": mutations, "total": len(mutations)})
    except Exception as e:
        return _json_response({"error": str(e)}, 500)


def _generate_world(body):
    """Generate a world from template + mutation."""
    template = body.get("template", "task_manager_api")
    mutation = body.get("mutation")
    try:
        from forge.world_factory.generator import WorldGenerator
        generator = WorldGenerator()
        # Auto-select a known mutation for the template
        if not mutation:
            mutation_map = {
                "task_manager_api": "pagination_boundary",
                "data_pipeline": "null_handling",
                "flask_app": "session_timeout",
                "express_api": "cors_bypass",
                "django_app": "sql_injection",
                "typescript_api": "error_leak",
                "go_service": "nil_pointer",
                "react_app": "xss_injection",
                "spring_service": "transaction_leak",
                "config_manager": "env_override",
                "browser_automation": "clickjacking",
                "database_query": "n_plus_one_query",
                "api_integration": "rate_limit_bypass",
                "dsl": "syntax_error",
            }
            mutation = mutation_map.get(template, "pagination_boundary")
        world = generator.generate(template_name=template, mutation_id=mutation)
        return _json_response({
            "world_id": world.world_id,
            "template": world.template_name,
            "mutation": world.mutation_id,
            "status": "generated",
        })
    except Exception as e:
        return _json_response({"error": str(e)}, 500)


def _generate_task(body):
    """Generate a task from a world."""
    world_id = body.get("world_id", "")
    try:
        from forge.task_factory.generator import TaskGenerator
        generator = TaskGenerator()
        task = generator.generate_from_world(world_id=world_id)
        return _json_response({
            "task_id": task.task_id,
            "world_id": task.world_id,
            "status": "generated",
        })
    except Exception as e:
        return _json_response({"error": str(e)}, 500)


def _experiments():
    """List preset experiments."""
    try:
        from forge.experiments.manager import ExperimentManager
        em = ExperimentManager()
        experiments = em.list_experiments()
        exp_list = []
        for exp in experiments:
            if isinstance(exp, dict):
                exp_list.append(exp)
            elif hasattr(exp, 'to_dict'):
                exp_list.append(exp.to_dict())
            elif hasattr(exp, 'experiment_id'):
                exp_list.append({
                    "id": exp.experiment_id,
                    "name": getattr(exp, 'name', ''),
                    "description": getattr(exp, 'description', ''),
                })
        return _json_response({"experiments": exp_list, "total": len(exp_list)})
    except Exception as e:
        return _json_response({"experiments": [], "total": 0, "note": str(e)})


def _benchmark():
    return _json_response({
        "message": "Run benchmark via CLI: forgelab benchmark run --agent mock",
        "templates": 14,
        "mutations": 37,
        "agents": 6,
    })


def _leaderboard():
    return _json_response({"leaderboard": [], "message": "Run experiments to populate."})


def _curriculum():
    return _json_response({
        "message": "Curriculum state is per-run in serverless mode.",
        "templates": 14,
        "mutations": 37,
    })


def _docs():
    return _json_response({
        "name": "ForgeLab API",
        "version": "0.9",
        "endpoints": [
            "GET  /api/health          - Health check",
            "GET  /api/templates       - List templates",
            "GET  /api/mutations       - List mutations",
            "POST /api/worlds/generate - Generate world",
            "POST /api/tasks/generate  - Generate task",
            "GET  /api/experiments     - List experiments",
            "GET  /api/benchmark       - Benchmark info",
            "GET  /api/leaderboard     - Leaderboard",
            "GET  /api/curriculum      - Curriculum state",
        ],
    })
