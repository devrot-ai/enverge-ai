"""Tests for v0.8 features: new templates, cross-domain curriculum, resource manager,
container signing, security audit, and benchmark publication."""

import json
import os
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# New Template Tests (database_query, api_integration, dsl)
# ---------------------------------------------------------------------------


class TestV08Templates:
    """Test the new v0.8 templates."""

    def test_database_query_template_exists(self):
        """database_query template should be registered."""
        from forge.world_factory.templates import get_template

        template = get_template("database_query")
        assert template is not None
        assert template["name"] == "database_query"
        assert "app.py" in template["files"]

    def test_database_query_has_classes(self):
        """database_query should have expected classes."""
        from forge.world_factory.templates import get_template

        template = get_template("database_query")
        app_code = template["files"]["app.py"]
        for cls in ["QueryBuilder", "ConnectionPool", "ResultCache", "IndexManager", "QueryOptimizer"]:
            assert f"class {cls}" in app_code

    def test_api_integration_template_exists(self):
        """api_integration template should be registered."""
        from forge.world_factory.templates import get_template

        template = get_template("api_integration")
        assert template is not None
        assert template["name"] == "api_integration"

    def test_api_integration_has_classes(self):
        """api_integration should have expected classes."""
        from forge.world_factory.templates import get_template

        template = get_template("api_integration")
        app_code = template["files"]["app.py"]
        for cls in ["APIClient", "RateLimiter", "TokenManager", "RetryHandler", "ResponseParser"]:
            assert f"class {cls}" in app_code

    def test_dsl_template_exists(self):
        """dsl template should be registered."""
        from forge.world_factory.templates import get_template

        template = get_template("dsl")
        assert template is not None
        assert template["name"] == "dsl"

    def test_dsl_has_classes(self):
        """dsl should have expected classes."""
        from forge.world_factory.templates import get_template

        template = get_template("dsl")
        app_code = template["files"]["app.py"]
        for cls in ["Lexer", "Parser", "AST", "Interpreter", "Validator"]:
            assert f"class {cls}" in app_code

    def test_new_mutations_registered(self):
        """New mutations should be registered."""
        from forge.world_factory.seeder import get_mutation

        for mut_id in [
            "sql_injection", "n_plus_one_query", "missing_index",
            "rate_limit_bypass", "auth_token_leak", "schema_mismatch",
            "syntax_error", "type_coercion", "undefined_reference",
        ]:
            mutation = get_mutation(mut_id)
            assert mutation is not None, f"Mutation {mut_id} not found"


# ---------------------------------------------------------------------------
# Cross-Domain Curriculum Tests
# ---------------------------------------------------------------------------


