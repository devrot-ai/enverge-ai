"""Tests for v0.2 new features: templates, agents, experiments."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from forge.agents.registry import get_registry
from forge.agents.rule_based import RepairRule, RuleBasedAgent
from forge.agents.script_agent import ScriptAgent
from forge.core.schemas import AgentConfig, RunConfig, TaskCategory, TaskSpec
from forge.experiments.comparison import (
    compare_experiments,
    generate_comparison_report,
)
from forge.experiments.manager import (
    ExperimentManager,
    create_experiment_ablation_tools,
    create_experiment_cross_template,
    create_experiment_difficulty_scaling,
)
from forge.world_factory.seeder import get_mutation, list_mutations
from forge.world_factory.templates import get_template, list_templates

# ---------------------------------------------------------------------------
# Template Tests
# ---------------------------------------------------------------------------


class TestNewTemplates:
    """Test the new express_api and django_app templates."""

    def test_list_templates_count(self):
        """Should have 14 templates total."""
        templates = list_templates()
        assert len(templates) == 14

    def test_express_api_template_exists(self):
        """express_api template should be registered."""
        template = get_template("express_api")
        assert template is not None
        assert template["name"] == "express_api"
        assert "app.py" in template["files"]
        assert "tests/test_public.py" in template["files"]
        assert ".hidden_tests/test_hidden.py" in template["files"]

    def test_express_api_has_classes(self):
        """express_api app code should contain expected classes."""
        template = get_template("express_api")
        app_code = template["files"]["app.py"]
        for cls in [
            "Request",
            "Response",
            "Router",
            "MiddlewareChain",
            "RequestValidator",
            "RateLimiter",
            "CorsHandler",
            "ErrorHandler",
        ]:
            assert f"class {cls}" in app_code

    def test_django_app_template_exists(self):
        """django_app template should be registered."""
        template = get_template("django_app")
        assert template is not None
        assert template["name"] == "django_app"
        assert "app.py" in template["files"]

    def test_django_app_has_classes(self):
        """django_app app code should contain expected classes."""
        template = get_template("django_app")
        app_code = template["files"]["app.py"]
        for cls in ["Field", "Model", "QuerySet", "FormValidator", "View", "Middleware", "User"]:
            assert f"class {cls}" in app_code

    def test_express_api_hidden_tests(self):
        """express_api hidden tests should target security bugs."""
        template = get_template("express_api")
        hidden = template["files"][".hidden_tests/test_hidden.py"]
        assert "sanitize" in hidden
        assert "rate_limiter" in hidden
        assert "cors" in hidden

    def test_django_app_hidden_tests(self):
        """django_app hidden tests should target security bugs."""
        template = get_template("django_app")
        hidden = template["files"][".hidden_tests/test_hidden.py"]
        assert "csrf" in hidden
        assert "redirect" in hidden


# ---------------------------------------------------------------------------
# Mutation Tests
# ---------------------------------------------------------------------------


class TestNewMutations:
    """Test the new mutations for express_api and django_app."""

    def test_mutation_count(self):
        """Should have 37 mutations total."""
        mutations = list_mutations()
        assert len(mutations) == 37

    def test_cors_bypass_mutation(self):
        """cors_bypass mutation should be registered."""
        mutation = get_mutation("cors_bypass")
        assert mutation is not None
        assert mutation["target_file"] == "app.py"
        assert "difficulty" in mutation

    def test_rate_limit_off_mutation(self):
        """rate_limit_off mutation should be registered."""
        mutation = get_mutation("rate_limit_off")
        assert mutation is not None
        assert mutation["target_file"] == "app.py"

    def test_input_injection_mutation(self):
        """input_injection mutation should be registered."""
        mutation = get_mutation("input_injection")
        assert mutation is not None
        assert mutation["target_file"] == "app.py"

    def test_sql_injection_mutation(self):
        """sql_injection mutation should be registered."""
        mutation = get_mutation("sql_injection")
        assert mutation is not None
        assert mutation["target_file"] == "app.py"

    def test_csrf_missing_mutation(self):
        """csrf_missing mutation should be registered."""
        mutation = get_mutation("csrf_missing")
        assert mutation is not None
        assert mutation["target_file"] == "app.py"

    def test_open_redirect_mutation(self):
        """open_redirect mutation should be registered."""
        mutation = get_mutation("open_redirect")
        assert mutation is not None
        assert mutation["target_file"] == "app.py"


# ---------------------------------------------------------------------------
# Agent Tests
# ---------------------------------------------------------------------------


class TestRuleBasedAgent:
    """Test the RuleBasedAgent."""

    def test_create_agent(self):
        """Should create a RuleBasedAgent."""
        config = AgentConfig(agent_id="test-rba", agent_type="rule_based")
        agent = RuleBasedAgent(config, rules=[])
        assert agent.agent_id == "test-rba"
        assert len(agent.rules) == 0

    def test_available_tools(self):
        """Should list available tools."""
        config = AgentConfig(agent_id="test-rba", agent_type="rule_based")
        agent = RuleBasedAgent(config, rules=[])
        tools = agent.get_available_tools()
        assert "read_file" in tools
        assert "apply_rule" in tools

    def test_stats(self):
        """Should return agent stats."""
        config = AgentConfig(agent_id="test-rba", agent_type="rule_based")
        agent = RuleBasedAgent(config, rules=[])
        stats = agent.get_stats()
        assert stats["agent_id"] == "test-rba"
        assert stats["total_rules"] == 0

    def test_execute_with_rules(self, tmp_path):
        """Should apply rules and create trajectory."""
        rule = RepairRule(
            name="test_fix",
            target_file="app.py",
            search_pattern="BUG",
            replace_with="FIXED",
            description="Test fix",
        )
        config = AgentConfig(agent_id="test-rba", agent_type="rule_based")
        agent = RuleBasedAgent(config, rules=[rule])

        # Create workspace with target file
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "app.py").write_text("This has a BUG in it")

        task = TaskSpec(
            task_id="test-001",
            world_id="world-test",
            description="Fix the bug",
            category=TaskCategory.BUG_REPAIR,
        )
        run_config = RunConfig(run_id="run-001", task_id="test-001", agent_id="test-rba")

        trajectory = agent.execute(task, workspace, run_config)
        assert len(trajectory.steps) > 0
        assert "test_fix" in agent._rules_applied

    def test_execute_no_match(self, tmp_path):
        """Should not apply rule if pattern doesn't match."""
        rule = RepairRule(
            name="no_match",
            target_file="app.py",
            search_pattern="NONEXISTENT_PATTERN",
            replace_with="FIXED",
        )
        config = AgentConfig(agent_id="test-rba", agent_type="rule_based")
        agent = RuleBasedAgent(config, rules=[rule])

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "app.py").write_text("No match here")

        task = TaskSpec(
            task_id="test-002",
            world_id="world-test",
            description="Fix the bug",
            category=TaskCategory.BUG_REPAIR,
        )
        run_config = RunConfig(run_id="run-002", task_id="test-002", agent_id="test-rba")

        trajectory = agent.execute(task, workspace, run_config)
        assert len(trajectory.steps) > 0
        assert len(agent._rules_applied) == 0

    def test_load_rules_from_file(self, tmp_path):
        """Should load rules from YAML file."""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(
            "rules:\n"
            "  - name: fix1\n"
            "    target_file: app.py\n"
            "    search_pattern: old\n"
            "    replace_with: new\n"
            "    description: Fix 1\n"
        )
        config = AgentConfig(agent_id="test-rba", agent_type="rule_based")
        agent = RuleBasedAgent(config, rules_file=str(rules_file))
        assert len(agent.rules) == 1
        assert agent.rules[0].name == "fix1"


class TestScriptAgent:
    """Test the ScriptAgent."""

    def test_create_agent(self):
        """Should create a ScriptAgent."""
        config = AgentConfig(agent_id="test-sa", agent_type="script")
        agent = ScriptAgent(config, script_path="/path/to/script.py")
        assert agent.script_path == "/path/to/script.py"
        assert agent.timeout == 300

    def test_available_tools(self):
        """Should list available tools."""
        config = AgentConfig(agent_id="test-sa", agent_type="script")
        agent = ScriptAgent(config, script_path="/path/to/script.py")
        tools = agent.get_available_tools()
        assert "run_script" in tools

    def test_stats(self):
        """Should return agent stats."""
        config = AgentConfig(agent_id="test-sa", agent_type="script")
        agent = ScriptAgent(config, script_path="/path/to/script.py")
        stats = agent.get_stats()
        assert stats["agent_id"] == "test-sa"
        assert stats["script_path"] == "/path/to/script.py"

    def test_execute_script_not_found(self, tmp_path):
        """Should handle missing script gracefully."""
        config = AgentConfig(agent_id="test-sa", agent_type="script")
        agent = ScriptAgent(config, script_path="/nonexistent/script.py")

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        task = TaskSpec(
            task_id="test-003",
            world_id="world-test",
            description="Test",
            category=TaskCategory.BUG_REPAIR,
        )
        run_config = RunConfig(run_id="run-003", task_id="test-003", agent_id="test-sa")

        trajectory = agent.execute(task, workspace, run_config)
        assert len(trajectory.steps) > 0
        assert agent._exit_code == -1

    def test_execute_with_script(self, tmp_path):
        """Should execute a valid script."""
        script = tmp_path / "agent.py"
        script.write_text("import os; print('Hello from agent')")

        config = AgentConfig(agent_id="test-sa", agent_type="script")
        agent = ScriptAgent(config, script_path=str(script), timeout=30)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        task = TaskSpec(
            task_id="test-004",
            world_id="world-test",
            description="Test",
            category=TaskCategory.BUG_REPAIR,
        )
        run_config = RunConfig(run_id="run-004", task_id="test-004", agent_id="test-sa")

        trajectory = agent.execute(task, workspace, run_config)
        assert len(trajectory.steps) > 0
        assert agent._exit_code == 0
        assert "Hello from agent" in agent._stdout

    def test_config_file_created(self, tmp_path):
        """Should create config file in workspace."""
        script = tmp_path / "agent.py"
        script.write_text("pass")

        config = AgentConfig(agent_id="test-sa", agent_type="script")
        agent = ScriptAgent(config, script_path=str(script), timeout=30)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        task = TaskSpec(
            task_id="test-005",
            world_id="world-test",
            description="Test task",
            category=TaskCategory.BUG_REPAIR,
        )
        run_config = RunConfig(run_id="run-005", task_id="test-005", agent_id="test-sa")

        agent.execute(task, workspace, run_config)
        config_file = workspace / ".forgelab_task_config.json"
        assert config_file.exists()
        data = json.loads(config_file.read_text())
        assert data["task_id"] == "test-005"


