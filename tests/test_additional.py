"""Tests for additional ForgeLab modules and new features.

Covers: seed task loader, flask_app template, Alembic migrations,
database models, OpenAI agent config, training adapter,
task_factory mutations/difficulty/selection, world_factory manifest,
sandbox policies/executor/reset, runner lifecycle/tool_executor,
diagnosis rules/triage/report, evaluation metrics/scoring/reports,
curriculum difficulty/history/updater, experiments artifacts/comparison.
"""

import os
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Seed Task Loader
# ---------------------------------------------------------------------------


class TestSeedTaskLoader:
    def test_load_seed_tasks_from_yaml(self):
        """Should load seed tasks from the actual seed_tasks.yaml file."""
        from forge.task_factory.generator import TaskGenerator

        generator = TaskGenerator()
        seed_file = Path(__file__).parent.parent / "datasets" / "seeds" / "seed_tasks.yaml"
        tasks = generator.load_seed_tasks(str(seed_file))

        assert len(tasks) == 8
        assert tasks[0].task_id == "PY-REPAIR-001"
        assert tasks[0].metadata["template"] == "task_manager_api"
        assert tasks[0].metadata["mutation"] == "pagination_boundary"

    def test_load_seed_tasks_missing_file(self):
        """Should return empty list for missing file."""
        from forge.task_factory.generator import TaskGenerator

        generator = TaskGenerator()
        tasks = generator.load_seed_tasks("/nonexistent/seed_tasks.yaml")
        assert tasks == []

    def test_load_seed_tasks_flask_app(self):
        """Should load flask_app seed tasks correctly."""
        from forge.task_factory.generator import TaskGenerator

        generator = TaskGenerator()
        seed_file = Path(__file__).parent.parent / "datasets" / "seeds" / "seed_tasks.yaml"
        tasks = generator.load_seed_tasks(str(seed_file))

        flask_tasks = [t for t in tasks if t.metadata["template"] == "flask_app"]
        assert len(flask_tasks) == 2  # PY-REPAIR-004 and 005
        assert flask_tasks[0].task_id == "PY-REPAIR-004"
        assert flask_tasks[0].metadata["mutation"] == "session_timeout"

    def test_load_seed_tasks_verification_nested(self):
        """Should handle nested verification dict in seed YAML."""
        from forge.task_factory.generator import TaskGenerator

        generator = TaskGenerator()
        seed_file = Path(__file__).parent.parent / "datasets" / "seeds" / "seed_tasks.yaml"
        tasks = generator.load_seed_tasks(str(seed_file))

        for task in tasks:
            assert task.verification_method == "hidden_pytest"
            assert task.require_existing_tests is True


# ---------------------------------------------------------------------------
# Flask App Template
# ---------------------------------------------------------------------------


class TestFlaskAppTemplate:
    def test_flask_app_template_registered(self):
        """Should have flask_app template registered."""
        from forge.world_factory.templates import get_template

        template = get_template("flask_app")
        assert template is not None
        assert template["name"] == "flask_app"
        assert "app.py" in template["files"]

    def test_flask_app_generates_world(self):
        """Should generate a world from flask_app template."""
        from forge.world_factory.generator import WorldGenerator

        generator = WorldGenerator()
        world = generator.generate("flask_app", "session_timeout", seed=42)
        assert world.template_name == "flask_app"
        assert world.mutation_id == "session_timeout"

    def test_flask_app_session_timeout_mutation(self):
        """Should apply session_timeout mutation correctly."""
        from forge.world_factory.seeder import get_mutation

        mutation = get_mutation("session_timeout")
        assert mutation is not None
        assert mutation["id"] == "session_timeout"
        assert "return 0" in mutation["replace_with"]

    def test_flask_app_password_hash_mutation(self):
        """Should apply password_hash mutation correctly."""
        from forge.world_factory.seeder import get_mutation

        mutation = get_mutation("password_hash")
        assert mutation is not None
        assert "return password" in mutation["replace_with"]

    def test_flask_app_csrf_token_mutation(self):
        """Should apply csrf_token mutation correctly."""
        from forge.world_factory.seeder import get_mutation

        mutation = get_mutation("csrf_token")
        assert mutation is not None
        assert "return True" in mutation["replace_with"]

    def test_flask_app_has_hidden_tests(self):
        """Should include hidden tests in flask_app template."""
        from forge.world_factory.templates import get_template

        template = get_template("flask_app")
        assert ".hidden_tests/test_hidden.py" in template["files"]
        assert "test_password_not_plaintext" in template["files"][".hidden_tests/test_hidden.py"]

    def test_flask_app_has_public_tests(self):
        """Should include public tests in flask_app template."""
        from forge.world_factory.templates import get_template

        template = get_template("flask_app")
        assert "tests/test_public.py" in template["files"]
        assert "test_register_user" in template["files"]["tests/test_public.py"]


# ---------------------------------------------------------------------------
# Alembic Migrations
# ---------------------------------------------------------------------------


class TestAlembicMigrations:
    def test_migration_file_exists(self):
        """Should have at least one migration file."""
        migrations_dir = Path(__file__).parent.parent / "migrations" / "versions"
        migration_files = list(migrations_dir.glob("*.py"))
        assert len(migration_files) >= 1

    def test_alembic_ini_exists(self):
        """Should have alembic.ini configuration."""
        alembic_ini = Path(__file__).parent.parent / "alembic.ini"
        assert alembic_ini.exists()

    def test_migration_env_py_imports_models(self):
        """Should import Base from forge.db.models."""
        env_py = Path(__file__).parent.parent / "migrations" / "env.py"
        content = env_py.read_text()
        assert "from forge.db.models import Base" in content
        assert "target_metadata = Base.metadata" in content


# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------


class TestDatabaseModels:
    def test_world_record_to_dict(self):
        """WorldRecord.to_dict should serialize correctly."""
        import json

        from forge.db.models import WorldRecord

        record = WorldRecord(
            world_id="w-1",
            world_type="code_repair",
            template_name="task_manager_api",
            mutation_id="pagination_boundary",
            metadata_json=json.dumps({"key": "value"}),
        )
        d = record.to_dict()
        assert d["world_id"] == "w-1"
        assert d["metadata"] == {"key": "value"}

    def test_task_record_to_dict(self):
        """TaskRecord.to_dict should serialize correctly."""
        import json

        from forge.db.models import TaskRecord

        record = TaskRecord(
            task_id="t-1",
            category="bug_repair",
            description="Fix a bug",
            constraints_json=json.dumps(["preserve_api"]),
            capabilities_json=json.dumps(["debugging"]),
        )
        d = record.to_dict()
        assert d["task_id"] == "t-1"
        assert d["constraints"] == ["preserve_api"]
        assert d["capabilities"] == ["debugging"]

    def test_run_record_to_dict(self):
        """RunRecord.to_dict should serialize correctly."""
        import json

        from forge.db.models import RunRecord

        record = RunRecord(
            run_id="r-1",
            task_id="t-1",
            agent_id="mock",
            status="completed",
            passed=1,
            metadata_json=json.dumps({"runs": 2}),
        )
        d = record.to_dict()
        assert d["run_id"] == "r-1"
        assert d["passed"] is True
        assert d["metadata"] == {"runs": 2}

    def test_schema_version_constant(self):
        """SCHEMA_VERSION should be a string."""
        from forge.db.models import SCHEMA_VERSION

        assert isinstance(SCHEMA_VERSION, str)
        assert SCHEMA_VERSION == "1.0"

    def test_init_db_creates_tables(self):
        """init_db should create all tables."""
        import sqlite3

        db_fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(db_fd)

        try:
            from forge.db.models import init_db

            session = init_db(db_path)
            session.close()
            # Check tables exist via raw sqlite
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            assert "_schema_meta" in tables
            assert "worlds" in tables
            assert "tasks" in tables
            assert "runs" in tables
            assert "curriculum_states" in tables
            assert "experiments" in tables
        finally:
            if os.path.exists(db_path):
                try:
                    os.unlink(db_path)
                except PermissionError:
                    pass


# ---------------------------------------------------------------------------
# OpenAI Agent Config
# ---------------------------------------------------------------------------


class TestOpenAIAgentConfig:
    def test_openai_agent_import(self):
        """OpenAI agent module should be importable."""
        from forge.agents import openai_compatible

        assert hasattr(openai_compatible, "OpenAICompatibleAgent")

    def test_openai_agent_tool_definitions(self):
        """OpenAI agent should define tools."""
        from forge.agents.openai_compatible import TOOLS

        assert len(TOOLS) > 0
        for tool in TOOLS:
            assert "type" in tool
            assert "function" in tool


# ---------------------------------------------------------------------------
# Training Adapter
# ---------------------------------------------------------------------------


class TestTrainingAdapter:
    def test_adapter_import(self):
        """Training adapter should be importable."""
        from forge.training import adapter

        assert hasattr(adapter, "TrainingAdapter")

    def test_training_adapter_is_abstract(self):
        """TrainingAdapter should be an abstract base class."""

        from forge.training.adapter import TrainingAdapter

        # TrainingAdapter has abstract methods
        assert len(TrainingAdapter.__abstractmethods__) > 0


# ---------------------------------------------------------------------------
# Task Factory: Mutations
# ---------------------------------------------------------------------------


class TestTaskFactoryMutations:
    def test_mutation_module_import(self):
        """Mutations module should be importable."""
        from forge.task_factory import mutations

        assert hasattr(mutations, "get_mutation")

    def test_get_mutation(self):
        """Should retrieve a mutation by ID."""
        from forge.task_factory.mutations import get_mutation

        mutation = get_mutation("pagination_boundary")
        assert mutation is not None
        assert mutation.mutation_id == "pagination_boundary"

    def test_get_all_mutations(self):
        """Should return all registered mutations."""
        from forge.task_factory.mutations import get_all_mutations

        all_mutations = get_all_mutations()
        assert len(all_mutations) >= 3


# ---------------------------------------------------------------------------
# Task Factory: Difficulty
# ---------------------------------------------------------------------------


class TestTaskFactoryDifficulty:
    def test_difficulty_module_import(self):
        """Difficulty module should be importable."""
        from forge.task_factory import difficulty

        assert hasattr(difficulty, "estimate_task_difficulty")

    def test_estimate_task_difficulty(self):
        """Should estimate difficulty score."""
        from forge.task_factory.difficulty import estimate_task_difficulty

        score = estimate_task_difficulty(
            mutation_id="pagination_boundary",
            capabilities=["debugging", "security"],
            base_difficulty=2,
        )
        assert isinstance(score, (int, float))
        assert score > 0


# ---------------------------------------------------------------------------
# Task Factory: Selection
# ---------------------------------------------------------------------------


class TestTaskFactorySelection:
    def test_selection_module_import(self):
        """Selection module should be importable."""
        from forge.task_factory import selection

        assert hasattr(selection, "TaskPool")

    def test_task_pool(self):
        """TaskPool should manage a pool of tasks."""
        from forge.task_factory.selection import TaskPool

        pool = TaskPool()
        assert len(pool.tasks) == 0


# ---------------------------------------------------------------------------
# World Factory: Manifest
# ---------------------------------------------------------------------------


class TestWorldFactoryManifest:
    def test_manifest_module_import(self):
        """Manifest module should be importable."""
        from forge.world_factory import manifest

        # Module exists and is importable
        assert manifest is not None

    def test_manifest_module_has_types(self):
        """Manifest module should define write_manifest."""
        from forge.world_factory.manifest import write_manifest

        assert callable(write_manifest)


# ---------------------------------------------------------------------------
# Sandbox: Policies
# ---------------------------------------------------------------------------


class TestSandboxPolicies:
    def test_policies_module_import(self):
        """Policies module should be importable."""
        from forge.sandbox import policies

        assert hasattr(policies, "SandboxPolicy")

    def test_sandbox_policy(self):
        """SandboxPolicy should be instantiable."""
        from forge.sandbox.policies import SandboxPolicy

        policy = SandboxPolicy()
        assert policy is not None


# ---------------------------------------------------------------------------
# Sandbox: Executor
# ---------------------------------------------------------------------------


class TestSandboxExecutor:
    def test_executor_module_import(self):
        """Executor module should be importable."""
        from forge.sandbox import executor

        assert hasattr(executor, "SandboxExecutor")


# ---------------------------------------------------------------------------
# Sandbox: Reset
# ---------------------------------------------------------------------------


class TestSandboxReset:
    def test_reset_module_import(self):
        """Reset module should be importable."""
        from forge.sandbox import reset

        assert hasattr(reset, "reset_workspace")


# ---------------------------------------------------------------------------
# Runner: Lifecycle
# ---------------------------------------------------------------------------


class TestRunnerLifecycle:
    def test_lifecycle_module_import(self):
        """Lifecycle module should be importable."""
        from forge.runner import lifecycle

        assert hasattr(lifecycle, "RunLifecycle")

    def test_run_lifecycle_states(self):
        """RunLifecycle should track state transitions."""
        from forge.core.schemas import RunStatus
        from forge.runner.lifecycle import RunConfig, RunLifecycle

        config = RunConfig(task_id="t-1", agent_id="mock")
        lifecycle = RunLifecycle(config)
        assert lifecycle.get_status() == RunStatus.PENDING
        lifecycle.start()
        assert lifecycle.get_status() == RunStatus.RUNNING


# ---------------------------------------------------------------------------
# Runner: Tool Executor
# ---------------------------------------------------------------------------


class TestRunnerToolExecutor:
    def test_tool_executor_module_import(self):
        """Tool executor module should be importable."""
        from forge.runner import tool_executor

        assert hasattr(tool_executor, "ToolExecutor")


# ---------------------------------------------------------------------------
# Diagnosis: Rules
# ---------------------------------------------------------------------------


class TestDiagnosisRules:
    def test_rules_module_import(self):
        """Rules module should be importable."""
        from forge.diagnosis import rules

        assert hasattr(rules, "DiagnosisRule")

    def test_agent_failure_rule(self):
        """AgentFailureRule should be instantiable."""
        from forge.diagnosis.rules import AgentFailureRule

        rule = AgentFailureRule()
        assert rule is not None


# ---------------------------------------------------------------------------
# Diagnosis: Triage
# ---------------------------------------------------------------------------


class TestDiagnosisTriage:
    def test_triage_module_import(self):
        """Triage module should be importable."""
        from forge.diagnosis import triage

        assert hasattr(triage, "EvidenceCollector")


# ---------------------------------------------------------------------------
# Diagnosis: Report
# ---------------------------------------------------------------------------


class TestDiagnosisReport:
    def test_report_module_import(self):
        """Report module should be importable."""
        from forge.diagnosis import report

        assert hasattr(report, "FailureDiagnosis")

    def test_failure_diagnosis(self):
        """FailureDiagnosis should be instantiable."""
        from forge.core.schemas import FailureCategory
        from forge.diagnosis.report import FailureDiagnosis

        diag = FailureDiagnosis(
            run_id="r-1",
            primary_category=FailureCategory.AGENT_FAILURE,
            confidence=0.8,
        )
        assert diag.confidence == 0.8


# ---------------------------------------------------------------------------
# Evaluation: Metrics
# ---------------------------------------------------------------------------


class TestEvaluationMetrics:
    def test_metrics_module_import(self):
        """Metrics module should be importable."""
        from forge.evaluation import metrics

        # Module exists and is importable
        assert metrics is not None

    def test_metrics_module_has_types(self):
        """Metrics module should define compute_metrics_summary."""
        from forge.evaluation.metrics import compute_metrics_summary

        assert callable(compute_metrics_summary)