class TestCrossDomainCurriculum:
    """Test cross-domain curriculum functionality."""

    def test_add_domain(self):
        """Should add a domain."""
        from forge.curriculum.cross_domain import CrossDomainCurriculum

        curriculum = CrossDomainCurriculum()
        curriculum.add_domain("task_manager_api")
        assert "task_manager_api" in curriculum.domains

    def test_add_multiple_domains(self):
        """Should add multiple domains."""
        from forge.curriculum.cross_domain import CrossDomainCurriculum

        curriculum = CrossDomainCurriculum()
        curriculum.add_domain("task_manager_api")
        curriculum.add_domain("data_pipeline")
        assert len(curriculum.domains) == 2

    def test_domain_state_update(self):
        """Should update domain state after run."""
        from forge.core.schemas import RunResult, RunStatus
        from forge.curriculum.cross_domain import CrossDomainCurriculum

        curriculum = CrossDomainCurriculum()
        curriculum.add_domain("test_domain")

        result = RunResult(run_id="r1", task_id="t1", agent_id="a1", status=RunStatus.COMPLETED)
        result.passed = True
        curriculum.update("test_domain", result)
        assert curriculum.domains["test_domain"].total_runs == 1
        assert curriculum.domains["test_domain"].pass_rate == 1.0

    def test_domain_state_failure(self):
        """Should track failures correctly."""
        from forge.core.schemas import RunResult, RunStatus
        from forge.curriculum.cross_domain import CrossDomainCurriculum

        curriculum = CrossDomainCurriculum()
        curriculum.add_domain("test_domain")

        result = RunResult(run_id="r1", task_id="t1", agent_id="a1", status=RunStatus.COMPLETED)
        result.passed = False
        curriculum.update("test_domain", result)
        assert curriculum.domains["test_domain"].pass_rate == 0.0

    def test_get_domain_summary(self):
        """Should return domain summary."""
        from forge.curriculum.cross_domain import CrossDomainCurriculum

        curriculum = CrossDomainCurriculum()
        curriculum.add_domain("domain1")
        curriculum.add_domain("domain2")
        summary = curriculum.get_domain_summary()
        assert "domain1" in summary
        assert "domain2" in summary

    def test_to_dict(self):
        """Should serialize to dict."""
        from forge.curriculum.cross_domain import CrossDomainCurriculum

        curriculum = CrossDomainCurriculum(transfer_strategy="random")
        curriculum.add_domain("test")
        d = curriculum.to_dict()
        assert d["transfer_strategy"] == "random"
        assert "test" in d["domains"]

    def test_transfer_strategy_none(self):
        """Should support none transfer strategy."""
        from forge.curriculum.cross_domain import CrossDomainCurriculum

        curriculum = CrossDomainCurriculum(transfer_strategy="none")
        assert curriculum.transfer_strategy == "none"

    def test_empty_curriculum(self):
        """Should handle empty curriculum."""
        from forge.curriculum.cross_domain import CrossDomainCurriculum

        curriculum = CrossDomainCurriculum()
        summary = curriculum.get_domain_summary()
        assert len(summary) == 0


# ---------------------------------------------------------------------------
# Resource Manager Tests
# ---------------------------------------------------------------------------


class TestResourceManager:
    """Test resource-aware scheduling."""

    def test_create_manager(self):
        """Should create a resource manager."""
        from forge.runner.resource_manager import ResourceManager

        manager = ResourceManager()
        assert manager.max_workers == 4

    def test_check_available(self):
        """Should check resource availability."""
        from forge.runner.resource_manager import ResourceManager

        manager = ResourceManager(max_workers=2, max_cpu_percent=99.0, max_memory_percent=99.0)
        assert manager.check_available() is True

    def test_allocate_and_release(self):
        """Should allocate and release workers."""
        from forge.runner.resource_manager import ResourceManager

        manager = ResourceManager(max_workers=2, max_cpu_percent=99.0, max_memory_percent=99.0)
        assert manager.allocate() is True
        assert manager.active_workers == 1
        manager.release()
        assert manager.active_workers == 0

    def test_max_workers_limit(self):
        """Should respect max workers limit."""
        from forge.runner.resource_manager import ResourceManager

        manager = ResourceManager(max_workers=1, max_cpu_percent=99.0, max_memory_percent=99.0)
        assert manager.allocate() is True
        assert manager.allocate() is False

    def test_get_utilization(self):
        """Should return resource usage."""
        from forge.runner.resource_manager import ResourceManager

        manager = ResourceManager()
        usage = manager.get_utilization()
        assert hasattr(usage, "cpu_percent")
        assert hasattr(usage, "memory_percent")
        assert hasattr(usage, "active_workers")

    def test_should_pause(self):
        """Should check if should pause."""
        from forge.runner.resource_manager import ResourceManager

        manager = ResourceManager(max_cpu_percent=99.0, max_memory_percent=99.0)
        # With high thresholds, should not pause
        assert manager.should_pause() is False

    def test_to_dict(self):
        """Should serialize to dict."""
        from forge.runner.resource_manager import ResourceManager

        manager = ResourceManager(max_cpu_percent=90.0)
        d = manager.to_dict()
        assert d["max_cpu_percent"] == 90.0
        assert "psutil_available" in d


# ---------------------------------------------------------------------------
# Container Signing Tests
# ---------------------------------------------------------------------------


class TestImageSigner:
    """Test container image signing."""

    def test_sign_image(self, tmp_path):
        """Should sign an image directory."""
        from forge.sandbox.signing import ImageSigner

        # Create a mock image directory
        image_dir = tmp_path / "image"
        image_dir.mkdir()
        (image_dir / "Dockerfile").write_text("FROM python:3.11")

        signer = ImageSigner(signatures_path=str(tmp_path / "sigs.json"))
        sig = signer.sign(image_dir)
        assert sig.dockerfile_hash != ""

    def test_verify_image(self, tmp_path):
        """Should verify a signed image."""
        from forge.sandbox.signing import ImageSigner

        image_dir = tmp_path / "image"
        image_dir.mkdir()
        (image_dir / "Dockerfile").write_text("FROM python:3.11")

        signer = ImageSigner(signatures_path=str(tmp_path / "sigs.json"))
        signer.sign(image_dir)
        assert signer.verify(image_dir) is True

    def test_verify_tampered_image(self, tmp_path):
        """Should detect tampered image."""
        from forge.sandbox.signing import ImageSigner

        image_dir = tmp_path / "image"
        image_dir.mkdir()
        (image_dir / "Dockerfile").write_text("FROM python:3.11")

        signer = ImageSigner(signatures_path=str(tmp_path / "sigs.json"))
        signer.sign(image_dir)

        # Tamper with the Dockerfile
        (image_dir / "Dockerfile").write_text("FROM python:3.12")
        assert signer.verify(image_dir) is False

    def test_list_signatures(self, tmp_path):
        """Should list signatures."""
        from forge.sandbox.signing import ImageSigner

        image_dir = tmp_path / "image"
        image_dir.mkdir()
        (image_dir / "Dockerfile").write_text("FROM python:3.11")

        signer = ImageSigner(signatures_path=str(tmp_path / "sigs.json"))
        signer.sign(image_dir)
        sigs = signer.list_signatures()
        assert len(sigs) == 1

    def test_remove_signature(self, tmp_path):
        """Should remove a signature."""
        from forge.sandbox.signing import ImageSigner

        image_dir = tmp_path / "image"
        image_dir.mkdir()
        (image_dir / "Dockerfile").write_text("FROM python:3.11")

        signer = ImageSigner(signatures_path=str(tmp_path / "sigs.json"))
        signer.sign(image_dir)
        assert signer.remove(image_dir) is True
        assert len(signer.list_signatures()) == 0

    def test_verify_unsigned(self, tmp_path):
        """Should return False for unsigned image."""
        from forge.sandbox.signing import ImageSigner

        image_dir = tmp_path / "image"
        image_dir.mkdir()
        (image_dir / "Dockerfile").write_text("FROM python:3.11")

        signer = ImageSigner(signatures_path=str(tmp_path / "sigs.json"))
        assert signer.verify(image_dir) is False


# ---------------------------------------------------------------------------
# Security Audit Tests
# ---------------------------------------------------------------------------