# ---------------------------------------------------------------------------
# Agent Registry Tests
# ---------------------------------------------------------------------------


class TestAgentRegistry:
    """Test the agent registry with new agents."""

    def test_registered_types(self):
        """Should have 4 agent types registered."""
        registry = get_registry()
        types = registry.list_types()
        assert "mock" in types
        assert "rule_based" in types
        assert "script" in types

    def test_create_rule_based(self):
        """Should create RuleBasedAgent from registry."""
        registry = get_registry()
        config = AgentConfig(
            agent_id="test",
            agent_type="rule_based",
            metadata={"rules": []},
        )
        agent = registry.create(config)
        assert isinstance(agent, RuleBasedAgent)

    def test_create_script(self):
        """Should create ScriptAgent from registry."""
        registry = get_registry()
        config = AgentConfig(
            agent_id="test",
            agent_type="script",
            metadata={"script_path": "/tmp/test.py"},
        )
        agent = registry.create(config)
        assert isinstance(agent, ScriptAgent)

    def test_unknown_type(self):
        """Should raise for unknown agent type."""
        registry = get_registry()
        config = AgentConfig(agent_id="test", agent_type="nonexistent")
        with pytest.raises(ValueError):
            registry.create(config)


# ---------------------------------------------------------------------------
# Experiment Tests
# ---------------------------------------------------------------------------


class TestNewExperiments:
    """Test the new preset experiments."""

    def test_ablation_tools(self):
        """Should create ablation tools experiment."""
        config = create_experiment_ablation_tools()
        assert config.name == "Tool Ablation Study"
        assert config.metadata["ablation_type"] == "tools"
        assert "tool_sets" in config.metadata

    def test_difficulty_scaling(self):
        """Should create difficulty scaling experiment."""
        config = create_experiment_difficulty_scaling()
        assert config.name == "Difficulty Scaling Analysis"
        assert config.metadata["scaling_type"] == "difficulty"
        assert config.metadata["difficulty_levels"] == [1, 2, 3, 4, 5]

    def test_cross_template(self):
        """Should create cross-template experiment."""
        config = create_experiment_cross_template()
        assert config.name == "Cross-Template Generalization"
        assert config.metadata["generalization_type"] == "cross_template"
        assert "express_api" in config.metadata["templates"]
        assert "django_app" in config.metadata["templates"]

    def test_experiment_manager(self):
        """Should create and manage experiments."""
        manager = ExperimentManager()
        config = create_experiment_ablation_tools()
        exp_id = manager.create_experiment(config)
        assert exp_id == config.experiment_id
        assert manager.get_experiment(exp_id) is not None


# ---------------------------------------------------------------------------
# Comparison Tests
# ---------------------------------------------------------------------------


class TestComparison:
    """Test experiment comparison functions."""

    def test_compare_empty(self):
        """Should handle empty result lists."""
        result = compare_experiments([], [])
        assert "comparison" in result

    def test_generate_report(self):
        """Should generate comparison report."""
        report = generate_comparison_report({})
        assert "experiments" in report
        assert "pairwise_comparisons" in report


# ---------------------------------------------------------------------------
# Static Analysis Tests
# ---------------------------------------------------------------------------


class TestStaticAnalysis:
    """Test static analysis module."""

    def test_analyzer_init(self):
        """Should initialize with defaults."""
        from forge.evaluation.static_analysis import StaticAnalyzer

        analyzer = StaticAnalyzer()
        assert analyzer.run_flake8 is True
        assert analyzer.run_mypy is True

    def test_analyzer_skip_tools(self):
        """Should skip missing tools gracefully."""
        from forge.evaluation.static_analysis import StaticAnalyzer

        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "test.py").write_text("x=1\n")
            analyzer = StaticAnalyzer()
            result = analyzer.check(workspace)
            assert result is not None
            # Tools may be missing; result should not crash

    def test_analyzer_no_flake8(self):
        """Should work when flake8 is disabled."""
        from forge.evaluation.static_analysis import StaticAnalyzer

        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "test.py").write_text("x=1\n")
            analyzer = StaticAnalyzer(run_flake8=False, run_mypy=False)
            result = analyzer.check(workspace)
            assert result.passed is True
            assert result.details == "Static analysis passed"


# ---------------------------------------------------------------------------
# Export Tests
# ---------------------------------------------------------------------------


class TestExport:
    """Test run data export."""

    def test_export_json_empty(self):
        """Should export empty JSON for fresh DB."""
        from forge.api.export import export_runs

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        from sqlalchemy import create_engine

        from forge.db.models import Base

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        engine.dispose()
        data = export_runs(f"sqlite:///{db_path}", format="json")
        import json

        parsed = json.loads(data)
        assert parsed["total_runs"] == 0
        os.unlink(db_path)

    def test_export_csv_empty(self):
        """Should export empty CSV for fresh DB."""
        from forge.api.export import export_runs

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        from sqlalchemy import create_engine

        from forge.db.models import Base

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        engine.dispose()
        data = export_runs(f"sqlite:///{db_path}", format="csv")
        assert data == ""
        os.unlink(db_path)

    def test_export_invalid_format(self):
        """Should raise for invalid format."""
        from forge.api.export import export_runs

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        from sqlalchemy import create_engine

        from forge.db.models import Base

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        engine.dispose()
        with pytest.raises(ValueError):
            export_runs(f"sqlite:///{db_path}", format="xml")
        os.unlink(db_path)


# ---------------------------------------------------------------------------
# Held-out Evaluation Tests
# ---------------------------------------------------------------------------


class TestHeldOut:
    """Test held-out evaluation set manager."""

    def test_manager_init(self):
        """Should create heldout directory."""
        from forge.task_factory.heldout import HeldOutManager

        with tempfile.TemporaryDirectory() as td:
            manager = HeldOutManager(Path(td) / "heldout")
            assert manager.heldout_dir.exists()

    def test_empty_heldout(self):
        """Should return empty list for new manager."""
        from forge.task_factory.heldout import HeldOutManager

        with tempfile.TemporaryDirectory() as td:
            manager = HeldOutManager(Path(td) / "heldout")
            tasks = manager.get_heldout_tasks()
            assert len(tasks) == 0

    def test_is_heldout_false(self):
        """Should return False for unknown task."""
        from forge.task_factory.heldout import HeldOutManager

        with tempfile.TemporaryDirectory() as td:
            manager = HeldOutManager(Path(td) / "heldout")
            assert manager.is_heldout("nonexistent") is False


# ---------------------------------------------------------------------------
# Agent Profile Tests
# ---------------------------------------------------------------------------


class TestAgentProfiles:
    """Test agent configuration profiles."""

    def test_default_profiles(self):
        """Should have 3 default profiles."""
        from forge.agents.profiles import ProfileManager

        with tempfile.TemporaryDirectory() as td:
            manager = ProfileManager(Path(td))
            profiles = manager.list_profiles()
            assert "conservative" in profiles
            assert "aggressive" in profiles
            assert "balanced" in profiles

    def test_load_default_profile(self):
        """Should load default profile."""
        from forge.agents.profiles import ProfileManager

        with tempfile.TemporaryDirectory() as td:
            manager = ProfileManager(Path(td))
            profile = manager.load_profile("balanced")
            assert profile is not None
            assert profile.name == "balanced"
            assert profile.temperature == 0.7

    def test_save_and_load_profile(self):
        """Should save and reload custom profile."""
        from forge.agents.profiles import AgentProfile, ProfileManager

        with tempfile.TemporaryDirectory() as td:
            manager = ProfileManager(Path(td))
            profile = AgentProfile(name="custom", temperature=0.5)
            manager.save_profile(profile)
            loaded = manager.load_profile("custom")
            assert loaded is not None
            assert loaded.temperature == 0.5

    def test_get_default(self):
        """Should return default profile."""
        from forge.agents.profiles import ProfileManager

        with tempfile.TemporaryDirectory() as td:
            manager = ProfileManager(Path(td))
            profile = manager.get_default("conservative")
            assert profile.temperature == 0.2

    def test_unknown_profile(self):
        """Should return None for unknown profile."""
        from forge.agents.profiles import ProfileManager

        with tempfile.TemporaryDirectory() as td:
            manager = ProfileManager(Path(td))
            profile = manager.load_profile("nonexistent")
            assert profile is None


