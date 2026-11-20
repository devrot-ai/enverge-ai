"""Vercel serverless handler for ForgeLab.

This is a lightweight FastAPI app that runs on Vercel's serverless Python runtime.
It imports forge modules lazily to avoid cold-start failures.
"""

import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel

# Vercel environment setup
os.environ.setdefault("FORGELAB_DATABASE_URL", "sqlite:///tmp/forgelab.db")
os.environ.setdefault("FORGELAB_ENV", "vercel")

app = FastAPI(
    title="ForgeLab",
    description="Adaptive environment factory for autonomous software engineering agents.",
    version="0.9.0",
)

# Allow the Next.js frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WorldGenerateRequest(BaseModel):
    template_name: str = "task_manager_api"
    mutation_id: Optional[str] = None


class TaskGenerateRequest(BaseModel):
    world_id: str


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.9.0",
        "environment": os.environ.get("FORGELAB_ENV", "unknown"),
    }


@app.get("/api/v1/root", response_class=JSONResponse)
async def root():
    """Root API endpoint."""
    return {
        "name": "ForgeLab",
        "version": "0.9.0",
        "description": "Adaptive environment factory for autonomous software engineering agents.",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/v1/templates")
async def list_templates_endpoint():
    """List all available environment templates."""
    try:
        from forge.world_factory.templates import list_templates
        templates = list_templates()
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/mutations")
async def list_mutations_endpoint():
    """List all available bug mutations."""
    try:
        from forge.world_factory.seeder import list_mutations, get_mutation

        mutation_ids = list_mutations()
        mutations = []
        for mid in mutation_ids:
            m = get_mutation(mid)
            if m:
                mutations.append({
                    "mutation_id": m.get("id", mid),
                    "name": m.get("name", ""),
                    "description": m.get("description", ""),
                    "capabilities": m.get("capabilities", []),
                    "difficulty": m.get("difficulty", 1),
                })
        return {"mutations": mutations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Mapping of templates to their compatible mutations for auto-selection
TEMPLATE_MUTATIONS = {
    "task_manager_api": ["pagination_boundary", "search_injection", "null_filter"],
    "data_pipeline": ["null_handling", "date_parsing", "duplicate_detection"],
    "flask_app": ["session_timeout", "password_hash", "csrf_token"],
    "express_api": ["cors_bypass", "rate_limit_off", "input_injection"],
    "django_app": ["sql_injection", "csrf_missing", "open_redirect"],
    "typescript_api": ["error_leak", "input_validation"],
    "go_service": ["nil_pointer", "resource_leak"],
    "react_app": ["state_race", "memory_leak", "xss_injection"],
    "spring_service": ["transaction_leak", "n_plus_one", "validation_bypass"],
    "config_manager": ["env_override", "secret_exposure", "merge_conflict"],
    "browser_automation": ["xss_reflected", "clickjacking", "auth_bypass"],
    "database_query": ["sql_injection", "n_plus_one_query", "missing_index"],
    "api_integration": ["rate_limit_bypass", "auth_token_leak", "schema_mismatch"],
    "dsl": ["syntax_error", "type_coercion", "undefined_reference"],
}


@app.post("/api/v1/worlds/generate")
async def generate_world(req: WorldGenerateRequest):
    """Generate a new world from a template with a bug mutation.

    Accepts JSON body:
    {
        "template_name": "task_manager_api",
        "mutation_id": "pagination_boundary"  # optional, auto-selects if null
    }
    """
    try:
        from forge.world_factory.generator import WorldGenerator
        from forge.world_factory.seeder import get_mutation

        template_name = req.template_name
        mutation_id = req.mutation_id

        # Auto-select a mutation if not provided
        if not mutation_id:
            compatible = TEMPLATE_MUTATIONS.get(template_name, [])
            if compatible:
                mutation_id = compatible[0]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"No mutation available for template: {template_name}",
                )

        # Verify mutation exists
        mutation = get_mutation(mutation_id)
        if not mutation:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown mutation: {mutation_id}",
            )

        world_gen = WorldGenerator(output_dir=tempfile.mkdtemp())
        spec = world_gen.generate(
            template_name=template_name,
            mutation_id=mutation_id,
            seed=int(uuid.uuid4().node) % 10000,
        )

        return {
            "world_id": spec.world_id,
            "template": spec.template_name,
            "mutation": spec.mutation_id,
            "seed": spec.seed,
            "capabilities": spec.metadata.get("capabilities", []),
            "description": spec.metadata.get("description", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tasks/generate")
async def generate_task(req: TaskGenerateRequest):
    """Generate a task from a world.

    Accepts JSON body:
    {
        "world_id": "world-42-task_manager_api-pagination_boundary"
    }
    """
    try:
        from forge.task_factory.generator import TaskGenerator

        task_gen = TaskGenerator()
        task_spec = task_gen.generate_from_world_id(req.world_id)

        return {
            "task_id": task_spec.task_id,
            "world_id": task_spec.world_id,
            "description": task_spec.description,
            "difficulty": task_spec.difficulty_level,
            "category": task_spec.category.value if hasattr(task_spec.category, 'value') else str(task_spec.category),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/experiments")
async def list_experiments():
    """List all preset experiments."""
    return {
        "experiments": [
            {"id": "A", "name": "Static vs Adaptive Curriculum", "description": "Compare static task selection vs adaptive curriculum."},
            {"id": "B", "name": "Random vs Validated Environments", "description": "Compare randomly generated vs validated environments."},
            {"id": "C", "name": "Generic vs Targeted Challenges", "description": "Compare generic tasks vs targeted skill-building tasks."},
            {"id": "D", "name": "Single-agent vs Independent Verification", "description": "Compare single-agent verification vs independent test execution."},
            {"id": "ablation_tools", "name": "Tool Ablation Study", "description": "Measure impact of removing tools one by one."},
            {"id": "difficulty_scaling", "name": "Difficulty Scaling", "description": "Measure agent performance across difficulty levels."},
            {"id": "cross_template", "name": "Cross-Template Generalization", "description": "Run same agent across all templates."},
        ]
    }


@app.get("/api/v1/benchmark")
async def benchmark_info():
    """Get benchmark information."""
    return {
        "templates": 14,
        "mutations": 37,
        "agents": 6,
        "tests": 645,
        "description": "ForgeLab benchmark suite with 14 templates and 37 mutations.",
    }


@app.get("/api/v1/docs")
async def api_docs():
    """Get API documentation."""
    return {
        "endpoints": [
            {"path": "/health", "method": "GET", "description": "Health check"},
            {"path": "/", "method": "GET", "description": "Landing page"},
            {"path": "/api/v1/templates", "method": "GET", "description": "List templates"},
            {"path": "/api/v1/mutations", "method": "GET", "description": "List mutations"},
            {"path": "/api/v1/worlds/generate", "method": "POST", "description": "Generate world"},
            {"path": "/api/v1/experiments", "method": "GET", "description": "List experiments"},
            {"path": "/api/v1/benchmark", "method": "GET", "description": "Benchmark info"},
        ]
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch-all for unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )
