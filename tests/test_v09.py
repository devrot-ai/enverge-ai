"""Tests for v0.9 features: snapshot, mutation coverage, difficulty calibration,
behavior analysis, and report templates."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from forge.evaluation.behavior_analysis import (
    BehaviorAnalyzer,
    BehaviorProfile,
    FailureMode,
    ToolPattern,
)
from forge.evaluation.difficulty_calibration import CalibrationResult, DifficultyCalibrator
from forge.evaluation.mutation_coverage import MutationCoverageAnalyzer, MutationCoverageReport
from forge.evaluation.report_templates import ReportTemplate
from forge.runner.snapshot import WorkspaceSnapshot, WorkspaceSnapshotter


# ---------------------------------------------------------------------------
# Workspace Snapshot
# ---------------------------------------------------------------------------


class TestWorkspaceSnapshot:
    """Tests for workspace snapshot and restore."""

    def test_capture_workspace(self, tmp_path):
        """Capture a workspace with multiple files."""
        # Create test workspace
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "app.py").write_text("print('hello')")
        (ws / "tests").mkdir()
        (ws / "tests" / "test_app.py").write_text("def test(): pass")

        snapshotter = WorkspaceSnapshotter(str(tmp_path / "snapshots"))
        snapshot = snapshotter.capture(str(ws), run_id="run-001")

        assert snapshot.run_id == "run-001"
        assert len(snapshot.file_contents) == 2
        assert "app.py" in snapshot.file_contents
        assert "tests/test_app.py" in snapshot.file_contents

    def test_save_and_restore(self, tmp_path):
        """Save a snapshot and restore it to a new directory."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "file1.py").write_text("content1")
        (ws / "file2.py").write_text("content2")

        snapshotter = WorkspaceSnapshotter(str(tmp_path / "snapshots"))
        snapshot = snapshotter.capture(str(ws), run_id="run-002")
        path = snapshotter.save(snapshot)

        # Restore
        restore_dir = str(tmp_path / "restored")
        count = snapshotter.restore(path, restore_dir)

        assert count == 2
        assert Path(restore_dir, "file1.py").read_text() == "content1"
        assert Path(restore_dir, "file2.py").read_text() == "content2"

    def test_list_snapshots(self, tmp_path):
        """List saved snapshots."""
        snapshotter = WorkspaceSnapshotter(str(tmp_path / "snapshots"))

        # Create and save a snapshot
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "test.py").write_text("pass")
        snapshot = snapshotter.capture(str(ws), run_id="run-003")
        snapshotter.save(snapshot)

        snapshots = snapshotter.list_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0]["run_id"] == "run-003"

    def test_capture_missing_workspace(self, tmp_path):
        """Capture should raise FileNotFoundError for missing workspace."""
        snapshotter = WorkspaceSnapshotter(str(tmp_path / "snapshots"))
        with pytest.raises(FileNotFoundError):
            snapshotter.capture(str(tmp_path / "nonexistent"))

    def test_restore_missing_snapshot(self, tmp_path):
        """Restore should raise FileNotFoundError for missing snapshot."""
        snapshotter = WorkspaceSnapshotter(str(tmp_path / "snapshots"))
        with pytest.raises(FileNotFoundError):
            snapshotter.restore(str(tmp_path / "nonexistent.json"), str(tmp_path / "restore"))

    def test_snapshot_serialization(self):
        """Snapshot should serialize and deserialize correctly."""
        snapshot = WorkspaceSnapshot(
            run_id="test-run",
            timestamp=1234567890.0,
            file_contents={"a.py": "print(1)"},
            metadata={"key": "value"},
        )
        data = snapshot.to_dict()
        restored = WorkspaceSnapshot.from_dict(data)
        assert restored.run_id == "test-run"
        assert restored.file_contents == {"a.py": "print(1)"}

    def test_empty_workspace(self, tmp_path):
        """Capture an empty workspace."""
        ws = tmp_path / "empty_ws"
        ws.mkdir()

        snapshotter = WorkspaceSnapshotter(str(tmp_path / "snapshots"))
        snapshot = snapshotter.capture(str(ws), run_id="empty")
        assert len(snapshot.file_contents) == 0

    def test_hidden_dirs_skipped(self, tmp_path):
        """Hidden directories and __pycache__ should be skipped."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "app.py").write_text("code")
        (ws / "__pycache__").mkdir()
        (ws / "__pycache__" / "app.cpython-311.pyc").write_text("binary")
        (ws / ".hidden").mkdir()
        (ws / ".hidden" / "secret.py").write_text("secret")

        snapshotter = WorkspaceSnapshotter(str(tmp_path / "snapshots"))
        snapshot = snapshotter.capture(str(ws), run_id="hidden-test")
        assert "app.py" in snapshot.file_contents
        assert len(snapshot.file_contents) == 1


# ---------------------------------------------------------------------------
# Mutation Coverage
# ---------------------------------------------------------------------------


class TestMutationCoverage:
    """Tests for mutation coverage analysis."""

    def test_analyze_full_coverage(self):
        """All mutations covered."""
        analyzer = MutationCoverageAnalyzer()
        mutations = ["mut_a", "mut_b", "mut_c"]
        tasks = [
            MagicMock(mutation="mut_a", task_id="task-1"),
            MagicMock(mutation="mut_b", task_id="task-2"),
            MagicMock(mutation="mut_c", task_id="task-3"),
        ]
        report = analyzer.analyze(all_mutations=mutations, task_specs=tasks)

        assert report.covered_mutations == 3
        assert report.total_mutations == 3
        assert report.coverage_percent == 100.0
        assert len(report.uncovered_mutations) == 0

    def test_analyze_partial_coverage(self):
        """Some mutations uncovered."""
        analyzer = MutationCoverageAnalyzer()
        mutations = ["mut_a", "mut_b", "mut_c", "mut_d"]
        tasks = [
            MagicMock(mutation="mut_a", task_id="task-1"),
            MagicMock(mutation="mut_b", task_id="task-2"),
        ]
        report = analyzer.analyze(all_mutations=mutations, task_specs=tasks)

        assert report.covered_mutations == 2
        assert report.total_mutations == 4
        assert report.coverage_percent == 50.0
        assert set(report.uncovered_mutations) == {"mut_c", "mut_d"}

    def test_get_coverage(self):
        """Get tasks covering a specific mutation."""
        analyzer = MutationCoverageAnalyzer()
        mutations = ["mut_a", "mut_b"]
        tasks = [
            MagicMock(mutation="mut_a", task_id="task-1"),
            MagicMock(mutation="mut_a", task_id="task-2"),
            MagicMock(mutation="mut_b", task_id="task-3"),
        ]
        analyzer.analyze(all_mutations=mutations, task_specs=tasks)

        coverage = analyzer.get_coverage("mut_a")
        assert set(coverage) == {"task-1", "task-2"}

    def test_get_gaps(self):
        """Get uncovered mutations."""
        analyzer = MutationCoverageAnalyzer()
        mutations = ["mut_a", "mut_b", "mut_c"]
        tasks = [MagicMock(mutation="mut_a", task_id="task-1")]
        analyzer.analyze(all_mutations=mutations, task_specs=tasks)

        gaps = analyzer.get_gaps()
        assert set(gaps) == {"mut_b", "mut_c"}

    def test_empty_analysis(self):
        """Analyze with no tasks."""
        analyzer = MutationCoverageAnalyzer()
        report = analyzer.analyze(all_mutations=["mut_a"], task_specs=[])
        assert report.covered_mutations == 0
        assert report.uncovered_mutations == ["mut_a"]

    def test_report_markdown(self):
        """Report should generate Markdown."""
        analyzer = MutationCoverageAnalyzer()
        mutations = ["mut_a", "mut_b"]
        tasks = [MagicMock(mutation="mut_a", task_id="task-1")]
        report = analyzer.analyze(all_mutations=mutations, task_specs=tasks)
        md = report.to_markdown()
        assert "# Mutation Coverage Report" in md
        assert "mut_a" in md
        assert "mut_b" in md


# ---------------------------------------------------------------------------
# Difficulty Calibration
# ---------------------------------------------------------------------------


class TestDifficultyCalibration:
    """Tests for difficulty calibration."""

    def test_calibrate_overestimated(self):
        """High pass rate should suggest easier difficulty."""
        calibrator = DifficultyCalibrator()
        results = [
            {"task_id": "task-1", "assigned_difficulty": 4, "passed": True}
            for _ in range(10)
        ]
        calibrations = calibrator.calibrate(results)
        cr = calibrations["task-1"]
        assert cr.suggested_difficulty < cr.assigned_difficulty
        assert cr.adjustment < 0

    def test_calibrate_underestimated(self):
        """Low pass rate should suggest harder difficulty."""
        calibrator = DifficultyCalibrator()
        results = [
            {"task_id": "task-1", "assigned_difficulty": 2, "passed": False}
            for _ in range(10)
        ]
        calibrations = calibrator.calibrate(results)
        cr = calibrations["task-1"]
        assert cr.suggested_difficulty > cr.assigned_difficulty
        assert cr.adjustment > 0

    def test_calibrate_no_change(self):
        """Moderate pass rate should keep difficulty."""
        calibrator = DifficultyCalibrator()
        results = [
            {"task_id": "task-1", "assigned_difficulty": 3, "passed": True},
            {"task_id": "task-1", "assigned_difficulty": 3, "passed": False},
            {"task_id": "task-1", "assigned_difficulty": 3, "passed": True},
            {"task_id": "task-1", "assigned_difficulty": 3, "passed": False},
        ]
        calibrations = calibrator.calibrate(results)
        cr = calibrations["task-1"]
        assert cr.suggested_difficulty == cr.assigned_difficulty

    def test_cap_at_min(self):
        """Difficulty should not go below 1."""
        calibrator = DifficultyCalibrator()
        results = [
            {"task_id": "task-1", "assigned_difficulty": 1, "passed": True}
            for _ in range(10)
        ]
        calibrations = calibrator.calibrate(results)
        cr = calibrations["task-1"]
        assert cr.suggested_difficulty >= 1

    def test_cap_at_max(self):
        """Difficulty should not go above 5."""
        calibrator = DifficultyCalibrator()
        results = [
            {"task_id": "task-1", "assigned_difficulty": 5, "passed": False}
            for _ in range(10)
        ]
        calibrations = calibrator.calibrate(results)
        cr = calibrations["task-1"]
        assert cr.suggested_difficulty <= 5

    def test_suggest_adjustments(self):
        """Only tasks needing adjustment should be returned."""
        calibrator = DifficultyCalibrator()
        results = [
            {"task_id": "task-1", "assigned_difficulty": 4, "passed": True}
            for _ in range(10)
        ] + [
            {"task_id": "task-2", "assigned_difficulty": 3, "passed": True},
            {"task_id": "task-2", "assigned_difficulty": 3, "passed": False},
        ]
        calibrator.calibrate(results)
        adjustments = calibrator.suggest_adjustments()
        assert len(adjustments) == 1
        assert adjustments[0].task_id == "task-1"


# ---------------------------------------------------------------------------
# Behavior Analysis
# ---------------------------------------------------------------------------


class TestBehaviorAnalysis:
    """Tests for agent behavior analysis."""

    def test_analyze_single_agent(self):
        """Analyze trajectories for a single agent."""
        analyzer = BehaviorAnalyzer()
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
                    {"tool_name": "read_file", "success": True, "duration_ms": 40},
                    {"tool_name": "write_file", "success": False, "duration_ms": 10},
                ],
                "passed": False,
                "failure_category": "agent_failure",
                "task_id": "task-2",
            },
        ]
        profiles = analyzer.analyze(trajectories)

        assert "mock" in profiles
        profile = profiles["mock"]
        assert profile.total_runs == 2
        assert profile.pass_rate == 0.5
        assert len(profile.tool_patterns) == 2
        assert len(profile.failure_modes) == 1

    def test_tool_patterns(self):
        """Get tool patterns for an agent."""
        analyzer = BehaviorAnalyzer()
        trajectories = [
            {
                "agent_type": "mock",
                "steps": [
                    {"tool_name": "read_file", "success": True, "duration_ms": 100},
                ],
                "passed": True,
            }
        ]
        analyzer.analyze(trajectories)
        patterns = analyzer.get_tool_patterns("mock")
        assert len(patterns) == 1
        assert patterns[0].tool_name == "read_file"
        assert patterns[0].call_count == 1

    def test_failure_modes(self):
        """Get failure modes for an agent."""
        analyzer = BehaviorAnalyzer()
        trajectories = [
            {
                "agent_type": "mock",
                "steps": [],
                "passed": False,
                "failure_category": "agent_failure",
                "task_id": "task-1",
            },
            {
                "agent_type": "mock",
                "steps": [],
                "passed": False,
                "failure_category": "agent_failure",
                "task_id": "task-2",
            },
            {
                "agent_type": "mock",
                "steps": [],
                "passed": False,
                "failure_category": "environment_failure",
                "task_id": "task-3",
            },
        ]
        analyzer.analyze(trajectories)
        modes = analyzer.get_failure_modes("mock")
        assert len(modes) == 2
        agent_fail = [m for m in modes if m.category == "agent_failure"]
        assert agent_fail[0].count == 2

    def test_empty_trajectories(self):
        """Analyze empty trajectories."""
        analyzer = BehaviorAnalyzer()
        profiles = analyzer.analyze([])
        assert len(profiles) == 0

    def test_multiple_agents(self):
        """Analyze trajectories for multiple agents."""
        analyzer = BehaviorAnalyzer()
        trajectories = [
            {"agent_type": "mock", "steps": [], "passed": True},
            {"agent_type": "rule_based", "steps": [], "passed": False, "failure_category": "agent_failure"},
        ]
        profiles = analyzer.analyze(trajectories)
        assert "mock" in profiles
        assert "rule_based" in profiles
        assert profiles["mock"].pass_rate == 1.0
        assert profiles["rule_based"].pass_rate == 0.0

    def test_profile_to_dict(self):
        """Profile should serialize to dict."""
        profile = BehaviorProfile(
            agent_type="mock",
            total_runs=5,
            tool_patterns=[ToolPattern("read_file", 3, 2, 1, 50.0)],
            failure_modes=[FailureMode("agent_failure", 2, ["task-1"])],
            pass_rate=0.6,
        )
        d = profile.to_dict()
        assert d["agent_type"] == "mock"
        assert d["total_runs"] == 5

    def test_profile_to_markdown(self):
        """Profile should generate Markdown."""
        profile = BehaviorProfile(
            agent_type="mock",
            total_runs=3,
            pass_rate=0.67,
        )
        md = profile.to_markdown()
        assert "# Behavior Profile: mock" in md

    def test_single_trajectory(self):
        """Analyze a single trajectory."""
        analyzer = BehaviorAnalyzer()
        trajectories = [
            {
                "agent_type": "mock",
                "steps": [{"tool_name": "read", "success": True, "duration_ms": 10}],
                "passed": True,
            }
        ]
        profiles = analyzer.analyze(trajectories)
        assert profiles["mock"].total_runs == 1
        assert profiles["mock"].pass_rate == 1.0


# ---------------------------------------------------------------------------
# Report Templates
# ---------------------------------------------------------------------------


class TestReportTemplates:
    """Tests for report template generation."""

    def test_research_paper(self):
        """Generate research paper report."""
        data = {
            "run_results": [
                {"task_id": "t1", "template": "task_manager_api", "passed": True, "duration_seconds": 10},
                {"task_id": "t2", "template": "data_pipeline", "passed": False, "duration_seconds": 5, "failure_category": "agent_failure"},
            ],
            "agent_type": "mock",
        }
        report = ReportTemplate.generate("research_paper", data)
        assert "# " in report
        assert "mock" in report
        assert "## Results" in report

    def test_executive_summary(self):
        """Generate executive summary report."""
        data = {
            "run_results": [
                {"task_id": "t1", "template": "task_manager_api", "passed": True, "duration_seconds": 10},
            ],
            "agent_type": "mock",
        }
        report = ReportTemplate.generate("executive_summary", data)
        assert "Key Findings" in report
        assert "Recommendations" in report

    def test_technical_deep_dive(self):
        """Generate technical deep dive report."""
        data = {
            "run_results": [
                {"task_id": "t1", "template": "task_manager_api", "passed": True, "duration_seconds": 10, "trajectory": []},
                {"task_id": "t2", "template": "data_pipeline", "passed": False, "duration_seconds": 5, "failure_category": "agent_failure", "trajectory": []},
            ],
            "agent_type": "mock",
        }
        report = ReportTemplate.generate("technical_deep_dive", data)
        assert "Summary Statistics" in report
        assert "Per-Task Results" in report

    def test_invalid_template(self):
        """Invalid template should raise ValueError."""
        with pytest.raises(ValueError):
            ReportTemplate.generate("nonexistent", {})

    def test_empty_data(self):
        """Empty data should produce valid report."""
        data = {"run_results": [], "agent_type": "mock"}
        report = ReportTemplate.generate("executive_summary", data)
        assert "mock" in report

    def test_all_templates_available(self):
        """All three templates should be available."""
        assert "research_paper" in ReportTemplate.TEMPLATES
        assert "executive_summary" in ReportTemplate.TEMPLATES
        assert "technical_deep_dive" in ReportTemplate.TEMPLATES

    def test_serialization(self):
        """Report should be a string."""
        data = {"run_results": [], "agent_type": "mock"}
        report = ReportTemplate.generate("executive_summary", data)
        assert isinstance(report, str)

    def test_cli_command(self):
        """Report generation should work with CLI-style data."""
        data = {
            "run_results": [
                {"task_id": "task-1", "template": "task_manager_api", "passed": True,
                 "duration_seconds": 10.5, "trajectory": []},
            ],
            "agent_type": "mock",
            "title": "Test Report",
        }
        report = ReportTemplate.generate("research_paper", data)
        assert "Test Report" in report
