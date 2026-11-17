"""Vercel serverless handler for ForgeLab.

This is a lightweight FastAPI app that runs on Vercel's serverless Python runtime.
It imports forge modules lazily to avoid cold-start failures.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse

# Vercel environment setup
os.environ.setdefault("FORGELAB_DATABASE_URL", "sqlite:///tmp/forgelab.db")
os.environ.setdefault("FORGELAB_ENV", "vercel")

app = FastAPI(
    title="ForgeLab",
    description="Adaptive environment factory for autonomous software engineering agents.",
    version="0.9.0",
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.9.0",
        "environment": os.environ.get("FORGELAB_ENV", "unknown"),
    }


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the landing page."""
    public_index = Path(__file__).parent.parent / "public" / "index.html"
    if public_index.exists():
        try:
            content = public_index.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = public_index.read_text(encoding="latin-1")
        return HTMLResponse(content=content)
    return HTMLResponse(
        content="""
        <html><head><title>ForgeLab API</title></head>
        <body><h1>ForgeLab</h1>
        <p>API is running. Visit <a href="/health">/health</a> or <a href="/docs">/docs</a>.</p>
        </body></html>
        """
    )


@app.get("/api/v1/templates")
async def list_templates():
    """List all available environment templates."""
    try:
        from forge.world_factory.templates import list_templates
        return list_templates()
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
                mutations.append(m)
        return mutations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/worlds/generate")
async def generate_world():
    """Generate a new world from a template with a bug mutation.

    Accepts JSON body:
    {
        "template_name": "task_manager_api",
        "mutation_id": "pagination_boundary",
        "seed": 42
    }
    """
    try:
        from forge.world_factory.generator import WorldGenerator
        from forge.world_factory.seeder import get_mutation

        import tempfile

        template_name = "task_manager_api"
        mutation_id = "pagination_boundary"
        seed = None

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
            seed=seed or int(uuid.uuid4().node) % 10000,
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


@app.get("/api/v1/experiments")
async def list_experiments():
    """List all preset experiments."""
    return [
        {"id": "A", "name": "Static vs Adaptive Curriculum", "description": "Compare static task selection vs adaptive curriculum."},
        {"id": "B", "name": "Random vs Validated Environments", "description": "Compare randomly generated vs validated environments."},
        {"id": "C", "name": "Generic vs Targeted Challenges", "description": "Compare generic tasks vs targeted skill-building tasks."},
        {"id": "D", "name": "Single-agent vs Independent Verification", "description": "Compare single-agent verification vs independent test execution."},
        {"id": "ablation_tools", "name": "Tool Ablation Study", "description": "Measure impact of removing tools one by one."},
        {"id": "difficulty_scaling", "name": "Difficulty Scaling", "description": "Measure agent performance across difficulty levels."},
        {"id": "cross_template", "name": "Cross-Template Generalization", "description": "Run same agent across all templates."},
    ]


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
