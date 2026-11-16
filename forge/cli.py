"""ForgeLab CLI — command-line interface for ForgeLab operations.

Provides commands for initializing the project, checking system health,
generating worlds and tasks, running agents, inspecting results, and
managing experiments.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import typer

app = typer.Typer(
    name="forgelab",
    help="ForgeLab — adaptive environment factory for autonomous agents",
    add_completion=False,
)


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


@app.command()
def init(
    path: str = "./forgelab_workspace",
):
    """Initialize a ForgeLab workspace directory."""
    workspace = Path(path)
    workspace.mkdir(parents=True, exist_ok=True)
    for subdir in ["worlds", "tasks", "runs", "experiments", "artifacts"]:
        (workspace / subdir).mkdir(exist_ok=True)

    # Create default config
    config = workspace / "config.yaml"
    if not config.exists():
        config.write_text(
            "database:\n"
            "  path: ./forgelab.db\n"
            "sandbox:\n"
            "  memory_limit: 512m\n"
            "  cpu_limit: 1.0\n"
            "  timeout_seconds: 120\n"
            "agent:\n"
            "  type: mock\n"
            "  max_steps: 50\n"
        )

    typer.echo(f"[OK] Initialized ForgeLab workspace at {workspace}")
    typer.echo(f"  Database: {workspace / 'forgelab.db'}")
    typer.echo(f"  Config: {config}")


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------


@app.command()
def doctor():
    """Check system health and dependencies."""
    typer.echo("ForgeLab System Check")
    typer.echo("=" * 40)

    # Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    status = "[OK]" if sys.version_info >= (3, 11) else "[FAIL]"
    typer.echo(f"  {status} Python version: {py_ver} (require >= 3.11)")

    # Required packages
    packages = {
        "pyyaml": "yaml",
        "sqlalchemy": "sqlalchemy",
        "typer": "typer",
        "pydantic": "pydantic",
    }
    for name, import_name in packages.items():
        try:
            __import__(import_name)
            typer.echo(f"  [OK] {name}")
        except ImportError:
            typer.echo(f"  [FAIL] {name} (not installed)")

    # Optional packages
    optional = {
        "docker": "docker",
        "fastapi": "fastapi",
        "streamlit": "streamlit",
        "openai": "openai",
    }
    for name, import_name in optional.items():
        try:
            __import__(import_name)
            typer.echo(f"  [OK] {name} (optional)")
        except ImportError:
            typer.echo(f"  [-] {name} (optional, not installed)")

    # Docker
    try:
        import docker

        client = docker.from_env()
        client.ping()
        typer.echo("  [OK] Docker: available")
    except Exception:
        typer.echo("  [-] Docker: not available (required for sandbox execution)")

    # Database
    db_path = Path("./forgelab.db")
    if db_path.exists():
        typer.echo(f"  [OK] Database: {db_path}")
    else:
        typer.echo("  [-] Database: not initialized (run 'forgelab init')")

    # Artifact directories
    for dir_name in ["worlds", "tasks", "runs", "experiments"]:
        if Path(dir_name).exists():
            typer.echo(f"  [OK] {dir_name}/ directory")
        else:
            typer.echo(f"  [-] {dir_name}/ directory (created by 'forgelab init')")


# ---------------------------------------------------------------------------
# World commands
# ---------------------------------------------------------------------------


world_app = typer.Typer(help="Manage software environments (worlds)")
app.add_typer(world_app, name="world")


@world_app.command("generate")
def world_generate(
    template: str = "task_manager_api",
    mutation: str = "pagination_boundary",
    seed: int | None = None,
    output: str = "./worlds",
):
    """Generate a new software environment with a seeded bug."""
    try:
        from forge.world_factory.generator import WorldGenerator
    except ImportError as e:
        typer.echo(f"✗ Cannot import world factory: {e}", err=True)
        raise SystemExit(1)

    generator = WorldGenerator()
    try:
        world = generator.generate(template, mutation, seed=seed)
        world_dict = world.to_dict()

        # Save manifest
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)
        manifest_path = output_path / f"{world.world_id}.json"
        manifest_path.write_text(json.dumps(world_dict, indent=2, default=str))

        typer.echo(f"[OK] Generated world: {world.world_id}")
        typer.echo(f"  Template: {template}")
        typer.echo(f"  Mutation: {mutation}")
        typer.echo(f"  Seed: {seed or 'auto'}")
        typer.echo(f"  Manifest: {manifest_path}")
    except Exception as e:
        typer.echo(f"[FAIL] Failed to generate world: {e}", err=True)
        raise SystemExit(1)


@world_app.command("validate")
def world_validate(
    world_path: str,
):
    """Validate a generated world environment."""
    try:
        from forge.validators.world_validator import WorldValidator
    except ImportError as e:
        typer.echo(f"✗ Cannot import validator: {e}", err=True)
        raise SystemExit(1)

    validator = WorldValidator()
    try:
        result = validator.validate(world_path)
        if result:
            typer.echo(f"✓ World {world_path} is valid")
        else:
            typer.echo(f"✗ World {world_path} validation failed", err=True)
            raise SystemExit(1)
    except Exception as e:
        typer.echo(f"✗ Validation error: {e}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Task commands
# ---------------------------------------------------------------------------


task_app = typer.Typer(help="Manage tasks")
app.add_typer(task_app, name="task")


@task_app.command("list")
def task_list():
    """List available tasks."""
    tasks_dir = Path("./tasks")
    if not tasks_dir.exists():
        typer.echo("No tasks directory found. Run 'forgelab init' first.")
        return

    tasks = list(tasks_dir.glob("*.json"))
    if not tasks:
        typer.echo("No tasks found.")
        return

    typer.echo(f"Found {len(tasks)} tasks:")
    for task_file in tasks:
        try:
            data = json.loads(task_file.read_text())
            typer.echo(f"  - {data.get('task_id', 'unknown')}: {data.get('description', '')[:60]}")
        except Exception:
            typer.echo(f"  - {task_file.name}: (unreadable)")


@task_app.command("validate")
def task_validate(
    task_file: str,
):
    """Validate a task specification."""
    try:
        from forge.validators.world_validator import TaskValidator
    except ImportError as e:
        typer.echo(f"✗ Cannot import validator: {e}", err=True)
        raise SystemExit(1)

    validator = TaskValidator()
    try:
        task_data = json.loads(Path(task_file).read_text())
        # Simple validation — check required fields
        required = ["task_id", "world_id", "category", "description"]
        missing = [f for f in required if f not in task_data]
        if missing:
            typer.echo(f"✗ Missing required fields: {missing}", err=True)
            raise SystemExit(1)
        typer.echo(f"✓ Task {task_data['task_id']} is valid")
    except json.JSONDecodeError as e:
        typer.echo(f"✗ Invalid JSON: {e}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Agent commands
# ---------------------------------------------------------------------------


agent_app = typer.Typer(help="Manage agents")
app.add_typer(agent_app, name="agent")


@agent_app.command("list")
def agent_list():
    """List available agent types."""
    agents = [
        ("mock", "Deterministic mock agent for testing (no API key needed)"),
        ("openai_compatible", "OpenAI-compatible LLM agent (requires API key)"),
    ]
    typer.echo("Available agents:")
    for name, desc in agents:
        typer.echo(f"  - {name}: {desc}")


# ---------------------------------------------------------------------------
# Run commands
# ---------------------------------------------------------------------------


run_app = typer.Typer(help="Execute agent runs")
app.add_typer(run_app, name="run")


@run_app.command()
def run_execute(
    task_file: str,
    agent_type: str = "mock",
    max_steps: int = 50,
):
    """Execute an agent on a task."""
    try:
        from forge.agents.mock_agent import MockAgent
        from forge.core.schemas import RunResult, RunStatus, TaskSpec, VerificationResult
    except ImportError as e:
        typer.echo(f"✗ Cannot import required modules: {e}", err=True)
        raise SystemExit(1)

    # Load task
    try:
        task_data = json.loads(Path(task_file).read_text())
        task = TaskSpec.from_dict(task_data)
    except Exception as e:
        typer.echo(f"✗ Failed to load task: {e}", err=True)
        raise SystemExit(1)

    typer.echo(f"Starting run: {task.task_id}")
    typer.echo(f"  Agent: {agent_type}")
    typer.echo(f"  Max steps: {max_steps}")
    typer.echo()

    # Create run result
    run_result = RunResult(
        run_id=f"run-{task.task_id}",
        task_id=task.task_id,
        agent_id=f"agent-{agent_type}",
        status=RunStatus.COMPLETED,
    )
    run_result.passed = False
    run_result.step_count = 0
    run_result.agent_made_changes = False

    start_time = time.time()

    if agent_type == "mock":
        steps = [
            ("Loading task", 0.2),
            ("Reading workspace files", 0.3),
            ("Analyzing code", 0.5),
            ("Applying fix", 0.4),
            ("Running tests", 0.3),
        ]
        for step_name, delay in steps:
            typer.echo(f"  ⠋ {step_name}...", nl=False)
            time.sleep(delay)
            typer.echo("\r  ✓ " + step_name)

        agent = MockAgent(scenario="success")
        run_result.step_count = len(steps)
        run_result.agent_made_changes = True
        run_result.passed = True
        run_result.agent_believes_success = True

        # Create verification result
        run_result.verification = VerificationResult(
            run_id=run_result.run_id,
            passed=True,
            hidden_tests_passed=True,
            public_tests_ran=True,
            public_tests_passed=True,
            hidden_tests_ran=True,
            reference_solution_checked=True,
            reference_solution_passed=True,
            initial_defect_checked=True,
            initial_defect_detected=True,
        )

        elapsed = time.time() - start_time
        typer.echo()
        typer.echo(f"✓ Run completed in {elapsed:.1f}s")
        typer.echo(f"  Steps: {run_result.step_count}")
        typer.echo(f"  Passed: {run_result.passed}")
    else:
        elapsed = time.time() - start_time
        typer.echo(f"✗ Agent type '{agent_type}' not yet implemented in CLI ({elapsed:.1f}s)", err=True)
        raise SystemExit(1)

    # Save result
    runs_dir = Path("./runs")
    runs_dir.mkdir(exist_ok=True)
    result_path = runs_dir / f"{run_result.run_id}.json"
    result_path.write_text(json.dumps(run_result.to_dict(), indent=2, default=str))
    typer.echo(f"  Result saved: {result_path}")


@run_app.command("inspect")
def run_inspect(
    run_id: str,
):
    """Inspect a run result and its diagnosis."""
    runs_dir = Path("./runs")
    result_file = runs_dir / f"{run_id}.json"

    if not result_file.exists():
        # Try without prefix
        result_file = runs_dir / f"{run_id}.json"
        if not result_file.exists():
            typer.echo(f"✗ Run not found: {run_id}", err=True)
            raise SystemExit(1)

    try:
        data = json.loads(result_file.read_text())
        typer.echo(f"Run: {data.get('run_id')}")
        typer.echo(f"  Status: {data.get('status')}")
        typer.echo(f"  Passed: {data.get('passed')}")
        typer.echo(f"  Steps: {data.get('step_count', 0)}")
        typer.echo(f"  Agent made changes: {data.get('agent_made_changes', False)}")

        if data.get("diagnosis"):
            diag = data["diagnosis"]
            typer.echo(f"  Diagnosis: {diag.get('primary_category')}")
            typer.echo(f"  Confidence: {diag.get('confidence', 0):.2f}")
            typer.echo(f"  Recommended: {diag.get('recommended_action', 'N/A')}")
    except Exception as e:
        typer.echo(f"✗ Failed to inspect run: {e}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Curriculum commands
# ---------------------------------------------------------------------------


curriculum_app = typer.Typer(help="Inspect adaptive curriculum")
app.add_typer(curriculum_app, name="curriculum")


@curriculum_app.command("inspect")
def curriculum_inspect():
    """Inspect the current curriculum state."""
    curriculum_file = Path("./curriculum_state.json")
    if not curriculum_file.exists():
        typer.echo("No curriculum state found. Run some experiments first.")
        return

    try:
        data = json.loads(curriculum_file.read_text())
        typer.echo(f"Curriculum: {data.get('curriculum_id', 'unknown')}")
        typer.echo(f"  Strategy: {data.get('strategy', 'unknown')}")
        typer.echo(f"  Generation: {data.get('generation', 0)}")
        typer.echo(f"  Task pool: {len(data.get('task_pool', []))} tasks")
        typer.echo(f"  Selected: {len(data.get('selected_tasks', []))} tasks")

        caps = data.get("capability_scores", {})
        if caps:
            typer.echo("  Capability scores:")
            for cap, score in caps.items():
                typer.echo(f"    - {cap}: {score:.3f}")
    except Exception as e:
        typer.echo(f"✗ Failed to inspect curriculum: {e}", err=True)


# ---------------------------------------------------------------------------
# Experiment commands
# ---------------------------------------------------------------------------


experiment_app = typer.Typer(help="Manage experiments")
app.add_typer(experiment_app, name="experiment")


@experiment_app.command("create")
def experiment_create(
    name: str = "test_experiment",
    strategy: str = "static",
    hypothesis: str = "",
):
    """Create a new experiment."""
    try:
        from forge.experiments.manager import CurriculumStrategy, ExperimentConfig, ExperimentManager
    except ImportError as e:
        typer.echo(f"✗ Cannot import experiment manager: {e}", err=True)
        raise SystemExit(1)

    strategy_map = {
        "static": CurriculumStrategy.STATIC,
        "random": CurriculumStrategy.RANDOM,
        "adaptive": CurriculumStrategy.ADAPTIVE,
    }
    strat = strategy_map.get(strategy, CurriculumStrategy.STATIC)

    config = ExperimentConfig(
        name=name,
        hypothesis=hypothesis or f"Testing {strategy} curriculum strategy",
        curriculum_strategy=strat,
    )

    manager = ExperimentManager()
    exp_id = manager.create_experiment(config)

    typer.echo(f"✓ Created experiment: {exp_id}")
    typer.echo(f"  Name: {name}")
    typer.echo(f"  Strategy: {strategy}")


@experiment_app.command("list")
def experiment_list():
    """List experiments."""
    exp_dir = Path("./experiments")
    if not exp_dir.exists():
        typer.echo("No experiments directory found.")
        return

    experiments = list(exp_dir.glob("*.json"))
    if not experiments:
        typer.echo("No experiments found.")
        return

    typer.echo(f"Found {len(experiments)} experiments:")
    for exp_file in experiments:
        try:
            data = json.loads(exp_file.read_text())
            typer.echo(f"  - {data.get('experiment_id', 'unknown')}: {data.get('name', '')}")
        except Exception:
            typer.echo(f"  - {exp_file.name}: (unreadable)")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@app.command()
def report(
    output: str = "./report.json",
):
    """Export a summary report of all runs."""
    runs_dir = Path("./runs")
    if not runs_dir.exists():
        typer.echo("No runs directory found.")
        return

    runs = list(runs_dir.glob("*.json"))
    if not runs:
        typer.echo("No runs found.")
        return

    total = len(runs)
    passed = 0
    for run_file in runs:
        try:
            data = json.loads(run_file.read_text())
            if data.get("passed"):
                passed += 1
        except Exception:
            pass

    report_data = {
        "total_runs": total,
        "passed_runs": passed,
        "success_rate": passed / total if total > 0 else 0.0,
    }

    output_path = Path(output)
    output_path.write_text(json.dumps(report_data, indent=2))
    typer.echo(f"✓ Report exported to {output_path}")
    typer.echo(f"  Total runs: {total}")
    typer.echo(f"  Passed: {passed}")
    typer.echo(f"  Success rate: {report_data['success_rate']:.1%}")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@app.command()
def export(
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json or csv"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Export run data from the database as JSON or CSV."""
    from forge.api.export import export_runs as do_export

    db_path = os.environ.get("FORGELAB_DB_PATH", "./forgelab.db")
    db_url = f"sqlite:///{db_path}"

    out_path = Path(output) if output else None
    try:
        result = do_export(db_url, format=fmt, output=out_path)
        if output:
            typer.echo(f"✓ Exported to {output}")
        else:
            typer.echo(result)
    except Exception as e:
        typer.echo(f"✗ Export failed: {e}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Database commands
# ---------------------------------------------------------------------------


db_app = typer.Typer(help="Manage database migrations")
app.add_typer(db_app, name="db")


@db_app.command("upgrade")
def db_upgrade(
    revision: str = typer.Option("head", help="Revision to upgrade to (default: head)"),
):
    """Upgrade database schema to a given revision."""
    try:
        from alembic import command
        from alembic.config import Config
    except ImportError:
        typer.echo("✗ Alembic is not installed. Run: pip install alembic", err=True)
        raise SystemExit(1)

    here = Path(__file__).resolve().parent.parent
    config = Config(str(here / "alembic.ini"))
    try:
        command.upgrade(config, revision)
        typer.echo(f"[OK] Database upgraded to {revision}")
    except Exception as e:
        typer.echo(f"[FAIL] Migration failed: {e}", err=True)
        raise SystemExit(1)


@db_app.command("current")
def db_current():
    """Show current database revision."""
    try:
        from alembic import command
        from alembic.config import Config
    except ImportError:
        typer.echo("✗ Alembic is not installed. Run: pip install alembic", err=True)
        raise SystemExit(1)

    here = Path(__file__).resolve().parent.parent
    config = Config(str(here / "alembic.ini"))
    try:
        command.current(config, verbose=True)
    except Exception as e:
        typer.echo(f"✗ Failed to check current revision: {e}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Benchmark commands
# ---------------------------------------------------------------------------


benchmark_app = typer.Typer(help="Run benchmark evaluations")
app.add_typer(benchmark_app, name="benchmark")


@benchmark_app.command("run")
def benchmark_run(
    agent_type: str = typer.Option("mock", "--agent", "-a", help="Agent type to benchmark"),
    tasks: str = typer.Option("seed", "--tasks", "-t", help="Task source: seed or heldout"),
    output: str = typer.Option("./benchmark_results", "--output", "-o", help="Output directory"),
    fmt: str = typer.Option("json", "--format", "-f", help="Report format: json or markdown"),
):
    """Run a benchmark evaluation against an agent."""
    try:
        from forge.agents.mock_agent import MockAgent
        from forge.agents.rule_based import RuleBasedAgent
        from forge.core.schemas import AgentConfig
        from forge.evaluation.benchmark import BenchmarkRunner
        from forge.task_factory.generator import TaskGenerator
    except ImportError as e:
        typer.echo(f"✗ Cannot import required modules: {e}", err=True)
        raise SystemExit(1)

    # Create agent
    config = AgentConfig(agent_type=agent_type)
    if agent_type == "mock":
        agent = MockAgent(config=config)
    elif agent_type == "rule_based":
        rules_file = str(Path(__file__).parent.parent / "configs" / "rules" / "default_rules.yaml")
        agent = RuleBasedAgent(config=config, rules_file=rules_file)
    else:
        typer.echo(f"✗ Unknown agent type: {agent_type}", err=True)
        raise SystemExit(1)

    # Load tasks
    if tasks == "seed":
        task_file = Path(__file__).parent.parent / "datasets" / "seeds" / "seed_tasks.yaml"
        task_list = TaskGenerator.load_seed_tasks(str(task_file))
    elif tasks == "heldout":
        from forge.task_factory.heldout import HeldOutManager

        manager = HeldOutManager()
        task_list = manager.get_heldout_tasks()
    else:
        typer.echo(f"✗ Unknown task source: {tasks}", err=True)
        raise SystemExit(1)

    if not task_list:
        typer.echo("No tasks found to benchmark.")
        return

    typer.echo(f"Starting benchmark: {len(task_list)} tasks with {agent_type} agent")
    typer.echo()

    runner = BenchmarkRunner(agent=agent)
    workspace_base = Path(output) / "workspaces"
    report = runner.run(task_list, workspace_base)

    # Save report
    output_path = Path(output)
    saved = runner.save_report(report, output_path, format=fmt)

    typer.echo("✓ Benchmark completed")
    typer.echo(f"  Agent: {report.agent_type}")
    typer.echo(f"  Tasks: {report.total_tasks}")
    typer.echo(f"  Passed: {report.passed_tasks}")
    typer.echo(f"  Failed: {report.failed_tasks}")
    typer.echo(f"  Pass rate: {report.pass_rate:.1%}")
    typer.echo(f"  Avg duration: {report.avg_duration:.2f}s")
    typer.echo(f"  Report: {saved}")


# ---------------------------------------------------------------------------
# Held-out evaluation commands
# ---------------------------------------------------------------------------


heldout_app = typer.Typer(help="Manage held-out evaluation sets")
app.add_typer(heldout_app, name="heldout")


@heldout_app.command("create")
def heldout_create(
    size: int = typer.Option(10, "--size", "-s", help="Number of tasks to generate"),
    output: str = typer.Option("./datasets/heldout", "--output", "-o", help="Output directory"),
):
    """Create a held-out evaluation set of frozen tasks."""
    try:
        from forge.task_factory.heldout import HeldOutManager
    except ImportError as e:
        typer.echo(f"✗ Cannot import held-out manager: {e}", err=True)
        raise SystemExit(1)

    manager = HeldOutManager(output_dir=Path(output))
    tasks = manager.create_heldout_set(size)

    typer.echo(f"✓ Created held-out set: {len(tasks)} tasks")
    typer.echo(f"  Output: {output}")
    for task in tasks:
        typer.echo(f"  - {task.task_id}: {task.description[:50] if task.description else ''}")


@heldout_app.command("list")
def heldout_list(
    path: str = typer.Option("./datasets/heldout", help="Held-out tasks directory"),
):
    """List held-out evaluation tasks."""
    try:
        from forge.task_factory.heldout import HeldOutManager
    except ImportError as e:
        typer.echo(f"✗ Cannot import held-out manager: {e}", err=True)
        raise SystemExit(1)

    manager = HeldOutManager(output_dir=Path(path))
    tasks = manager.get_heldout_tasks()

    if not tasks:
        typer.echo("No held-out tasks found.")
        return

    typer.echo(f"Found {len(tasks)} held-out tasks:")
    for task in tasks:
        typer.echo(f"  - {task.task_id}: {task.description[:50] if task.description else ''}")


# ---------------------------------------------------------------------------
# Training data commands
# ---------------------------------------------------------------------------


train_app = typer.Typer(help="Manage training data versions and curation")
app.add_typer(train_app, name="train")


@train_app.command("version")
def train_version(
    tag: str = typer.Option(..., "--tag", "-t", help="Version tag (e.g., v1.0)"),
    description: str = typer.Option("", "--description", "-d", help="Version description"),
):
    """Create a versioned snapshot of training data from the database."""
    from forge.training.versioning import DatasetVersioner

    db_path = os.environ.get("FORGELAB_DB_PATH", "./forgelab.db")
    db_url = f"sqlite:///{db_path}"

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(db_url)
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT trajectory_json FROM run_record WHERE trajectory_json IS NOT NULL")).fetchall()

        examples = []
        for row in rows:
            if row[0]:
                try:
                    data = json.loads(row[0])
                    examples.append(data)
                except json.JSONDecodeError:
                    pass

        versioner = DatasetVersioner()
        version = versioner.create_version(
            tag=tag,
            examples=examples,
            description=description,
            metadata={"source": db_url, "num_runs": len(rows)},
        )

        typer.echo(f"✓ Created version: {version.version_tag}")
        typer.echo(f"  Examples: {version.num_examples}")
        typer.echo(f"  Description: {version.description or '(none)'}")
    except Exception as e:
        typer.echo(f"✗ Failed to create version: {e}", err=True)
        raise SystemExit(1)


@train_app.command("curate")
def train_curate(
    fmt: str = typer.Option("sft", "--format", "-f", help="Export format: sft or rl"),
    output: str = typer.Option("./curated_examples.jsonl", "--output", "-o", help="Output file"),
):
    """Curate positive and negative examples from run data."""
    from forge.training.curator import ExampleCurator
    from forge.core.schemas import RunResult, FailureCategory, Trajectory, TrajectoryStep, RunStatus, FailureDiagnosis

    db_path = os.environ.get("FORGELAB_DB_PATH", "./forgelab.db")
    db_url = f"sqlite:///{db_path}"

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(db_url)
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT run_id, task_id, passed, failure_category, trajectory_json FROM run_record")).fetchall()

        results = []
        for row in rows:
            run_id, task_id, passed, failure_cat, traj_json = row
            diagnosis = None
            if failure_cat:
                try:
                    cat = FailureCategory(failure_cat)
                    diagnosis = FailureDiagnosis(
                        run_id=run_id,
                        primary_category=cat,
                        confidence=0.8,
                    )
                except ValueError:
                    pass

            trajectory = None
            if traj_json:
                try:
                    traj_data = json.loads(traj_json)
                    steps = [
                        TrajectoryStep(
                            step_index=s.get("step_index", 0),
                            action=s.get("action", ""),
                            tool_name=s.get("tool_name"),
                            tool_result=s.get("tool_result"),
                            duration_seconds=s.get("duration_seconds", 0.0),
                        )
                        for s in traj_data.get("steps", [])
                    ]
                    trajectory = Trajectory(steps=steps)
                except (json.JSONDecodeError, KeyError):
                    pass

            result = RunResult(
                run_id=run_id,
                task_id=task_id,
                status=RunStatus.COMPLETED,
                passed=bool(passed),
                trajectory=trajectory,
                diagnosis=diagnosis,
                metadata={"agent_id": "mock"},
            )
            results.append(result)

        curator = ExampleCurator()
        positive = curator.curate_positive(results)
        negative = curator.curate_negative(results)
        all_examples = positive + negative

        if fmt == "sft":
            curator.export_sft_format(all_examples, output)
        else:
            curator.export_rl_format(all_examples, output)

        typer.echo(f"✓ Curated {len(all_examples)} examples ({len(positive)} positive, {len(negative)} negative)")
        typer.echo(f"  Format: {fmt}")
        typer.echo(f"  Output: {output}")
    except Exception as e:
        typer.echo(f"✗ Curation failed: {e}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Experiment run command
# ---------------------------------------------------------------------------


@experiment_app.command("run")
def experiment_run(
    preset: str = typer.Option("A", "--preset", "-p", help="Experiment preset: A, B, C, D, ablation_tools, difficulty_scaling, cross_template"),
    agent: str = typer.Option("mock", "--agent", "-a", help="Agent type"),
    tasks: int = typer.Option(5, "--tasks", "-t", help="Number of tasks to run"),
):
    """Run an experiment preset end-to-end."""
    try:
        from forge.experiments.config import get_preset_experiments
        from forge.experiments.runner import ExperimentRunner
    except ImportError as e:
        typer.echo(f"✗ Cannot import experiment modules: {e}", err=True)
        raise SystemExit(1)

    presets = get_preset_experiments()
    if preset not in presets:
        typer.echo(f"✗ Unknown preset: {preset}. Available: {', '.join(presets.keys())}", err=True)
        raise SystemExit(1)

    config = presets[preset]()
    config.agent_type = agent

    # Generate task IDs
    task_ids = [f"task-{i}" for i in range(tasks)]

    typer.echo(f"Running experiment: {config.name}")
    typer.echo(f"  Preset: {preset}")
    typer.echo(f"  Agent: {agent}")
    typer.echo(f"  Tasks: {tasks}")
    typer.echo()

    runner = ExperimentRunner()
    result = runner.run_experiment(config=config, task_ids=task_ids, agent_type=agent)

    typer.echo("✓ Experiment completed")
    typer.echo(f"  ID: {result.experiment_id}")
    typer.echo(f"  Total runs: {result.total_runs}")
    typer.echo(f"  Passed: {result.passed_runs}")
    typer.echo(f"  Failed: {result.failed_runs}")
    typer.echo(f"  Success rate: {result.success_rate:.1%}")


@experiment_app.command("report")
def experiment_report(
    group_a: str = typer.Option("1.0,1.0,0.5,0.5,1.0", "--group-a", "-a", help="Comma-separated values for group A"),
    group_b: str = typer.Option("0.5,0.5,0.5,0.0,0.5", "--group-b", "-b", help="Comma-separated values for group B"),
    name_a: str = typer.Option("Method A", "--name-a", help="Name for group A"),
    name_b: str = typer.Option("Method B", "--name-b", help="Name for group B"),
):
    """Generate a statistical comparison report for two experiment groups."""
    from forge.experiments.statistics import StatisticalAnalyzer

    try:
        vals_a = [float(x.strip()) for x in group_a.split(",")]
        vals_b = [float(x.strip()) for x in group_b.split(",")]
    except ValueError as e:
        typer.echo(f"✗ Invalid values: {e}", err=True)
        raise SystemExit(1)

    analyzer = StatisticalAnalyzer()
    report = analyzer.generate_report(vals_a, vals_b, name_a=name_a, name_b=name_b)

    typer.echo(report["summary"])
    typer.echo()


# ---------------------------------------------------------------------------
# Serve
# ---------------------------------------------------------------------------


@app.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
):
    """Start the ForgeLab API server."""
    try:
        import uvicorn
    except ImportError:
        typer.echo("✗ uvicorn is not installed. Run: pip install uvicorn", err=True)
        raise SystemExit(1)

    typer.echo(f"Starting ForgeLab API server at http://{host}:{port}")
    typer.echo("Press Ctrl+C to stop.")
    try:
        uvicorn.run("forge.api.app:app", host=host, port=port, reload=False)
    except KeyboardInterrupt:
        typer.echo("\nServer stopped.")


# ---------------------------------------------------------------------------
# Snapshot commands
# ---------------------------------------------------------------------------

snapshot_app = typer.Typer(help="Workspace snapshot management")
app.add_typer(snapshot_app, name="snapshot")


@snapshot_app.command()
def snapshot_capture(
    workspace: str = typer.Argument(..., help="Workspace directory to capture"),
    run_id: str = typer.Option("", "--run-id", "-r", help="Run ID for the snapshot"),
    output_dir: str = typer.Option("snapshots", "--output-dir", "-o", help="Snapshot output directory"),
):
    """Capture a workspace snapshot."""
    from forge.runner.snapshot import WorkspaceSnapshotter

    try:
        snapshotter = WorkspaceSnapshotter(output_dir)
        snapshot = snapshotter.capture(workspace, run_id=run_id)
        path = snapshotter.save(snapshot)
        typer.echo(f"✓ Captured {len(snapshot.file_contents)} files")
        typer.echo(f"  Run ID: {snapshot.run_id}")
        typer.echo(f"  Saved: {path}")
    except Exception as e:
        typer.echo(f"✗ Capture failed: {e}", err=True)
        raise SystemExit(1)


@snapshot_app.command()
def snapshot_list(
    snapshot_dir: str = typer.Option("snapshots", "--snapshot-dir", "-d", help="Snapshot directory"),
):
    """List all saved snapshots."""
    from forge.runner.snapshot import WorkspaceSnapshotter

    snapshotter = WorkspaceSnapshotter(snapshot_dir)
    snapshots = snapshotter.list_snapshots()
    if not snapshots:
        typer.echo("No snapshots found.")
        return
    for s in snapshots:
        typer.echo(f"  {s['run_id']} | {s['file_count']} files | {s['file']}")


@snapshot_app.command()
def snapshot_restore(
    snapshot_path: str = typer.Argument(..., help="Path to snapshot JSON file"),
    restore_dir: str = typer.Argument(..., help="Directory to restore into"),
):
    """Restore a workspace from a snapshot."""
    from forge.runner.snapshot import WorkspaceSnapshotter

    try:
        snapshotter = WorkspaceSnapshotter()
        count = snapshotter.restore(snapshot_path, restore_dir)
        typer.echo(f"✓ Restored {count} files to {restore_dir}")
    except Exception as e:
        typer.echo(f"✗ Restore failed: {e}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Coverage command
# ---------------------------------------------------------------------------

@app.command()
def coverage(
    mutations: str = typer.Option("", "--mutations", "-m", help="Comma-separated mutation names"),
):
    """Analyze mutation coverage across tasks."""
    from forge.evaluation.mutation_coverage import MutationCoverageAnalyzer
    from forge.world_factory import seeder

    try:
        analyzer = MutationCoverageAnalyzer(seeder_module=seeder)
        all_muts = seeder.list_mutations()
        if mutations:
            all_muts = [m.strip() for m in mutations.split(",")]
        report = analyzer.analyze(all_mutations=all_muts)
        typer.echo(f"Coverage: {report.covered_mutations}/{report.total_mutations} "
                    f"({report.coverage_percent:.1f}%)")
        if report.uncovered_mutations:
            typer.echo(f"Uncovered: {', '.join(report.uncovered_mutations)}")
    except Exception as e:
        typer.echo(f"✗ Coverage analysis failed: {e}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Difficulty calibrate command
# ---------------------------------------------------------------------------

@app.command()
def difficulty_calibrate(
    results_file: str = typer.Option("", "--results", "-r", help="JSON file with run results"),
):
    """Calibrate task difficulty based on run results."""
    from forge.evaluation.difficulty_calibration import DifficultyCalibrator

    try:
        calibrator = DifficultyCalibrator()
        if results_file:
            import json as _json
            with open(results_file) as f:
                results = _json.load(f)
        else:
            # Demo data
            results = [
                {"task_id": f"task-{i}", "assigned_difficulty": 3, "passed": i % 2 == 0}
                for i in range(10)
            ]
        calibrations = calibrator.calibrate(results)
        adjustments = calibrator.suggest_adjustments()
        typer.echo(f"Calibrated {len(calibrations)} tasks")
        if adjustments:
            typer.echo(f"Adjustments needed: {len(adjustments)}")
            for adj in adjustments:
                direction = "easier" if adj.adjustment < 0 else "harder"
                typer.echo(
                    f"  {adj.task_id}: {adj.assigned_difficulty} → {adj.suggested_difficulty} "
                    f"({direction}, pass rate {adj.actual_pass_rate:.0%})"
                )
        else:
            typer.echo("No adjustments needed.")
    except Exception as e:
        typer.echo(f"✗ Calibration failed: {e}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Behavior analyze command
# ---------------------------------------------------------------------------

@app.command()
def behavior_analyze(
    trajectories_file: str = typer.Option("", "--trajectories", "-t", help="JSON file with trajectories"),
):
    """Analyze agent behavior from trajectories."""
    from forge.evaluation.behavior_analysis import BehaviorAnalyzer

    try:
        analyzer = BehaviorAnalyzer()
        if trajectories_file:
            import json as _json
            with open(trajectories_file) as f:
                trajectories = _json.load(f)
            if not isinstance(trajectories, list):
                trajectories = [trajectories]
        else:
            # Demo data
            trajectories = [
                {
                    "agent_type": "mock",
                    "steps": [
                        {"tool_name": "read_file", "success": True, "duration_ms": 50},
                        {"tool_name": "write_file", "success": True, "duration_ms": 30},
                    ],
                    "passed": True,
                    "task_id": "task-1",
                },
                {
                    "agent_type": "mock",
                    "steps": [
                        {"tool_name": "read_file", "success": True, "duration_ms": 50},
                        {"tool_name": "write_file", "success": False, "duration_ms": 10},
                    ],
                    "passed": False,
                    "failure_category": "agent_failure",
                    "task_id": "task-2",
                },
            ]
        profiles = analyzer.analyze(trajectories)
        for agent_type, profile in profiles.items():
            typer.echo(f"Agent: {agent_type}")
            typer.echo(f"  Runs: {profile.total_runs}, Pass rate: {profile.pass_rate:.1%}")
            for tp in profile.tool_patterns:
                typer.echo(f"  Tool: {tp.tool_name} ({tp.call_count} calls)")
            for fm in profile.failure_modes:
                typer.echo(f"  Failure: {fm.category} ({fm.count}x)")
    except Exception as e:
        typer.echo(f"✗ Behavior analysis failed: {e}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Report generate command
# ---------------------------------------------------------------------------

@app.command()
def report_generate(
    template: str = typer.Option("executive_summary", "--template", "-t",
                                  help="Template: research_paper, executive_summary, technical_deep_dive"),
    results_file: str = typer.Option("", "--results", "-r", help="JSON file with run results"),
    output: str = typer.Option("", "--output", "-o", help="Output file (default: stdout)"),
):
    """Generate an evaluation report using a template."""
    from forge.evaluation.report_templates import ReportTemplate

    try:
        if results_file:
            import json as _json
            with open(results_file) as f:
                results = _json.load(f)
            data = {"run_results": results}
        else:
            data = {
                "run_results": [
                    {"task_id": "task-1", "template": "task_manager_api", "passed": True,
                     "duration_seconds": 10.5, "trajectory": []},
                    {"task_id": "task-2", "template": "data_pipeline", "passed": False,
                     "duration_seconds": 5.2, "failure_category": "agent_failure", "trajectory": []},
                ],
                "agent_type": "mock",
            }
        report = ReportTemplate.generate(template, data)
        if output:
            Path(output).write_text(report, encoding="utf-8")
            typer.echo(f"✓ Report saved to {output}")
        else:
            typer.echo(report)
    except Exception as e:
        typer.echo(f"✗ Report generation failed: {e}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    app()


if __name__ == "__main__":
    main()
