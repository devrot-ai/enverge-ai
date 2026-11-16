"""FastAPI application for ForgeLab.

Provides REST API endpoints for worlds, tasks, runs, curriculum,
experiments, and metrics.  Long-running agent executions are handled
as background tasks so the API doesn't block.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from forge.agents.mock_agent import MockAgent
from forge.core.schemas import (
    RunConfig,
    RunStatus,
    TaskSpec,
    WorldSpec,
)
from forge.curriculum.selector import CurriculumSelector
from forge.db.models import (
    CurriculumRecord,
    ExperimentRecord,
    RunRecord,
    TaskRecord,
    WorldRecord,
    get_session,
    init_db,
)
from forge.diagnosis.classifier import FailureClassifier
from forge.experiments.manager import ExperimentConfig, ExperimentManager
from forge.runner.orchestrator import RunOrchestrator
from forge.task_factory.generator import TaskGenerator
from forge.validators.world_validator import TaskValidator, WorldValidator
from forge.world_factory.generator import WorldGenerator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App state
# ---------------------------------------------------------------------------

DB_PATH = os.environ.get("FORGELAB_DB", "forgelab.db")
BASE_DIR = Path(os.environ.get("FORGELAB_BASE_DIR", str(Path.cwd())))

# Initialize database
init_db(str(BASE_DIR / DB_PATH))

# Component instances
world_generator = WorldGenerator(output_dir=str(BASE_DIR / "worlds"))
task_generator = TaskGenerator()
world_validator = WorldValidator()
task_validator = TaskValidator()
orchestrator = RunOrchestrator(artifacts_dir=str(BASE_DIR / "runs"))
classifier = FailureClassifier()
curriculum_selector = CurriculumSelector()
experiment_manager = ExperimentManager()

app = FastAPI(
    title="ForgeLab",
    description="Adaptive environment factory for autonomous software engineering agents.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# Worlds
# ---------------------------------------------------------------------------


@app.get("/api/v1/worlds")
async def list_worlds():
    """List all generated worlds."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        records = session.query(WorldRecord).all()
        return [r.to_dict() for r in records]
    finally:
        session.close()


@app.post("/api/v1/worlds/generate")
async def generate_world(
    template_name: str = "task_manager_api",
    mutation_id: str = "pagination_boundary",
    seed: int | None = None,
):
    """Generate a new world from a template with a bug mutation."""
    try:
        spec = world_generator.generate(
            template_name=template_name,
            mutation_id=mutation_id,
            seed=seed or int(uuid.uuid4().node) % 10000,
        )
        # Store in database
        session = get_session(str(BASE_DIR / DB_PATH))
        try:
            record = WorldRecord(
                world_id=spec.world_id,
                world_type=spec.world_type,
                template_name=spec.template_name,
                template_version=spec.template_version,
                mutation_id=spec.mutation_id,
                seed=spec.seed,
                world_dir=spec.metadata.get("world_dir", ""),
                initial_commit=spec.metadata.get("initial_commit", ""),
                manifest=json.dumps(spec.metadata.get("manifest", {})),
                metadata_json=json.dumps(spec.metadata),
            )
            session.add(record)
            session.commit()
        finally:
            session.close()
        return spec.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/worlds/{world_id}")
async def get_world(world_id: str):
    """Get a world by ID."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        record = session.query(WorldRecord).filter_by(world_id=world_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"World {world_id} not found")
        return record.to_dict()
    finally:
        session.close()


@app.post("/api/v1/worlds/{world_id}/validate")
async def validate_world(world_id: str):
    """Validate a generated world."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        record = session.query(WorldRecord).filter_by(world_id=world_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"World {world_id} not found")
        world_spec = WorldSpec(
            world_id=record.world_id,
            world_type=record.world_type,
            template_name=record.template_name,
            template_version=record.template_version,
            mutation_id=record.mutation_id,
            seed=record.seed,
            metadata={"world_dir": record.world_dir},
        )
        status, issues = world_validator.validate(world_spec)
        return {"status": status.value, "issues": issues, "valid": status.value == "valid"}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@app.get("/api/v1/tasks")
async def list_tasks(validated_only: bool = Query(False, description="Only return validated tasks")):
    """List all tasks."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        query = session.query(TaskRecord)
        if validated_only:
            query = query.filter_by(validated=1)
        records = query.all()
        return [r.to_dict() for r in records]
    finally:
        session.close()


@app.post("/api/v1/tasks/generate")
async def generate_task(
    world_id: str,
    task_id: str | None = None,
):
    """Generate a task for a world."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        world_record = session.query(WorldRecord).filter_by(world_id=world_id).first()
        if not world_record:
            raise HTTPException(status_code=404, detail=f"World {world_id} not found")
        # Build WorldSpec from record
        world_spec = WorldSpec(
            world_id=world_id,
            world_type=world_record.world_type,
            template_name=world_record.template_name,
            template_version=world_record.template_version,
            mutation_id=world_record.mutation_id,
            seed=world_record.seed,
            metadata={"world_dir": world_record.world_dir},
        )
        task = task_generator.generate_from_world(world_spec, task_id=task_id)
        # Store in database
        record = TaskRecord(
            task_id=task.task_id,
            world_id=task.world_id,
            schema_version=task.schema_version,
            category=task.category.value if hasattr(task.category, "value") else str(task.category),
            description=task.description,
            constraints_json=json.dumps(task.constraints),
            verification_method=task.verification_method,
            difficulty_level=task.difficulty_level,
            capabilities_json=json.dumps(task.capabilities),
            metadata_json=json.dumps(task.to_dict()),
        )
        session.add(record)
        session.commit()
        return task.to_dict()
    finally:
        session.close()


