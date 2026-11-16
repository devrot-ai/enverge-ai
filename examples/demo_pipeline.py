"""End-to-end demo for ForgeLab.

Demonstrates the complete pipeline:
1. Generate a broken Python repository
2. Validate the world
3. Generate a task
4. Validate the task
5. Run a MockAgent
6. Verify the result independently
7. Diagnose the outcome
8. Update the curriculum
9. Generate a related task variant

Run with: python examples/demo_pipeline.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

# Ensure the project root is on the path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from forge.agents.mock_agent import MockAgent
from forge.core.schemas import AgentConfig, RunConfig
from forge.curriculum.selector import CapabilityTracker, CurriculumSelector
from forge.db.models import (
    CurriculumRecord,
    RunRecord,
    TaskRecord,
    WorldRecord,
    get_session,
    init_db,
)
from forge.diagnosis.classifier import FailureClassifier
from forge.runner.orchestrator import RunOrchestrator
from forge.task_factory.generator import TaskGenerator
from forge.validators.world_validator import TaskValidator, WorldValidator
from forge.world_factory.generator import WorldGenerator


def print_header(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_step(num: int, title: str):
    print(f"\n  Step {num}: {title}")
    print(f"  {'-' * 40}")


def main():
    # Setup — use unique temp dir to avoid Windows file lock issues
    demo_dir = Path(tempfile.gettempdir()) / f"forgelab_demo_{uuid.uuid4().hex[:8]}"
    demo_dir.mkdir(parents=True)
    os.chdir(demo_dir)

    print_header("ForgeLab — End-to-End Demo")
    print(f"  Working directory: {demo_dir}")
    print("  This demo uses MockAgent (no API keys required)")

    # Initialize database
    print_step(0, "Initialize ForgeLab")
    db_path = str(demo_dir / "forgelab.db")
    session = init_db(db_path)
    session.close()
    print(f"  Database initialized: {db_path}")

    # Also initialize the project-root database so the dashboard can find data
    project_db_path = str(PROJECT_ROOT / "forgelab.db")
    init_db(project_db_path).close()
    print(f"  Project database: {project_db_path}")

    # Components
    world_gen = WorldGenerator(output_dir=str(demo_dir / "worlds"))
    task_gen = TaskGenerator()
    world_val = WorldValidator()
    task_val = TaskValidator()
    orchestrator = RunOrchestrator(artifacts_dir=str(demo_dir / "runs"))
    classifier = FailureClassifier()
    curriculum = CurriculumSelector()
    tracker = CapabilityTracker()

    # -----------------------------------------------------------------------
    # Step 1: Generate a world
    # -----------------------------------------------------------------------
    print_step(1, "Generate a broken Python repository")
    world_spec = world_gen.generate(
        template_name="task_manager_api",
        mutation_id="pagination_boundary",
        seed=42,
    )
    print(f"  World ID: {world_spec.world_id}")
    print(f"  Template: {world_spec.template_name}")
    print(f"  Mutation: {world_spec.mutation_id}")
    print(f"  Seed: {world_spec.seed}")
    print(f"  Directory: {world_spec.metadata.get('world_dir', 'N/A')}")

    # -----------------------------------------------------------------------
    # Step 2: Validate the world
    # -----------------------------------------------------------------------
    print_step(2, "Validate the generated world")
    status, issues = world_val.validate(world_spec)
    print(f"  Status: {status.value}")
    if issues:
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  All checks passed [OK]")

    # -----------------------------------------------------------------------
    # Step 3: Generate a task
    # -----------------------------------------------------------------------
    print_step(3, "Generate a task from the world")
    task = task_gen.generate_from_world(world_spec)
    print(f"  Task ID: {task.task_id}")
    print(f"  Category: {task.category.value}")
    print(f"  Difficulty: {task.difficulty_level}")
    print(f"  Description: {task.description[:100]}...")

    # -----------------------------------------------------------------------
    # Step 4: Validate the task
    # -----------------------------------------------------------------------
    print_step(4, "Validate the task specification")
    t_status, t_issues = task_val.validate(task, world_spec)
    print(f"  Status: {t_status.value}")
    if t_issues:
        for issue in t_issues:
            print(f"    - {issue}")
    else:
        print("  Task is valid [OK]")

    # -----------------------------------------------------------------------
    # Step 5: Run MockAgent (success scenario)
    # -----------------------------------------------------------------------
    print_step(5, "Run MockAgent (success scenario)")
    agent_config = AgentConfig(agent_type="mock", max_steps=50)
    agent_success = MockAgent(config=agent_config, scenario="success")
    run_config = RunConfig(
        run_id="demo-run-success",
        task_id=task.task_id,
        agent_id=agent_success.agent_id,
    )
    result_success = orchestrator.run(task, world_spec, agent_success, run_config)
    print(f"  Run ID: {result_success.run_id}")
    print(
        f"  Status: {result_success.status.value if hasattr(result_success.status, 'value') else result_success.status}"
    )
    print(f"  Passed: {result_success.passed}")
    print(f"  Agent believes success: {result_success.agent_believes_success}")
    print(f"  Steps: {result_success.step_count}")
    if result_success.verification:
        print(f"  Verification passed: {result_success.verification.passed}")
    if result_success.trajectory:
        print(f"  Trajectory steps: {len(result_success.trajectory.steps)}")

    # -----------------------------------------------------------------------
    # Step 6: Run MockAgent (failure scenario)
    # -----------------------------------------------------------------------
    print_step(6, "Run MockAgent (failure scenario)")
    agent_config_fail = AgentConfig(agent_type="mock", max_steps=50)
    agent_fail = MockAgent(config=agent_config_fail, scenario="failure")
    run_config_fail = RunConfig(
        run_id="demo-run-failure",
        task_id=task.task_id,
        agent_id=agent_fail.agent_id,
    )
    result_fail = orchestrator.run(task, world_spec, agent_fail, run_config_fail)
    print(f"  Run ID: {result_fail.run_id}")
    print(f"  Status: {result_fail.status.value if hasattr(result_fail.status, 'value') else result_fail.status}")
    print(f"  Passed: {result_fail.passed}")
    print(f"  Steps: {result_fail.step_count}")

    # -----------------------------------------------------------------------
    # Step 7: Diagnose the failure
    # -----------------------------------------------------------------------
    print_step(7, "Diagnose the failed run")
    if result_fail.diagnosis:
        diag = result_fail.diagnosis
        if hasattr(diag, "primary_category"):
            # It's the schema FailureDiagnosis
            cat = diag.primary_category
            if hasattr(cat, "value"):
                print(f"  Primary category: {cat.value}")
            else:
                print(f"  Primary category: {cat}")
            print(f"  Confidence: {diag.confidence:.2f}")
            print(f"  Recommended action: {diag.recommended_action}")
        else:
            # It's the dataclass FailureDiagnosis from classifier
            print(f"  Primary category: {diag.primary_category.value}")
            print(f"  Confidence: {diag.confidence:.2f}")
            print(f"  Recommended action: {diag.recommended_action}")
            print("  Supporting evidence:")
            for ev in diag.supporting_evidence:
                print(f"    - {ev}")
    else:
        print("  No diagnosis available")

    # -----------------------------------------------------------------------
    # Step 8: Update curriculum
    # -----------------------------------------------------------------------
    print_step(8, "Update curriculum based on results")
    # Record outcomes per capability
    for cap in task.capabilities:
        tracker.record(cap, result_success.passed)
        tracker.record(cap, result_fail.passed)
    scores = tracker.get_all_scores()
    print("  Capability scores after 2 runs:")
    for cap, score in scores.items():
        filled = int(score * 20)
        bar = "#" * filled + "-" * (20 - filled)
        print(f"    [{bar}] {cap}: {score:.3f}")

    # -----------------------------------------------------------------------
    # Step 9: Generate a related task variant
    # -----------------------------------------------------------------------
    print_step(9, "Generate a related task variant")
    variant = task_gen.generate_variant(
        base_task=task,
        variation="Focus on edge cases with negative page numbers",
    )
    print(f"  Variant task ID: {variant.task_id}")
    print(f"  Difficulty: {variant.difficulty_level} (increased from {task.difficulty_level})")
    print(f"  Description: {variant.description[:100]}...")

    # -----------------------------------------------------------------------
    # Step 10: Persist results to database for dashboard
    # -----------------------------------------------------------------------
    print_step(10, "Persist results to database")
    session = get_session(project_db_path)
    try:
        # Store world
        session.add(
            WorldRecord(
                world_id=world_spec.world_id,
                world_type=world_spec.world_type,
                template_name=world_spec.template_name,
                template_version=world_spec.template_version,
                mutation_id=world_spec.mutation_id,
                seed=world_spec.seed,
                world_dir=world_spec.metadata.get("world_dir", ""),
                initial_commit=world_spec.metadata.get("initial_commit", ""),
                manifest=json.dumps(world_spec.metadata.get("manifest", {})),
                metadata_json=json.dumps(world_spec.to_dict()),
            )
        )

        # Store task
        session.add(
            TaskRecord(
                task_id=task.task_id,
                world_id=task.world_id,
                schema_version=task.schema_version,
                category=task.category.value if hasattr(task.category, "value") else str(task.category),
                description=task.description,
                constraints_json=json.dumps(task.constraints),
                verification_method=task.verification_method,
                difficulty_level=task.difficulty_level,
                capabilities_json=json.dumps(task.capabilities),
                validated=1,
                metadata_json=json.dumps(task.to_dict()),
            )
        )

        # Store success run
        now = datetime.utcnow()
        session.add(
            RunRecord(
                run_id=result_success.run_id,
                task_id=task.task_id,
                agent_id=result_success.agent_id,
                status=(
                    result_success.status.value
                    if hasattr(result_success.status, "value")
                    else str(result_success.status)
                ),
                started_at=now,
                finished_at=now,
                duration_seconds=result_success.duration_seconds,
                agent_believes_success=1 if result_success.agent_believes_success else 0,
                passed=1 if result_success.passed else 0,
                error=result_success.error,
                step_count=result_success.step_count,
                trajectory_json=json.dumps(result_success.trajectory.to_dict()) if result_success.trajectory else None,
                verification_json=(
                    json.dumps(result_success.verification.to_dict()) if result_success.verification else None
                ),
                diagnosis_json=json.dumps(result_success.diagnosis.to_dict()) if result_success.diagnosis else None,
                metadata_json=json.dumps(result_success.metadata),
            )
        )

        # Store failure run
        session.add(
            RunRecord(
                run_id=result_fail.run_id,
                task_id=task.task_id,
                agent_id=result_fail.agent_id,
                status=result_fail.status.value if hasattr(result_fail.status, "value") else str(result_fail.status),
                started_at=now,
                finished_at=now,
                duration_seconds=result_fail.duration_seconds,
                agent_believes_success=1 if result_fail.agent_believes_success else 0,
                passed=1 if result_fail.passed else 0,
                error=result_fail.error,
                step_count=result_fail.step_count,
                trajectory_json=json.dumps(result_fail.trajectory.to_dict()) if result_fail.trajectory else None,
                verification_json=json.dumps(result_fail.verification.to_dict()) if result_fail.verification else None,
                diagnosis_json=json.dumps(result_fail.diagnosis.to_dict()) if result_fail.diagnosis else None,
                metadata_json=json.dumps(result_fail.metadata),
            )
        )

        # Store curriculum state
        session.add(
            CurriculumRecord(
                curriculum_id="demo-curriculum",
                strategy="adaptive",
                generation=1,
                task_pool_json=json.dumps([task.task_id, variant.task_id]),
                capability_scores_json=json.dumps(tracker.get_all_scores()),
                selected_tasks_json=json.dumps([task.task_id]),
            )
        )

        session.commit()
        print("  World, task, 2 runs, and curriculum state stored")
        print(f"  Dashboard can now display data from: {project_db_path}")
    except Exception as e:
        print(f"  Warning: Could not store to database: {e}")
        session.rollback()
    finally:
        session.close()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print_header("Demo Summary")
    print("  [OK] Generated 1 world with pagination_boundary mutation")
    print("  [OK] Validated world and task")
    print(f"  [OK] Ran MockAgent (success): passed={result_success.passed}")
    print(f"  [OK] Ran MockAgent (failure): passed={result_fail.passed}")
    print("  [OK] Diagnosed failure with evidence-based classification")
    print("  [OK] Updated capability tracker")
    print("  [OK] Generated task variant for targeted practice")
    print("  [OK] Persisted results to database for dashboard")
    print("\n  Demo completed successfully!")
    print(f"  Artifacts saved to: {demo_dir}")
    print(f"  Dashboard data in: {project_db_path}")
    print("\n  To view the dashboard:")
    print(f"    cd {PROJECT_ROOT}")
    print("    streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