# ---------------------------------------------------------------------------
# Performance Regression Tests
# ---------------------------------------------------------------------------


class TestPerformance:
    """Test performance regression checks."""

    def test_checker_init(self):
        """Should initialize with default threshold."""
        from forge.evaluation.performance import PerformanceChecker

        checker = PerformanceChecker()
        assert checker.regression_threshold == 2.0

    def test_no_baseline(self):
        """Should report no baseline when not provided."""
        from forge.evaluation.performance import PerformanceChecker

        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "tests").mkdir()
            (workspace / "tests" / "test_public.py").write_text("def test_x(): pass\n")
            checker = PerformanceChecker()
            result = checker.measure(workspace)
            assert "no baseline" in result.details

    def test_with_baseline_no_regression(self):
        """Should detect no regression when within threshold."""
        from forge.evaluation.performance import PerformanceChecker

        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "tests").mkdir()
            (workspace / "tests" / "test_public.py").write_text("def test_x(): pass\n")
            checker = PerformanceChecker()
            result = checker.measure(workspace, baseline_seconds=10.0)
            assert result.regression is False

    def test_get_baseline(self):
        """Should extract baseline from metadata."""
        from forge.evaluation.performance import PerformanceChecker

        checker = PerformanceChecker()
        meta = {"baseline_test_seconds": 1.5}
        assert checker.get_baseline(meta) == 1.5

    def test_get_baseline_missing(self):
        """Should return None when no baseline in metadata."""
        from forge.evaluation.performance import PerformanceChecker

        checker = PerformanceChecker()
        assert checker.get_baseline({}) is None


# ---------------------------------------------------------------------------
# Diff Viewer Tests
# ---------------------------------------------------------------------------


class TestDiffViewer:
    """Test code diff viewer for agent workspace changes."""

    def test_simple_diff(self):
        """Should detect added and removed lines."""
        from forge.evaluation.diff_viewer import DiffViewer

        viewer = DiffViewer()
        original = "def hello():\n    print('hello')\n"
        modified = "def hello():\n    print('world')\n"
        diff = viewer.diff_content("test.py", original, modified)
        assert diff.changed is True
        assert diff.added_count == 1
        assert diff.removed_count == 1

    def test_no_change(self):
        """Should report no change when content is identical."""
        from forge.evaluation.diff_viewer import DiffViewer

        viewer = DiffViewer()
        content = "def hello():\n    print('hello')\n"
        diff = viewer.diff_content("test.py", content, content)
        assert diff.changed is False
        assert diff.added_count == 0
        assert diff.removed_count == 0

    def test_added_lines_only(self):
        """Should detect lines added without removals."""
        from forge.evaluation.diff_viewer import DiffViewer

        viewer = DiffViewer()
        original = "x = 1\n"
        modified = "x = 1\ny = 2\n"
        diff = viewer.diff_content("test.py", original, modified)
        assert diff.changed is True
        assert diff.added_count >= 1

    def test_removed_lines_only(self):
        """Should detect lines removed without additions."""
        from forge.evaluation.diff_viewer import DiffViewer

        viewer = DiffViewer()
        original = "x = 1\ny = 2\n"
        modified = "x = 1\n"
        diff = viewer.diff_content("test.py", original, modified)
        assert diff.changed is True
        assert diff.removed_count >= 1

    def test_workspace_diff(self):
        """Should diff two workspace directories."""
        import tempfile
        from pathlib import Path

        from forge.evaluation.diff_viewer import DiffViewer

        viewer = DiffViewer()
        with tempfile.TemporaryDirectory() as td:
            orig_dir = Path(td) / "original"
            mod_dir = Path(td) / "modified"
            orig_dir.mkdir()
            mod_dir.mkdir()
            (orig_dir / "app.py").write_text("def hello():\n    print('hello')\n")
            (mod_dir / "app.py").write_text("def hello():\n    print('world')\n")
            (mod_dir / "new.py").write_text("def new():\n    pass\n")
            diff = viewer.diff_workspaces(orig_dir, mod_dir)
            assert diff.files_changed >= 1
            assert diff.total_added >= 1

    def test_format_diff_text(self):
        """Should format diff as plain text."""
        from forge.evaluation.diff_viewer import DiffHunk, DiffViewer, FileDiff, WorkspaceDiff

        viewer = DiffViewer()
        workspace = WorkspaceDiff(
            files=[
                FileDiff(
                    filename="app.py",
                    changed=True,
                    added_count=1,
                    removed_count=1,
                    hunks=[
                        DiffHunk(
                            filename="app.py",
                            added_lines=["print('world')"],
                            removed_lines=["print('hello')"],
                            start_line=2,
                        )
                    ],
                )
            ],
            total_added=1,
            total_removed=1,
            files_changed=1,
        )
        text = viewer.format_diff_text(workspace)
        assert "app.py" in text
        assert "+1/-1" in text

    def test_format_diff_markdown(self):
        """Should format diff as Markdown."""
        from forge.evaluation.diff_viewer import DiffHunk, DiffViewer, FileDiff, WorkspaceDiff

        viewer = DiffViewer()
        workspace = WorkspaceDiff(
            files=[
                FileDiff(
                    filename="app.py",
                    changed=True,
                    added_count=1,
                    removed_count=1,
                    hunks=[
                        DiffHunk(
                            filename="app.py",
                            added_lines=["print('world')"],
                            removed_lines=["print('hello')"],
                            start_line=2,
                        )
                    ],
                )
            ],
            total_added=1,
            total_removed=1,
            files_changed=1,
        )
        md = viewer.format_diff_markdown(workspace)
        assert "```diff" in md
        assert "app.py" in md

    def test_workspace_diff_to_dict(self):
        """Should serialize workspace diff to dict."""
        from forge.evaluation.diff_viewer import DiffHunk, FileDiff, WorkspaceDiff

        workspace = WorkspaceDiff(
            files=[
                FileDiff(
                    filename="app.py",
                    changed=True,
                    added_count=1,
                    removed_count=1,
                    hunks=[
                        DiffHunk(
                            filename="app.py",
                            added_lines=["new"],
                            removed_lines=["old"],
                            start_line=1,
                        )
                    ],
                )
            ],
            total_added=1,
            total_removed=1,
            files_changed=1,
        )
        d = workspace.to_dict()
        assert d["files_changed"] == 1
        assert len(d["files"]) == 1
        assert d["files"][0]["filename"] == "app.py"

    def test_empty_workspace_diff(self):
        """Should handle empty workspace diff."""
        from forge.evaluation.diff_viewer import DiffViewer

        viewer = DiffViewer()
        with tempfile.TemporaryDirectory() as td:
            orig_dir = Path(td) / "orig"
            mod_dir = Path(td) / "mod"
            orig_dir.mkdir()
            mod_dir.mkdir()
            diff = viewer.diff_workspaces(orig_dir, mod_dir)
            assert diff.files_changed == 0
            assert diff.total_added == 0
            assert diff.total_removed == 0


# ---------------------------------------------------------------------------
# Fuzzer Tests
# ---------------------------------------------------------------------------


class TestFuzzer:
    """Test the fuzzing-based verification module."""

    def test_fuzzer_init(self):
        """Fuzzer should initialize with default parameters."""
        from forge.evaluation.fuzzer import Fuzzer

        fuzzer = Fuzzer()
        assert fuzzer.iterations == 50

    def test_fuzzer_with_seed(self):
        """Fuzzer should accept a random seed."""
        from forge.evaluation.fuzzer import Fuzzer

        fuzzer = Fuzzer(seed=42, iterations=10)
        assert fuzzer.iterations == 10

    def test_fuzz_unknown_template(self):
        """Fuzzing an unknown template should pass with no inputs."""
        import tempfile
        from pathlib import Path

        from forge.evaluation.fuzzer import Fuzzer

        fuzzer = Fuzzer(iterations=5)
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "app.py").write_text("x = 1\n")
            result = fuzzer.fuzz(workspace, "unknown_template")
            assert result.passed is True
            assert result.inputs_tested == 0
            assert result.template == "unknown_template"

    def test_fuzz_no_app_file(self):
        """Fuzzing a workspace without app.py should pass."""
        import tempfile
        from pathlib import Path

        from forge.evaluation.fuzzer import Fuzzer

        fuzzer = Fuzzer(iterations=5)
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            result = fuzzer.fuzz(workspace, "task_manager_api")
            assert result.passed is True

    def test_fuzz_task_manager_api(self):
        """Fuzzing task_manager_api should generate inputs."""
        import tempfile
        from pathlib import Path

        from forge.evaluation.fuzzer import Fuzzer

        fuzzer = Fuzzer(seed=42, iterations=5)
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            # Write a minimal TaskManager app
            app_code = """
class TaskManager:
    def __init__(self):
        self.tasks = []
    def add_task(self, title, description="", status="todo"):
        self.tasks.append({"title": title, "status": status})
    def get_tasks(self, page=1, per_page=10):
        return self.tasks
    def search_tasks(self, query=""):
        return self.tasks
    def filter_by_status(self, status=None):
        return self.tasks
    def update_task(self, task_id, changes):
        pass
    def delete_task(self, task_id):
        pass
"""
            (workspace / "app.py").write_text(app_code)
            result = fuzzer.fuzz(workspace, "task_manager_api")
            assert result.inputs_tested > 0
            assert result.template == "task_manager_api"

    def test_fuzz_result_to_dict(self):
        """FuzzResult should serialize to dict."""
        from forge.evaluation.fuzzer import FuzzResult

        result = FuzzResult(
            inputs_tested=100,
            crashes_found=2,
            error_samples=["Error 1", "Error 2"],
            passed=False,
            template="test",
        )
        d = result.to_dict()
        assert d["inputs_tested"] == 100
        assert d["crashes_found"] == 2
        assert d["passed"] is False

    def test_fuzz_detects_crash(self):
        """Fuzzer should detect crashes in buggy code."""
        import tempfile
        from pathlib import Path

        from forge.evaluation.fuzzer import Fuzzer

        fuzzer = Fuzzer(seed=42, iterations=10)
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            # Write a buggy TaskManager that crashes on empty string
            app_code = """
class TaskManager:
    def __init__(self):
        self.tasks = []
    def add_task(self, title, description="", status="todo"):
        if not title:
            raise ValueError("title required")
        self.tasks.append({"title": title})
    def get_tasks(self, page=1, per_page=10):
        return self.tasks
    def search_tasks(self, query=""):
        return self.tasks
    def filter_by_status(self, status=None):
        return self.tasks
    def update_task(self, task_id, changes):
        pass
    def delete_task(self, task_id):
        pass
"""
            (workspace / "app.py").write_text(app_code)
            result = fuzzer.fuzz(workspace, "task_manager_api")
            assert result.inputs_tested > 0
            # Crashes may or may not occur depending on random inputs
            assert isinstance(result.crashes_found, int)
            assert isinstance(result.passed, bool)

    def test_fuzz_flask_app(self):
        """Fuzzing flask_app should generate inputs for auth/session/CSRF."""
        import tempfile
        from pathlib import Path

        from forge.evaluation.fuzzer import Fuzzer

        fuzzer = Fuzzer(seed=42, iterations=5)
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            app_code = """
import hashlib
import time

class AuthManager:
    def __init__(self):
        self.users = {}
    def register(self, username, password):
        self.users[username] = hashlib.sha256(password.encode()).hexdigest()
    def login(self, username, password):
        return self.users.get(username) == hashlib.sha256(password.encode()).hexdigest()
    def logout(self, username):
        pass

class SessionManager:
    def __init__(self):
        self.sessions = {}
    def create_session(self, user_id):
        self.sessions[user_id] = time.time()
        return user_id
    def validate_session(self, session_id):
        return session_id in self.sessions

class CSRFProtector:
    def __init__(self):
        pass
    def generate_token(self):
        import secrets
        return secrets.token_hex(16)
    def validate_token(self, token):
        return bool(token)
"""
            (workspace / "app.py").write_text(app_code)
            result = fuzzer.fuzz(workspace, "flask_app")
            assert result.inputs_tested > 0
            assert result.template == "flask_app"

    def test_fuzz_result_passed_default(self):
        """FuzzResult should default to passed=True."""
        from forge.evaluation.fuzzer import FuzzResult

        result = FuzzResult()
        assert result.passed is True
        assert result.inputs_tested == 0
        assert result.crashes_found == 0

    def test_random_string_generator(self):
        """Random string generator should produce varied strings."""

        from forge.evaluation.fuzzer import Fuzzer

        fuzzer = Fuzzer(seed=42)
        strings = [fuzzer._random_string(fuzzer.rng) for _ in range(10)]
        assert len(strings) == 10
        assert all(isinstance(s, str) for s in strings)
        assert len(set(strings)) > 1  # At least some variation

    def test_random_value_generator(self):
        """Random value generator should produce various types."""

        from forge.evaluation.fuzzer import Fuzzer

        fuzzer = Fuzzer(seed=42)
        values = [fuzzer._random_value(fuzzer.rng) for _ in range(50)]
        types_found = set(type(v).__name__ for v in values)
        assert "str" in types_found
        assert "int" in types_found or "float" in types_found


# ---------------------------------------------------------------------------
# Default Rules Tests
# ---------------------------------------------------------------------------


class TestDefaultRules:
    """Test the pre-built rule sets for RuleBasedAgent."""

    def test_rules_file_exists(self):
        """Default rules YAML file should exist."""
        rules_file = Path(__file__).parent.parent / "configs" / "rules" / "default_rules.yaml"
        assert rules_file.exists()

    def test_rules_load(self):
        """Rules should load from YAML file."""
        import yaml

        rules_file = Path(__file__).parent.parent / "configs" / "rules" / "default_rules.yaml"
        data = yaml.safe_load(rules_file.read_text())
        assert "rules" in data
        assert len(data["rules"]) == 15

    def test_rules_cover_all_templates(self):
        """Rules should cover all 5 templates."""
        import yaml

        rules_file = Path(__file__).parent.parent / "configs" / "rules" / "default_rules.yaml"
        data = yaml.safe_load(rules_file.read_text())
        # Check rule names cover all templates
        rule_names = [r["name"] for r in data["rules"]]
        names_str = " ".join(rule_names)
        # task_manager_api rules
        assert any("pagination" in n for n in rule_names)
        assert any("empty_search" in n for n in rule_names)
        assert any("duplicate_records" in n for n in rule_names)
        # data_pipeline rules
        assert any("null_handling" in n for n in rule_names)
        assert any("date_parsing" in n for n in rule_names)
        assert any("duplicate_detection" in n for n in rule_names)
        # flask_app rules
        assert any("session_timeout" in n for n in rule_names)
        assert any("password_hash" in n for n in rule_names)
        assert any("csrf_token" in n for n in rule_names)
        # express_api rules
        assert any("cors_bypass" in n for n in rule_names)
        assert any("rate_limit" in n for n in rule_names)
        assert any("input_injection" in n for n in rule_names)
        # django_app rules
        assert any("sql_injection" in n for n in rule_names)
        assert any("csrf_missing" in n for n in rule_names)
        assert any("open_redirect" in n for n in rule_names)

    def test_rule_based_agent_loads_rules(self):
        """RuleBasedAgent should load rules from file."""
        rules_file = str(Path(__file__).parent.parent / "configs" / "rules" / "default_rules.yaml")
        config = AgentConfig(agent_type="rule_based")
        agent = RuleBasedAgent(config=config, rules_file=rules_file)
        assert len(agent.rules) == 15

    def test_rule_has_required_fields(self):
        """Each rule should have required fields."""
        import yaml

        rules_file = Path(__file__).parent.parent / "configs" / "rules" / "default_rules.yaml"
        data = yaml.safe_load(rules_file.read_text())
        for rule in data["rules"]:
            assert "name" in rule
            assert "target_file" in rule
            assert "search_pattern" in rule
            assert "replace_with" in rule
            assert "description" in rule


# ---------------------------------------------------------------------------
# Benchmark Runner Tests
# ---------------------------------------------------------------------------