# ---------------------------------------------------------------------------
# Evaluation: Scoring
# ---------------------------------------------------------------------------


class TestEvaluationScoring:
    def test_scoring_module_import(self):
        """Scoring module should be importable."""
        from forge.evaluation import scoring

        assert hasattr(scoring, "EvaluationReport")

    def test_evaluation_report(self):
        """EvaluationReport should be instantiable."""
        from forge.evaluation.scoring import EvaluationReport

        report = EvaluationReport()
        assert report is not None


# ---------------------------------------------------------------------------
# Evaluation: Reports
# ---------------------------------------------------------------------------


class TestEvaluationReports:
    def test_reports_module_import(self):
        """Reports module should be importable."""
        from forge.evaluation import reports

        # Module exists and is importable
        assert reports is not None


# ---------------------------------------------------------------------------
# Curriculum: Difficulty
# ---------------------------------------------------------------------------


class TestCurriculumDifficulty:
    def test_difficulty_module_import(self):
        """Difficulty module should be importable."""
        from forge.curriculum import difficulty

        # Module exists and is importable
        assert difficulty is not None


# ---------------------------------------------------------------------------
# Curriculum: History
# ---------------------------------------------------------------------------


class TestCurriculumHistory:
    def test_history_module_import(self):
        """History module should be importable."""
        from forge.curriculum import history

        assert hasattr(history, "CurriculumHistory")

    def test_curriculum_history(self):
        """CurriculumHistory should be instantiable."""
        from forge.curriculum.history import CurriculumHistory

        hist = CurriculumHistory()
        assert hist is not None


# ---------------------------------------------------------------------------
# Curriculum: Updater
# ---------------------------------------------------------------------------


class TestCurriculumUpdater:
    def test_updater_module_import(self):
        """Updater module should be importable."""
        from forge.curriculum import updater

        assert hasattr(updater, "CurriculumUpdater")


# ---------------------------------------------------------------------------
# Experiments: Artifacts
# ---------------------------------------------------------------------------


class TestExperimentsArtifacts:
    def test_artifacts_module_import(self):
        """Artifacts module should be importable."""
        from forge.experiments import artifacts

        assert hasattr(artifacts, "ArtifactManager")


# ---------------------------------------------------------------------------
# Experiments: Comparison
# ---------------------------------------------------------------------------


class TestExperimentsComparison:
    def test_comparison_module_import(self):
        """Comparison module should be importable."""
        from forge.experiments import comparison

        assert hasattr(comparison, "compare_experiments")

    def test_compare_experiments(self):
        """Should compare two experiments."""
        from forge.core.schemas import RunResult, RunStatus
        from forge.experiments.comparison import compare_experiments

        runs_a = [RunResult(run_id="r1", task_id="t1", agent_id="a1", status=RunStatus.COMPLETED)]
        runs_b = [RunResult(run_id="r2", task_id="t1", agent_id="a1", status=RunStatus.COMPLETED)]
        result = compare_experiments(runs_a, runs_b)
        assert result is not None


# ---------------------------------------------------------------------------
# CLI: DB commands
# ---------------------------------------------------------------------------


class TestCLIDBCommands:
    def test_db_subcommand_exists(self):
        """CLI should have a 'db' subcommand."""
        from forge.cli import db_app

        assert db_app is not None

    def test_db_upgrade_command_exists(self):
        """CLI should have a 'db upgrade' command."""
        from forge.cli import db_app

        # Check the command is registered
        commands = db_app.registered_commands
        command_names = [c.name for c in commands]
        assert "db-upgrade" in command_names or "upgrade" in command_names

    def test_db_current_command_exists(self):
        """CLI should have a 'db current' command."""
        from forge.cli import db_app

        commands = db_app.registered_commands
        command_names = [c.name for c in commands]
        assert "db-current" in command_names or "current" in command_names