@app.get("/api/v1/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a task by ID."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        record = session.query(TaskRecord).filter_by(task_id=task_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return record.to_dict()
    finally:
        session.close()


@app.post("/api/v1/tasks/{task_id}/validate")
async def validate_task(task_id: str):
    """Validate a task specification."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        task_record = session.query(TaskRecord).filter_by(task_id=task_id).first()
        if not task_record:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        world_record = session.query(WorldRecord).filter_by(world_id=task_record.world_id).first()
        if not world_record:
            raise HTTPException(status_code=404, detail=f"World {task_record.world_id} not found")
        # Reconstruct objects
        task_data = json.loads(task_record.metadata_json) if task_record.metadata_json else {}
        task = TaskSpec.from_dict(task_data)
        world_spec = WorldSpec(
            world_id=world_record.world_id,
            world_type=world_record.world_type,
            template_name=world_record.template_name,
            template_version=world_record.template_version,
            mutation_id=world_record.mutation_id,
            seed=world_record.seed,
            metadata={"world_dir": world_record.world_dir},
        )
        status, issues = task_validator.validate(task, world_spec)
        result = {"status": status.value, "issues": issues, "valid": status.value == "valid"}
        if result["valid"]:
            task_record.validated = 1
            task_record.validation_notes = json.dumps(result)
            session.commit()
        return result
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


@app.get("/api/v1/agents")
async def list_agents():
    """List available agents."""
    return [
        {"agent_id": "mock-success", "name": "MockAgent (Success)", "type": "mock", "scenario": "success"},
        {"agent_id": "mock-partial", "name": "MockAgent (Partial)", "type": "mock", "scenario": "partial"},
        {"agent_id": "mock-failure", "name": "MockAgent (Failure)", "type": "mock", "scenario": "failure"},
        {"agent_id": "mock-no-change", "name": "MockAgent (No Change)", "type": "mock", "scenario": "no_change"},
    ]


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


@app.post("/api/v1/runs")
async def create_run(
    task_id: str,
    agent_id: str = "mock-success",
    experiment_id: str | None = None,
    background_tasks: BackgroundTasks = None,
):
    """Create and start a new agent run."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        task_record = session.query(TaskRecord).filter_by(task_id=task_id).first()
        if not task_record:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        world_record = session.query(WorldRecord).filter_by(world_id=task_record.world_id).first()
        if not world_record:
            raise HTTPException(status_code=404, detail=f"World {task_record.world_id} not found")
    finally:
        session.close()

    # Create run ID
    run_id = f"run-{uuid.uuid4().hex[:12]}"

    # Determine agent scenario
    scenario = "success"
    if "partial" in agent_id:
        scenario = "partial"
    elif "failure" in agent_id:
        scenario = "failure"
    elif "no-change" in agent_id or "no_change" in agent_id:
        scenario = "no_change"

    # Build objects
    world_spec = WorldSpec(
        world_id=world_record.world_id,
        world_type=world_record.world_type,
        template_name=world_record.template_name,
        template_version=world_record.template_version,
        mutation_id=world_record.mutation_id,
        seed=world_record.seed,
        metadata={"world_dir": world_record.world_dir},
    )
    task_data = json.loads(task_record.metadata_json) if task_record.metadata_json else {}
    task_spec = TaskSpec.from_dict(task_data)
    agent = MockAgent(scenario=scenario)
    run_config = RunConfig(
        run_id=run_id,
        task_id=task_id,
        agent_id=agent_id,
        experiment_id=experiment_id,
    )

    # Store pending run
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        record = RunRecord(
            run_id=run_id,
            task_id=task_id,
            agent_id=agent_id,
            experiment_id=experiment_id,
            status="running",
            started_at=datetime.utcnow(),
        )
        session.add(record)
        session.commit()
    finally:
        session.close()

    # Run in background
    if background_tasks:
        background_tasks.add_task(_execute_run, run_id, task_spec, world_spec, agent, run_config)
    else:
        # Synchronous execution for testing
        _execute_run(run_id, task_spec, world_spec, agent, run_config)

    return {"run_id": run_id, "status": "running"}


def _execute_run(run_id: str, task_spec: TaskSpec, world_spec: WorldSpec, agent: MockAgent, run_config: RunConfig):
    """Execute a run and store the result."""
    try:
        result = orchestrator.run(task_spec, world_spec, agent, run_config)

        # Store result
        session = get_session(str(BASE_DIR / DB_PATH))
        try:
            record = session.query(RunRecord).filter_by(run_id=run_id).first()
            if record:
                record.status = result.status.value if isinstance(result.status, RunStatus) else result.status
                record.trajectory_json = json.dumps(result.trajectory.to_dict()) if result.trajectory else None
                record.verification_json = json.dumps(result.verification.to_dict()) if result.verification else None
                record.diagnosis_json = json.dumps(result.diagnosis.to_dict()) if result.diagnosis else None
                record.finished_at = datetime.utcnow()
                record.duration_seconds = result.duration_seconds
                record.agent_believes_success = 1 if result.agent_believes_success else 0
                record.passed = 1 if result.passed else 0
                record.error = result.error
                record.step_count = result.step_count
                record.metadata_json = json.dumps(result.metadata)
                session.commit()
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Run {run_id} failed: {e}")
        session = get_session(str(BASE_DIR / DB_PATH))
        try:
            record = session.query(RunRecord).filter_by(run_id=run_id).first()
            if record:
                record.status = "failed"
                record.error = str(e)
                record.finished_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()


@app.get("/api/v1/runs")
async def list_runs(
    status: str | None = None,
    agent_id: str | None = None,
    limit: int = Query(50, ge=1, le=500),
):
    """List all runs with optional filters."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        query = session.query(RunRecord)
        if status:
            query = query.filter_by(status=status)
        if agent_id:
            query = query.filter_by(agent_id=agent_id)
        records = query.order_by(RunRecord.started_at.desc()).limit(limit).all()
        return [r.to_dict() for r in records]
    finally:
        session.close()


@app.get("/api/v1/runs/{run_id}")
async def get_run(run_id: str):
    """Get a run by ID."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        record = session.query(RunRecord).filter_by(run_id=run_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return record.to_dict()
    finally:
        session.close()


@app.get("/api/v1/runs/{run_id}/trajectory")
async def get_trajectory(run_id: str):
    """Get the trajectory for a run."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        record = session.query(RunRecord).filter_by(run_id=run_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        if not record.trajectory_json:
            raise HTTPException(status_code=404, detail="No trajectory found")
        return json.loads(record.trajectory_json)
    finally:
        session.close()


@app.get("/api/v1/runs/{run_id}/diagnosis")
async def get_diagnosis(run_id: str):
    """Get the failure diagnosis for a run."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        record = session.query(RunRecord).filter_by(run_id=run_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        if not record.diagnosis_json:
            raise HTTPException(status_code=404, detail="No diagnosis found")
        return json.loads(record.diagnosis_json)
    finally:
        session.close()


@app.get("/api/v1/runs/{run_id}/verification")
async def get_verification(run_id: str):
    """Get the verification result for a run."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        record = session.query(RunRecord).filter_by(run_id=run_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        if not record.verification_json:
            raise HTTPException(status_code=404, detail="No verification found")
        return json.loads(record.verification_json)
    finally:
        session.close()


@app.get("/api/v1/runs/{run_id}/status")
async def get_run_status(run_id: str):
    """Get the current status of a run for real-time polling.

    Returns minimal status info suitable for frequent polling.
    """
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        record = session.query(RunRecord).filter_by(run_id=run_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return {
            "run_id": record.run_id,
            "status": record.status,
            "passed": bool(record.passed) if record.status in ("completed", "failed") else None,
            "step_count": record.step_count,
            "duration_seconds": record.duration_seconds,
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "finished_at": record.finished_at.isoformat() if record.finished_at else None,
        }
    finally:
        session.close()


@app.get("/api/v1/runs/{run_id}/diff")
async def get_run_diff(run_id: str):
    """Get the code diff for a run, showing agent workspace changes.

    Compares the original world code with the agent's modified workspace.
    """
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        record = session.query(RunRecord).filter_by(run_id=run_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        # Get trajectory to extract file changes
        if not record.trajectory_json:
            return {"files": [], "total_added": 0, "total_removed": 0, "files_changed": 0}

        trajectory = json.loads(record.trajectory_json)
        steps = trajectory.get("steps", [])

        # Extract file reads and writes from trajectory
        file_states: dict[str, dict[str, str]] = {}  # filename -> {original, modified}
        for step in steps:
            tool = step.get("tool_name", "")
            args = step.get("tool_arguments", {})
            result = step.get("tool_result", "")

            if tool == "read_file" and args.get("file_path"):
                fname = args["file_path"]
                if fname not in file_states:
                    file_states[fname] = {}
                if "original" not in file_states[fname] and isinstance(result, str):
                    file_states[fname]["original"] = result

            elif tool == "write_file" and args.get("file_path"):
                fname = args["file_path"]
                content = args.get("content", "")
                if fname not in file_states:
                    file_states[fname] = {}
                file_states[fname]["modified"] = content

        # Compute diffs
        from forge.evaluation.diff_viewer import DiffViewer

        viewer = DiffViewer()
        files_diff = []
        total_added = 0
        total_removed = 0
        files_changed = 0

        for fname, states in file_states.items():
            original = states.get("original", "")
            modified = states.get("modified", "")
            if original and modified and original != modified:
                file_diff = viewer.diff_content(fname, original, modified)
                if file_diff.changed:
                    files_changed += 1
                    total_added += file_diff.added_count
                    total_removed += file_diff.removed_count
                    files_diff.append(
                        {
                            "filename": file_diff.filename,
                            "added": file_diff.added_count,
                            "removed": file_diff.removed_count,
                            "hunks": [
                                {
                                    "added_lines": h.added_lines,
                                    "removed_lines": h.removed_lines,
                                    "start_line": h.start_line,
                                }
                                for h in file_diff.hunks
                            ],
                        }
                    )

        return {
            "files": files_diff,
            "total_added": total_added,
            "total_removed": total_removed,
            "files_changed": files_changed,
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Curriculum
# ---------------------------------------------------------------------------


@app.get("/api/v1/curriculum")
async def get_curriculum():
    """Get the current curriculum state."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        records = session.query(CurriculumRecord).order_by(CurriculumRecord.updated_at.desc()).all()
        if not records:
            return {
                "curriculum_id": "default",
                "strategy": "static",
                "capability_scores": {},
                "task_pool": [],
                "selected_tasks": [],
                "generation": 0,
            }
        return records[0].to_dict()
    finally:
        session.close()


@app.get("/api/v1/curriculum/history")
async def get_curriculum_history(limit: int = Query(50, ge=1, le=500)):
    """Get curriculum history."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        records = session.query(CurriculumRecord).order_by(CurriculumRecord.updated_at.desc()).limit(limit).all()
        return [r.to_dict() for r in records]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------


@app.post("/api/v1/experiments")
async def create_experiment(
    name: str,
    description: str = "",
    hypothesis: str = "",
    config: dict[str, Any] | None = None,
):
    """Create a new experiment."""
    exp_id = f"exp-{uuid.uuid4().hex[:12]}"
    exp_config = ExperimentConfig(
        experiment_id=exp_id,
        name=name,
        description=description,
        hypothesis=hypothesis,
        metadata=config or {},
    )
    experiment_manager.create_experiment(exp_config)
    # Store in database
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        record = ExperimentRecord(
            experiment_id=exp_id,
            name=name,
            description=description,
            hypothesis=hypothesis,
            config_json=json.dumps(config or {}),
            started_at=datetime.utcnow(),
        )
        session.add(record)
        session.commit()
    finally:
        session.close()
    return {"experiment_id": exp_id, "name": name, "status": "created"}


@app.get("/api/v1/experiments")
async def list_experiments():
    """List all experiments."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        records = session.query(ExperimentRecord).all()
        return [r.to_dict() for r in records]
    finally:
        session.close()


@app.get("/api/v1/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get an experiment by ID."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        record = session.query(ExperimentRecord).filter_by(experiment_id=experiment_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
        return record.to_dict()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@app.get("/api/v1/metrics/overview")
async def get_metrics_overview():
    """Get overview metrics."""
    session = get_session(str(BASE_DIR / DB_PATH))
    try:
        total_worlds = session.query(WorldRecord).count()
        total_tasks = session.query(TaskRecord).count()
        validated_tasks = session.query(TaskRecord).filter_by(validated=1).count()
        total_runs = session.query(RunRecord).count()
        completed_runs = session.query(RunRecord).filter_by(status="completed").count()
        passed_runs = session.query(RunRecord).filter_by(passed=1).count()
        failed_runs = session.query(RunRecord).filter_by(status="failed").count()

        # Failure category breakdown
        diagnoses: list[dict[str, Any]] = []
        for run in session.query(RunRecord).filter(RunRecord.diagnosis_json.isnot(None)).all():
            if run.diagnosis_json:
                diag = json.loads(run.diagnosis_json)
                diagnoses.append(diag)

        category_counts: dict[str, int] = {}
        for diag in diagnoses:
            cat = diag.get("primary_category", "unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        success_rate = passed_runs / total_runs if total_runs > 0 else 0.0

        return {
            "total_worlds": total_worlds,
            "total_tasks": total_tasks,
            "validated_tasks": validated_tasks,
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "passed_runs": passed_runs,
            "failed_runs": failed_runs,
            "success_rate": round(success_rate, 3),
            "failure_categories": category_counts,
            "invalid_task_rate": (
                round(category_counts.get("invalid_task", 0) / total_runs, 3) if total_runs > 0 else 0.0
            ),
            "environment_failure_rate": (
                round(category_counts.get("environment_failure", 0) / total_runs, 3) if total_runs > 0 else 0.0
            ),
            "verifier_failure_rate": (
                round(category_counts.get("verifier_failure", 0) / total_runs, 3) if total_runs > 0 else 0.0
            ),
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