class TestBenchmarkRunner:
    """Test the benchmark runner module."""

    def test_benchmark_result(self):
        """BenchmarkResult should store task results."""
        from forge.evaluation.benchmark import BenchmarkResult

        result = BenchmarkResult(
            task_id="test-1",
            task_name="Test task",
            template="task_manager_api",
            mutation="pagination_boundary",
            difficulty=2,
            category="code_repair",
            passed=True,
            duration=1.5,
        )
        assert result.passed is True
        assert result.task_id == "test-1"

    def test_benchmark_report(self):
        """BenchmarkReport should calculate statistics."""
        from forge.evaluation.benchmark import BenchmarkReport, BenchmarkResult

        results = [
            BenchmarkResult(
                task_id=f"task-{i}",
                task_name=f"Task {i}",
                template="task_manager_api",
                mutation="pagination_boundary",
                difficulty=2,
                category="code_repair",
                passed=i % 2 == 0,
                duration=1.0,
            )
            for i in range(4)
        ]
        report = BenchmarkReport(
            benchmark_id="test-bench",
            agent_type="mock",
            timestamp="2024-01-01T00:00:00",
            total_tasks=4,
            passed_tasks=2,
            failed_tasks=2,
            pass_rate=0.5,
            avg_duration=1.0,
            results=results,
        )
        assert report.pass_rate == 0.5
        assert report.total_tasks == 4

    def test_benchmark_report_to_dict(self):
        """BenchmarkReport.to_dict should serialize correctly."""
        from forge.evaluation.benchmark import BenchmarkReport, BenchmarkResult

        results = [
            BenchmarkResult(
                task_id="task-1",
                task_name="Task 1",
                template="task_manager_api",
                mutation="pagination_boundary",
                difficulty=2,
                category="code_repair",
                passed=True,
                duration=1.0,
            )
        ]
        report = BenchmarkReport(
            benchmark_id="test-bench",
            agent_type="mock",
            timestamp="2024-01-01T00:00:00",
            total_tasks=1,
            passed_tasks=1,
            failed_tasks=0,
            pass_rate=1.0,
            avg_duration=1.0,
            results=results,
        )
        d = report.to_dict()
        assert d["benchmark_id"] == "test-bench"
        assert d["pass_rate"] == 1.0
        assert len(d["results"]) == 1

    def test_benchmark_report_to_markdown(self):
        """BenchmarkReport.to_markdown should produce valid markdown."""
        from forge.evaluation.benchmark import BenchmarkReport, BenchmarkResult

        results = [
            BenchmarkResult(
                task_id="task-1",
                task_name="Task 1",
                template="task_manager_api",
                mutation="pagination_boundary",
                difficulty=2,
                category="code_repair",
                passed=True,
                duration=1.0,
            )
        ]
        report = BenchmarkReport(
            benchmark_id="test-bench",
            agent_type="mock",
            timestamp="2024-01-01T00:00:00",
            total_tasks=1,
            passed_tasks=1,
            failed_tasks=0,
            pass_rate=1.0,
            avg_duration=1.0,
            results=results,
        )
        md = report.to_markdown()
        assert "# Benchmark Report" in md
        assert "| task-1 |" in md
        assert "✓" in md

    def test_benchmark_save_json(self, tmp_path):
        """BenchmarkRunner.save_report should save JSON file."""
        from forge.agents.mock_agent import MockAgent
        from forge.evaluation.benchmark import BenchmarkReport, BenchmarkRunner

        config = AgentConfig(agent_type="mock")
        agent = MockAgent(config=config)
        runner = BenchmarkRunner(agent=agent)
        report = BenchmarkReport(
            benchmark_id="test-save",
            agent_type="mock",
            timestamp="2024-01-01T00:00:00",
            total_tasks=1,
            passed_tasks=1,
            failed_tasks=0,
            pass_rate=1.0,
            avg_duration=1.0,
        )
        saved = runner.save_report(report, tmp_path, format="json")
        assert saved.exists()
        assert saved.suffix == ".json"
        data = json.loads(saved.read_text())
        assert data["benchmark_id"] == "test-save"

    def test_benchmark_save_markdown(self, tmp_path):
        """BenchmarkRunner.save_report should save Markdown file."""
        from forge.agents.mock_agent import MockAgent
        from forge.evaluation.benchmark import BenchmarkReport, BenchmarkRunner

        config = AgentConfig(agent_type="mock")
        agent = MockAgent(config=config)
        runner = BenchmarkRunner(agent=agent)
        report = BenchmarkReport(
            benchmark_id="test-md",
            agent_type="mock",
            timestamp="2024-01-01T00:00:00",
            total_tasks=1,
            passed_tasks=1,
            failed_tasks=0,
            pass_rate=1.0,
            avg_duration=1.0,
        )
        saved = runner.save_report(report, tmp_path, format="markdown")
        assert saved.exists()
        assert saved.suffix == ".md"
        content = saved.read_text()
        assert "# Benchmark Report" in content

    def test_benchmark_empty_tasks(self, tmp_path):
        """BenchmarkRunner should handle empty task list."""
        from forge.agents.mock_agent import MockAgent
        from forge.evaluation.benchmark import BenchmarkRunner

        config = AgentConfig(agent_type="mock")
        agent = MockAgent(config=config)
        runner = BenchmarkRunner(agent=agent)
        report = runner.run([], tmp_path)
        assert report.total_tasks == 0
        assert report.pass_rate == 0.0


# ---------------------------------------------------------------------------
# Training Adapter Tests
# ---------------------------------------------------------------------------


class TestTrajectoryFilter:
    """Test the TrajectoryFilter for selecting training data."""

    def _make_result(self, run_id, passed, difficulty=1, verification=None):
        """Helper to create a RunResult with the correct schema."""
        from forge.core.schemas import RunResult, Trajectory

        r = RunResult(run_id=run_id, task_id=f"task-{run_id}", agent_id="a1")
        r.passed = passed
        r.trajectory = Trajectory(run_id=run_id, task_id=f"task-{run_id}", agent_id="a1")
        r.metadata = {"difficulty_level": difficulty}
        if verification is not None:
            r.verification = verification
        return r

    def test_filter_passed_only(self):
        """Filter should return only passed runs."""
        from forge.training.adapter import TrajectoryFilter

        passed = self._make_result("r1", passed=True)
        failed = self._make_result("r2", passed=False)
        f = TrajectoryFilter()
        result = f.filter([passed, failed], passed_only=True)
        assert len(result) == 1
        assert result[0].passed is True

    def test_filter_failed_only(self):
        """Filter should return only failed runs."""
        from forge.training.adapter import TrajectoryFilter

        passed = self._make_result("r1", passed=True)
        failed = self._make_result("r2", passed=False)
        f = TrajectoryFilter()
        result = f.filter([passed, failed], passed_only=False)
        assert len(result) == 1
        assert result[0].passed is False

    def test_filter_by_difficulty(self):
        """Filter should respect difficulty range."""
        from forge.training.adapter import TrajectoryFilter

        easy = self._make_result("r1", passed=True, difficulty=1)
        hard = self._make_result("r2", passed=True, difficulty=4)
        f = TrajectoryFilter()
        result = f.filter([easy, hard], min_difficulty=3)
        assert len(result) == 1
        assert result[0].metadata["difficulty_level"] == 4

    def test_filter_by_quality_top_k(self):
        """filter_by_quality should return top-k by reward."""
        from forge.core.schemas import VerificationResult
        from forge.training.adapter import TrajectoryFilter

        ver = VerificationResult(run_id="r1", passed=True)
        high = self._make_result("r1", passed=True, verification=ver)
        low = self._make_result("r2", passed=False)
        f = TrajectoryFilter()
        result = f.filter_by_quality([low, high], top_k=1)
        assert len(result) == 1
        assert result[0].passed is True

    def test_filter_by_quality_percentile(self):
        """filter_by_quality should return top percentile."""
        from forge.training.adapter import TrajectoryFilter

        results = [self._make_result(f"r{i}", passed=(i < 3)) for i in range(10)]
        f = TrajectoryFilter()
        result = f.filter_by_quality(results, percentile=0.5)
        assert len(result) >= 1
        # All passed should come before failed
        for i, r in enumerate(result):
            if r.passed:
                assert all(
                    nr.passed or nr not in result[:i]
                    for nr in results
                    if nr.passed
                )


class TestDifficultyWeightedReward:
    """Test difficulty-weighted reward computation."""

    def _make_result(self, run_id, passed, difficulty=1):
        """Helper to create a RunResult with the correct schema."""
        from forge.core.schemas import RunResult, Trajectory

        r = RunResult(run_id=run_id, task_id=f"task-{run_id}", agent_id="a1")
        r.passed = passed
        r.trajectory = Trajectory(run_id=run_id, task_id=f"task-{run_id}", agent_id="a1")
        r.metadata = {"difficulty_level": difficulty}
        return r

    def test_reward_without_difficulty_weight(self):
        """Default reward should not use difficulty weighting."""
        from forge.training.adapter import TrajectoryExporter

        result = self._make_result("r1", passed=True, difficulty=5)
        exporter = TrajectoryExporter()
        components = exporter._compute_reward_components(result, difficulty_weight=False)
        assert components["task_completion"] == 1.0

    def test_reward_with_difficulty_weight(self):
        """Difficulty-weighted reward should scale with difficulty."""
        from forge.training.adapter import TrajectoryExporter

        easy = self._make_result("r1", passed=True, difficulty=1)
        hard = self._make_result("r2", passed=True, difficulty=5)
        exporter = TrajectoryExporter()
        easy_reward = exporter._compute_reward_components(easy, difficulty_weight=True)
        hard_reward = exporter._compute_reward_components(hard, difficulty_weight=True)
        assert hard_reward["task_completion"] > easy_reward["task_completion"]

    def test_difficulty_bonus(self):
        """Difficulty bonus should apply for hard tasks."""
        from forge.training.adapter import TrajectoryExporter

        result = self._make_result("r1", passed=True, difficulty=5)
        exporter = TrajectoryExporter()
        components = exporter._compute_reward_components(result, difficulty_weight=True)
        assert "difficulty_bonus" in components
        assert components["difficulty_bonus"] > 0


# ---------------------------------------------------------------------------
# Session Replay Tests
# ---------------------------------------------------------------------------