class TestSecurityAudit:
    """Test security audit functionality."""

    def test_audit_clean_workspace(self, tmp_path):
        """Should find no issues in clean workspace."""
        from forge.core.security_audit import SecurityAuditor

        (tmp_path / "clean.py").write_text("x = 1 + 2\n")
        auditor = SecurityAuditor()
        result = auditor.audit_workspace(tmp_path)
        assert result.clean is True

    def test_detect_hardcoded_password(self, tmp_path):
        """Should detect hardcoded passwords."""
        from forge.core.security_audit import SecurityAuditor

        (tmp_path / "insecure.py").write_text('password = "secret123"\n')
        auditor = SecurityAuditor()
        result = auditor.audit_workspace(tmp_path)
        assert result.clean is False
        assert len(result.findings) > 0

    def test_detect_eval(self, tmp_path):
        """Should detect eval() usage."""
        from forge.core.security_audit import SecurityAuditor

        (tmp_path / "insecure.py").write_text("result = eval(user_input)\n")
        auditor = SecurityAuditor()
        result = auditor.audit_workspace(tmp_path)
        assert any(f.category == "insecure_pattern" for f in result.findings)

    def test_summary(self, tmp_path):
        """Should generate summary."""
        from forge.core.security_audit import SecurityAuditor

        (tmp_path / "insecure.py").write_text('password = "secret"\n')
        auditor = SecurityAuditor()
        result = auditor.audit_workspace(tmp_path)
        summary = result.summary()
        assert "high" in summary

    def test_generate_report(self, tmp_path):
        """Should generate Markdown report."""
        from forge.core.security_audit import SecurityAuditor

        (tmp_path / "insecure.py").write_text('password = "secret"\n')
        auditor = SecurityAuditor()
        result = auditor.audit_workspace(tmp_path)
        report = auditor.generate_report(result)
        assert "# Security Audit Report" in report

    def test_empty_workspace(self, tmp_path):
        """Should handle empty workspace."""
        from forge.core.security_audit import SecurityAuditor

        auditor = SecurityAuditor()
        result = auditor.audit_workspace(tmp_path)
        assert result.total_files == 0
        assert result.clean is True


# ---------------------------------------------------------------------------
# Benchmark Publisher Tests
# ---------------------------------------------------------------------------


class TestBenchmarkPublisher:
    """Test benchmark publication."""

    def test_generate_report(self):
        """Should generate a Markdown report."""
        from forge.evaluation.publish import BenchmarkPublisher, BenchmarkResult

        results = [
            BenchmarkResult(agent_type="mock", task_id="t1", passed=True, duration=1.0, template="task_manager_api"),
            BenchmarkResult(agent_type="mock", task_id="t2", passed=False, duration=2.0, template="data_pipeline", failure_category="agent_failure"),
        ]
        publisher = BenchmarkPublisher()
        report = publisher.generate_report(results)
        assert "# Benchmark Report" in report
        assert "mock" in report

    def test_generate_empty_report(self):
        """Should handle empty results."""
        from forge.evaluation.publish import BenchmarkPublisher

        publisher = BenchmarkPublisher()
        report = publisher.generate_report([])
        assert "No results" in report

    def test_publish_report(self, tmp_path):
        """Should publish report to files."""
        from forge.evaluation.publish import BenchmarkPublisher, BenchmarkResult

        results = [
            BenchmarkResult(agent_type="mock", task_id="t1", passed=True, duration=1.0),
        ]
        publisher = BenchmarkPublisher()
        output_dir = str(tmp_path / "reports")
        path = publisher.publish(results, output_dir)
        assert Path(path).exists()

    def test_baseline_comparison(self, tmp_path):
        """Should compare with baseline."""
        from forge.evaluation.publish import BenchmarkPublisher

        baselines_path = str(tmp_path / "baselines.yaml")
        publisher = BenchmarkPublisher(baselines_path=baselines_path)
        publisher.set_baseline("mock", 0.5)
        comparison = publisher.compare_with_baseline("mock", 0.7)
        assert "IMPROVEMENT" in comparison

    def test_baseline_regression(self, tmp_path):
        """Should detect regression."""
        from forge.evaluation.publish import BenchmarkPublisher

        baselines_path = str(tmp_path / "baselines.yaml")
        publisher = BenchmarkPublisher(baselines_path=baselines_path)
        publisher.set_baseline("mock", 0.8)
        comparison = publisher.compare_with_baseline("mock", 0.5)
        assert "REGRESSION" in comparison

    def test_no_baseline(self, tmp_path):
        """Should handle missing baseline."""
        from forge.evaluation.publish import BenchmarkPublisher

        publisher = BenchmarkPublisher(baselines_path=str(tmp_path / "nonexistent.yaml"))
        comparison = publisher.compare_with_baseline("unknown", 0.5)
        assert "No baseline" in comparison