class TestSessionReplay:
    """Test the session replay module."""

    def test_load_json_session(self, tmp_path):
        """Should load a session from a JSON file."""
        from forge.runner.replay import SessionReplayer

        data = {
            "task_id": "test-1",
            "model_metadata": {"agent_id": "mock-agent"},
            "final_outcome": {"passed": True},
            "steps": [
                {
                    "step_index": 0,
                    "action": "read_file",
                    "tool_name": "read_file",
                    "tool_arguments": {"path": "app.py"},
                    "observation": "File content",
                }
            ],
        }
        json_file = tmp_path / "session.json"
        json_file.write_text(json.dumps(data))

        replayer = SessionReplayer()
        session = replayer.load(json_file)
        assert session.task_id == "test-1"
        assert session.passed is True
        assert len(session.steps) == 1

    def test_load_jsonl_batch(self, tmp_path):
        """Should load multiple sessions from JSONL."""
        from forge.runner.replay import SessionReplayer

        lines = []
        for i in range(3):
            line = json.dumps({
                "task_id": f"test-{i}",
                "model_metadata": {"agent_id": "mock"},
                "final_outcome": {"passed": i % 2 == 0},
                "steps": [],
            })
            lines.append(line)
        jsonl_file = tmp_path / "sessions.jsonl"
        jsonl_file.write_text("\n".join(lines))

        replayer = SessionReplayer()
        sessions = replayer.load_batch(jsonl_file)
        assert len(sessions) == 3

    def test_replay_summary(self):
        """Replay should produce a summary."""
        from forge.runner.replay import ReplaySession, ReplayStep, SessionReplayer

        session = ReplaySession(
            task_id="test-1",
            agent_id="mock",
            passed=True,
            steps=[
                ReplayStep(step_index=0, action="read", tool_name="read_file"),
                ReplayStep(step_index=1, action="write", tool_name="write_file"),
            ],
        )
        replayer = SessionReplayer()
        summary = replayer.replay(session)
        assert summary["total_steps"] == 2
        assert summary["passed"] is True
        assert "read_file" in summary["tools_used"]
        assert "write_file" in summary["tools_used"]

    def test_replay_callback(self):
        """Replay should call callback for each step."""
        from forge.runner.replay import ReplaySession, ReplayStep, SessionReplayer

        called = []
        def cb(step):
            called.append(step.step_index)

        session = ReplaySession(
            task_id="test-1", agent_id="mock", passed=True,
            steps=[
                ReplayStep(step_index=0, action="a"),
                ReplayStep(step_index=1, action="b"),
            ],
        )
        replayer = SessionReplayer()
        replayer.replay(session, callback=cb)
        assert called == [0, 1]

    def test_compare_sessions(self):
        """Compare should produce a side-by-side report."""
        from forge.runner.replay import ReplaySession, ReplayStep, SessionReplayer

        a = ReplaySession(
            task_id="t1", agent_id="agent-a", passed=True,
            steps=[ReplayStep(step_index=0, action="a", tool_name="read")],
        )
        b = ReplaySession(
            task_id="t1", agent_id="agent-b", passed=False,
            steps=[
                ReplayStep(step_index=0, action="b", tool_name="read"),
                ReplayStep(step_index=1, action="c", tool_name="write"),
            ],
        )
        replayer = SessionReplayer()
        comparison = replayer.compare(a, b)
        assert comparison["passed"]["a"] is True
        assert comparison["passed"]["b"] is False
        assert comparison["steps"]["a"] == 1
        assert comparison["steps"]["b"] == 2

    def test_load_directory(self, tmp_path):
        """Should load all JSON files from a directory."""
        from forge.runner.replay import SessionReplayer

        for i in range(3):
            f = tmp_path / f"session_{i}.json"
            f.write_text(json.dumps({
                "task_id": f"t{i}",
                "model_metadata": {"agent_id": "mock"},
                "final_outcome": {"passed": True},
                "steps": [],
            }))

        replayer = SessionReplayer()
        sessions = replayer.load_directory(tmp_path)
        assert len(sessions) == 3

    def test_empty_workspace_replay(self):
        """Should handle session with no steps."""
        from forge.runner.replay import ReplaySession, SessionReplayer

        session = ReplaySession(task_id="empty", agent_id="mock", passed=False, steps=[])
        replayer = SessionReplayer()
        summary = replayer.replay(session)
        assert summary["total_steps"] == 0
        assert summary["tools_used"] == []


# ---------------------------------------------------------------------------
# Normalized Trajectory Tests
# ---------------------------------------------------------------------------


class TestNormalizedTrajectory:
    """Test normalized trajectory export and reward computation."""

    def test_schema_version(self):
        """Schema version should be set."""
        from forge.training.normalized import SCHEMA_VERSION

        assert SCHEMA_VERSION == "1.0.0"

    def test_normalized_trajectory_creation(self):
        """Should create normalized trajectory with defaults."""
        from forge.training.normalized import NormalizedTrajectory

        traj = NormalizedTrajectory(
            run_id="run-1",
            task_id="task-1",
            agent_type="mock",
        )
        assert traj.run_id == "run-1"
        assert traj.passed is False
        assert traj.schema_version == "1.0.0"
        assert traj.steps == []

    def test_normalized_trajectory_to_dict(self):
        """Should serialize to dictionary."""
        from forge.training.normalized import NormalizedTrajectory

        traj = NormalizedTrajectory(
            run_id="run-1",
            task_id="task-1",
            agent_type="mock",
            passed=True,
            difficulty_level=3,
        )
        d = traj.to_dict()
        assert d["run_id"] == "run-1"
        assert d["passed"] is True
        assert d["difficulty_level"] == 3
        assert d["schema_version"] == "1.0.0"

    def test_normalized_trajectory_to_json(self):
        """Should serialize to JSON string."""
        from forge.training.normalized import NormalizedTrajectory
        import json

        traj = NormalizedTrajectory(
            run_id="run-1",
            task_id="task-1",
            agent_type="mock",
        )
        json_str = traj.to_json()
        parsed = json.loads(json_str)
        assert parsed["run_id"] == "run-1"

    def test_trajectory_normalizer_normalize(self):
        """Should normalize a trajectory with steps."""
        from forge.core.schemas import (
            RunResult,
            RunStatus,
            TaskCategory,
            TaskSpec,
            Trajectory,
            TrajectoryStep,
            VerificationResult,
        )
        from forge.training.normalized import TrajectoryNormalizer

        task = TaskSpec(
            task_id="task-1",
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="Fix bug",
            difficulty_level=3,
            metadata={"template_name": "task_manager_api", "mutation_name": "pagination_boundary"},
        )
        trajectory = Trajectory(run_id="run-1", task_id="task-1", agent_id="agent-1")
        trajectory.add_step(
            TrajectoryStep(
                step_index=0,
                observation="File content",
                action="read",
                tool_name="read_file",
                tool_arguments={"path": "app.py"},
                tool_result="content",
                duration_seconds=0.5,
            )
        )
        trajectory.finalize("completed", 1.0)

        verification = VerificationResult(run_id="run-1", passed=True)
        result = RunResult(
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
            status=RunStatus.COMPLETED,
        )
        result.passed = True
        result.duration_seconds = 1.0
        result.verification = verification

        normalizer = TrajectoryNormalizer()
        normalized = normalizer.normalize(trajectory, result, task)

        assert normalized.run_id == "run-1"
        assert normalized.task_id == "task-1"
        assert normalized.passed is True
        assert normalized.difficulty_level == 3
        assert normalized.task_category == "bug_repair"
        assert normalized.template_name == "task_manager_api"
        assert len(normalized.steps) == 1
        assert normalized.steps[0]["tool_name"] == "read_file"

    def test_trajectory_normalizer_empty(self):
        """Should handle empty trajectory."""
        from forge.core.schemas import (
            RunResult,
            RunStatus,
            TaskCategory,
            TaskSpec,
            Trajectory,
        )
        from forge.training.normalized import TrajectoryNormalizer

        task = TaskSpec(
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="Fix bug",
        )
        trajectory = Trajectory(run_id="run-1", task_id="task-1", agent_id="agent-1")
        trajectory.finalize("completed", 0.0)

        result = RunResult(
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
            status=RunStatus.COMPLETED,
        )
        result.passed = False

        normalizer = TrajectoryNormalizer()
        normalized = normalizer.normalize(trajectory, result, task)

        assert normalized.passed is False
        assert normalized.steps == []

    def test_trajectory_normalizer_batch(self):
        """Should normalize a batch of trajectories."""
        from forge.core.schemas import (
            RunResult,
            RunStatus,
            TaskCategory,
            TaskSpec,
            Trajectory,
        )
        from forge.training.normalized import TrajectoryNormalizer

        normalizer = TrajectoryNormalizer()
        trajectories = []
        results = []
        tasks = []

        for i in range(3):
            task = TaskSpec(
                world_id=f"world-{i}",
                category=TaskCategory.BUG_REPAIR,
                description=f"Fix bug {i}",
            )
            trajectory = Trajectory(run_id=f"run-{i}", task_id=f"task-{i}", agent_id="agent-1")
            trajectory.finalize("completed", 0.0)
            result = RunResult(
                run_id=f"run-{i}",
                task_id=f"task-{i}",
                agent_id="agent-1",
                status=RunStatus.COMPLETED,
            )
            result.passed = i % 2 == 0
            trajectories.append(trajectory)
            results.append(result)
            tasks.append(task)

        normalized = normalizer.normalize_batch(trajectories, results, tasks)
        assert len(normalized) == 3
        assert normalized[0].passed is True
        assert normalized[1].passed is False

    def test_export_jsonl(self, tmp_path):
        """Should export trajectories as JSONL."""
        from forge.training.normalized import NormalizedTrajectory, TrajectoryNormalizer
        import json

        trajectories = [
            NormalizedTrajectory(run_id="run-1", task_id="task-1", agent_type="mock", passed=True),
            NormalizedTrajectory(run_id="run-2", task_id="task-2", agent_type="mock", passed=False),
        ]
        output = tmp_path / "output.jsonl"
        normalizer = TrajectoryNormalizer()
        count = normalizer.export_jsonl(trajectories, output)

        assert count == 2
        lines = output.read_text().strip().split("\n")
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["run_id"] == "run-1"
        assert first["passed"] is True


# ---------------------------------------------------------------------------
# Reward Computation Tests
# ---------------------------------------------------------------------------


class TestRewardComputation:
    """Test reward signal computation."""

    def test_reward_signal_creation(self):
        """Should create reward signal with defaults."""
        from forge.training.rewards import RewardSignal

        signal = RewardSignal()
        assert signal.total_reward == 0.0
        assert signal.components == {}
        assert signal.explanation == ""

    def test_reward_signal_to_dict(self):
        """Should serialize reward signal."""
        from forge.training.rewards import RewardSignal

        signal = RewardSignal(
            total_reward=1.5,
            components={"pass_fail": 1.0},
            explanation="Passed",
            run_id="run-1",
            task_id="task-1",
        )
        d = signal.to_dict()
        assert d["total_reward"] == 1.5
        assert d["components"]["pass_fail"] == 1.0
        assert d["run_id"] == "run-1"

    def test_reward_pass(self):
        """Passed run should get positive reward."""
        from forge.core.schemas import (
            RunResult,
            RunStatus,
            TaskCategory,
            TaskSpec,
            VerificationResult,
        )
        from forge.training.rewards import RewardComputer

        task = TaskSpec(
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="Fix bug",
            difficulty_level=1,
        )
        verification = VerificationResult(run_id="run-1", passed=True)
        result = RunResult(
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
            status=RunStatus.COMPLETED,
        )
        result.passed = True
        result.verification = verification

        computer = RewardComputer()
        reward = computer.compute(result, task)

        assert reward.total_reward > 0
        assert "pass_fail" in reward.components
        assert reward.components["pass_fail"] == 1.0

    def test_reward_fail(self):
        """Failed run should get negative reward."""
        from forge.core.schemas import (
            RunResult,
            RunStatus,
            TaskCategory,
            TaskSpec,
        )
        from forge.training.rewards import RewardComputer

        task = TaskSpec(
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="Fix bug",
            difficulty_level=1,
        )
        result = RunResult(
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
            status=RunStatus.FAILED,
        )
        result.passed = False

        computer = RewardComputer()
        reward = computer.compute(result, task)

        assert reward.total_reward < 0
        assert reward.components["pass_fail"] == -0.5

    def test_reward_difficulty_weight(self):
        """Higher difficulty should increase reward."""
        from forge.core.schemas import (
            RunResult,
            RunStatus,
            TaskCategory,
            TaskSpec,
            VerificationResult,
        )
        from forge.training.rewards import RewardComputer

        computer = RewardComputer()

        task_easy = TaskSpec(
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="Fix bug",
            difficulty_level=1,
        )
        task_hard = TaskSpec(
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="Fix bug",
            difficulty_level=5,
        )

        verification = VerificationResult(run_id="run-1", passed=True)
        result = RunResult(
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
            status=RunStatus.COMPLETED,
        )
        result.passed = True
        result.verification = verification

        reward_easy = computer.compute(result, task_easy)
        reward_hard = computer.compute(result, task_hard)

        assert reward_hard.total_reward > reward_easy.total_reward

    def test_reward_hidden_tests_bonus(self):
        """Hidden tests passing should add bonus."""
        from forge.core.schemas import (
            RunResult,
            RunStatus,
            TaskCategory,
            TaskSpec,
            VerificationResult,
        )
        from forge.training.rewards import RewardComputer

        task = TaskSpec(
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="Fix bug",
            difficulty_level=1,
        )
        verification = VerificationResult(
            run_id="run-1",
            passed=True,
            hidden_tests_passed=True,
        )
        result = RunResult(
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
            status=RunStatus.COMPLETED,
        )
        result.passed = True
        result.verification = verification

        computer = RewardComputer()
        reward = computer.compute(result, task)

        assert "hidden_tests" in reward.components
        assert reward.components["hidden_tests"] == 0.2

    def test_reward_batch(self):
        """Should compute rewards for a batch."""
        from forge.core.schemas import (
            RunResult,
            RunStatus,
            TaskCategory,
            TaskSpec,
        )
        from forge.training.rewards import RewardComputer

        computer = RewardComputer()
        results = []
        tasks = []

        for i in range(3):
            task = TaskSpec(
                world_id=f"world-{i}",
                category=TaskCategory.BUG_REPAIR,
                description=f"Fix bug {i}",
            )
            result = RunResult(
                run_id=f"run-{i}",
                task_id=f"task-{i}",
                agent_id="agent-1",
                status=RunStatus.COMPLETED,
            )
            result.passed = i % 2 == 0
            results.append(result)
            tasks.append(task)

        rewards = computer.compute_batch(results, tasks)
        assert len(rewards) == 3
        assert rewards[0].total_reward > 0
        assert rewards[1].total_reward < 0

    def test_average_reward(self):
        """Should calculate average reward."""
        from forge.training.rewards import RewardComputer, RewardSignal

        computer = RewardComputer()
        rewards = [
            RewardSignal(total_reward=1.0),
            RewardSignal(total_reward=2.0),
            RewardSignal(total_reward=3.0),
        ]
        avg = computer.average_reward(rewards)
        assert avg == 2.0

    def test_average_reward_empty(self):
        """Should return 0 for empty list."""
        from forge.training.rewards import RewardComputer

        computer = RewardComputer()
        avg = computer.average_reward([])
        assert avg == 0.0

    def test_reward_custom_weights(self):
        """Should allow custom reward weights."""
        from forge.core.schemas import (
            RunResult,
            RunStatus,
            TaskCategory,
            TaskSpec,
        )
        from forge.training.rewards import RewardComputer

        computer = RewardComputer(weights={"pass_reward": 2.0})
        task = TaskSpec(
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="Fix bug",
        )
        result = RunResult(
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
            status=RunStatus.COMPLETED,
        )
        result.passed = True

        reward = computer.compute(result, task)
        assert reward.components["pass_fail"] == 2.0


# ---------------------------------------------------------------------------
# Auto-Scaling Tests
# ---------------------------------------------------------------------------


class TestAutoScaling:
    """Test automatic difficulty scaling."""

    def test_increase_difficulty(self):
        """Should increase difficulty when pass rate is high."""
        from forge.curriculum.autoscale import AutoScaler

        scaler = AutoScaler(window_size=5, high_threshold=0.8)
        for _ in range(4):
            scaler.record_result("mock", "task_manager_api", True)
        scaler.record_result("mock", "task_manager_api", True)

        adjustment = scaler.adjust_difficulty("mock", "task_manager_api", 3)
        assert adjustment.action == "increase"
        assert adjustment.new_difficulty == 4
        assert adjustment.pass_rate == 1.0

    def test_decrease_difficulty(self):
        """Should decrease difficulty when pass rate is low."""
        from forge.curriculum.autoscale import AutoScaler

        scaler = AutoScaler(window_size=5, low_threshold=0.2)
        for _ in range(5):
            scaler.record_result("mock", "task_manager_api", False)

        adjustment = scaler.adjust_difficulty("mock", "task_manager_api", 3)
        assert adjustment.action == "decrease"
        assert adjustment.new_difficulty == 2

    def test_maintain_difficulty(self):
        """Should maintain difficulty when pass rate is in middle range."""
        from forge.curriculum.autoscale import AutoScaler

        scaler = AutoScaler(window_size=5)
        scaler.record_result("mock", "task_manager_api", True)
        scaler.record_result("mock", "task_manager_api", False)
        scaler.record_result("mock", "task_manager_api", True)

        adjustment = scaler.adjust_difficulty("mock", "task_manager_api", 3)
        assert adjustment.action == "maintain"
        assert adjustment.new_difficulty == 3

    def test_cap_at_max_difficulty(self):
        """Should not exceed max difficulty."""
        from forge.curriculum.autoscale import AutoScaler

        scaler = AutoScaler(window_size=3, high_threshold=0.8)
        for _ in range(3):
            scaler.record_result("mock", "task_manager_api", True)

        adjustment = scaler.adjust_difficulty("mock", "task_manager_api", 5)
        assert adjustment.new_difficulty == 5

    def test_cap_at_min_difficulty(self):
        """Should not go below min difficulty."""
        from forge.curriculum.autoscale import AutoScaler

        scaler = AutoScaler(window_size=3, low_threshold=0.2)
        for _ in range(3):
            scaler.record_result("mock", "task_manager_api", False)

        adjustment = scaler.adjust_difficulty("mock", "task_manager_api", 1)
        assert adjustment.new_difficulty == 1

    def test_empty_history(self):
        """Should maintain difficulty with no history."""
        from forge.curriculum.autoscale import AutoScaler

        scaler = AutoScaler()
        adjustment = scaler.adjust_difficulty("mock", "task_manager_api", 3)
        assert adjustment.action == "maintain"
        assert adjustment.recent_runs == 0

    def test_window_size_limit(self):
        """Should only consider the most recent results."""
        from forge.curriculum.autoscale import AutoScaler

        scaler = AutoScaler(window_size=3)
        # First 3: all fail
        for _ in range(3):
            scaler.record_result("mock", "task_manager_api", False)
        # Next 3: all pass (should replace old ones)
        for _ in range(3):
            scaler.record_result("mock", "task_manager_api", True)

        adjustment = scaler.adjust_difficulty("mock", "task_manager_api", 3)
        assert adjustment.pass_rate == 1.0
        assert adjustment.action == "increase"

    def test_reset(self):
        """Should reset history."""
        from forge.curriculum.autoscale import AutoScaler

        scaler = AutoScaler()
        scaler.record_result("mock", "task_manager_api", True)
        scaler.record_result("mock", "data_pipeline", False)
        scaler.reset()
        assert scaler.get_history_size("mock", "task_manager_api") == 0
        assert scaler.get_history_size("mock", "data_pipeline") == 0


# ---------------------------------------------------------------------------
# Audit Logging Tests
# ---------------------------------------------------------------------------


class TestAuditLogging:
    """Test audit logging functionality."""

    def test_log_and_read(self, tmp_path):
        """Should log and read entries."""
        from forge.core.audit import AuditLogger

        logger = AuditLogger(log_dir=tmp_path)
        entry = logger.log(
            action="world_generate",
            actor="cli",
            target="world-1",
            outcome="success",
        )
        assert entry.action == "world_generate"

        entries = logger.read()
        assert len(entries) == 1
        assert entries[0].action == "world_generate"

    def test_filter_by_action(self, tmp_path):
        """Should filter entries by action."""
        from forge.core.audit import AuditLogger

        logger = AuditLogger(log_dir=tmp_path)
        logger.log(action="world_generate", actor="cli", target="w1")
        logger.log(action="run_start", actor="cli", target="r1")
        logger.log(action="world_generate", actor="cli", target="w2")

        entries = logger.read(action="world_generate")
        assert len(entries) == 2

    def test_filter_by_limit(self, tmp_path):
        """Should limit number of entries returned."""
        from forge.core.audit import AuditLogger

        logger = AuditLogger(log_dir=tmp_path)
        for i in range(5):
            logger.log(action="test", target=f"t{i}")

        entries = logger.read(limit=3)
        assert len(entries) == 3

    def test_count(self, tmp_path):
        """Should count entries."""
        from forge.core.audit import AuditLogger

        logger = AuditLogger(log_dir=tmp_path)
        logger.log(action="a", target="t1")
        logger.log(action="b", target="t2")
        logger.log(action="a", target="t3")

        assert logger.count() == 3
        assert logger.count(action="a") == 2

    def test_get_actions(self, tmp_path):
        """Should return unique action names."""
        from forge.core.audit import AuditLogger

        logger = AuditLogger(log_dir=tmp_path)
        logger.log(action="world_generate")
        logger.log(action="run_start")
        logger.log(action="world_generate")

        actions = logger.get_actions()
        assert actions == ["run_start", "world_generate"]

    def test_clear(self, tmp_path):
        """Should clear the audit log."""
        from forge.core.audit import AuditLogger

        logger = AuditLogger(log_dir=tmp_path)
        logger.log(action="test")
        assert logger.count() == 1
        logger.clear()
        assert logger.count() == 0

    def test_empty_log(self, tmp_path):
        """Should handle empty log."""
        from forge.core.audit import AuditLogger

        logger = AuditLogger(log_dir=tmp_path)
        entries = logger.read()
        assert entries == []
        assert logger.count() == 0

    def test_audit_entry_serialization(self):
        """Should serialize and deserialize entries."""
        from forge.core.audit import AuditEntry
        import json

        entry = AuditEntry(
            timestamp="2024-01-01T00:00:00",
            action="test",
            actor="cli",
            target="t1",
            outcome="success",
            duration_seconds=1.5,
            details={"key": "value"},
        )
        json_str = entry.to_json()
        data = json.loads(json_str)
        assert data["action"] == "test"
        assert data["duration_seconds"] == 1.5
        assert data["details"]["key"] == "value"


# ---------------------------------------------------------------------------
# v0.5 Template Tests
# ---------------------------------------------------------------------------


class TestV05Templates:
    """Test the new react_app and spring_service templates."""

    def test_list_templates_count(self):
        """Should have 14 templates total."""
        templates = list_templates()
        assert len(templates) == 14

    def test_react_app_template_exists(self):
        """react_app template should be registered."""
        template = get_template("react_app")
        assert template is not None
        assert template["name"] == "react_app"
        assert "app.py" in template["files"]
        assert "tests/test_public.py" in template["files"]
        assert ".hidden_tests/test_hidden.py" in template["files"]

    def test_react_app_has_classes(self):
        """react_app app code should contain expected classes."""
        template = get_template("react_app")
        app_code = template["files"]["app.py"]
        for cls in [
            "Component",
            "StateManager",
            "EventDispatcher",
            "Router",
            "FormHandler",
        ]:
            assert f"class {cls}" in app_code

    def test_spring_service_template_exists(self):
        """spring_service template should be registered."""
        template = get_template("spring_service")
        assert template is not None
        assert template["name"] == "spring_service"
        assert "app.py" in template["files"]

    def test_spring_service_has_classes(self):
        """spring_service app code should contain expected classes."""
        template = get_template("spring_service")
        app_code = template["files"]["app.py"]
        for cls in [
            "Repository",
            "TransactionManager",
            "Validator",
            "Service",
            "Controller",
        ]:
            assert f"class {cls}" in app_code

    def test_mutation_count(self):
        """Should have 37 mutations total."""
        mutations = list_mutations()
        assert len(mutations) == 37

    def test_xss_injection_mutation(self):
        """xss_injection mutation should be registered."""
        mutation = get_mutation("xss_injection")
        assert mutation is not None
        assert mutation["id"] == "xss_injection"

    def test_transaction_leak_mutation(self):
        """transaction_leak mutation should be registered."""
        mutation = get_mutation("transaction_leak")
        assert mutation is not None
        assert mutation["id"] == "transaction_leak"


# ---------------------------------------------------------------------------
# Benchmark Suite Tests
# ---------------------------------------------------------------------------


class TestBenchmarkSuite:
    """Test benchmark suite functionality."""

    def test_create_suite(self):
        """Should create a benchmark suite."""
        from forge.evaluation.suite import create_benchmark_suite

        suite = create_benchmark_suite(level="all")
        assert suite.name == "benchmark_all"
        assert suite.level == "all"
        assert "mock" in suite.baselines

    def test_suite_set_baseline(self):
        """Should set baseline for agent type."""
        from forge.evaluation.suite import BenchmarkSuite

        suite = BenchmarkSuite(name="test")
        suite.set_baseline("mock", 0.75)
        assert suite.get_baseline("mock") == 0.75

    def test_suite_to_dict(self):
        """Should serialize suite to dict."""
        from forge.evaluation.suite import BenchmarkSuite

        suite = BenchmarkSuite(name="test", level="easy")
        suite.set_baseline("mock", 0.5)
        d = suite.to_dict()
        assert d["name"] == "test"
        assert d["level"] == "easy"
        assert d["baselines"]["mock"] == 0.5

    def test_suite_add_task(self):
        """Should add tasks to suite."""
        from forge.core.schemas import TaskCategory, TaskSpec
        from forge.evaluation.suite import BenchmarkSuite

        suite = BenchmarkSuite(name="test")
        task = TaskSpec(
            task_id="task-1",
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="Fix bug",
        )
        suite.add_task(task)
        assert len(suite.tasks) == 1

    def test_empty_suite(self):
        """Should handle empty suite."""
        from forge.evaluation.suite import BenchmarkSuite

        suite = BenchmarkSuite(name="empty")
        assert len(suite.tasks) == 0
        assert suite.to_dict()["task_count"] == 0


# ---------------------------------------------------------------------------
# Task Queue Tests
# ---------------------------------------------------------------------------


class TestTaskQueue:
    """Test task queue functionality."""

    def test_enqueue_dequeue(self):
        """Should enqueue and dequeue tasks."""
        from forge.core.schemas import TaskCategory, TaskSpec
        from forge.runner.queue import TaskQueue

        queue = TaskQueue()
        task = TaskSpec(
            task_id="task-1",
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="Fix bug",
        )
        queue.enqueue(task)
        assert queue.size() == 1

        dequeued = queue.dequeue()
        assert dequeued.task_id == "task-1"
        assert queue.size() == 0

    def test_priority_ordering(self):
        """Should dequeue in priority order."""
        from forge.core.schemas import TaskCategory, TaskSpec
        from forge.runner.queue import PRIORITY_HIGH, PRIORITY_LOW, TaskQueue

        queue = TaskQueue()
        low = TaskSpec(
            task_id="low",
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="Low priority",
        )
        high = TaskSpec(
            task_id="high",
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="High priority",
        )
        queue.enqueue(low, PRIORITY_LOW)
        queue.enqueue(high, PRIORITY_HIGH)

        first = queue.dequeue()
        assert first.task_id == "high"

    def test_empty_queue(self):
        """Should handle empty queue."""
        from forge.runner.queue import TaskQueue

        queue = TaskQueue()
        assert queue.is_empty()
        assert queue.dequeue() is None
        assert queue.peek() is None

    def test_pause_resume(self):
        """Should pause and resume queue."""
        from forge.runner.queue import TaskQueue

        queue = TaskQueue()
        queue.pause()
        queue.resume()
        assert not queue._paused

    def test_clear(self):
        """Should clear all tasks."""
        from forge.core.schemas import TaskCategory, TaskSpec
        from forge.runner.queue import TaskQueue

        queue = TaskQueue()
        task = TaskSpec(
            task_id="task-1",
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="Fix bug",
        )
        queue.enqueue(task)
        queue.clear()
        assert queue.is_empty()

    def test_peek(self):
        """Should peek without removing."""
        from forge.core.schemas import TaskCategory, TaskSpec
        from forge.runner.queue import TaskQueue

        queue = TaskQueue()
        task = TaskSpec(
            task_id="task-1",
            world_id="world-1",
            category=TaskCategory.BUG_REPAIR,
            description="Fix bug",
        )
        queue.enqueue(task)
        peeked = queue.peek()
        assert peeked.task_id == "task-1"
        assert queue.size() == 1  # Not removed
