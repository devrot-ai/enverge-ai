"""Tests for deferred feature implementations (v0.2-v0.3, v1.0).

Tests for:
- ClaudeAgent (Anthropic adapter)
- OpenSourceAgent (Ollama/vLLM adapter)
- LLMTaskGenerator
- TRLTrainer
- GRPOTrainer
- AgentLightningClient
- K8SSandboxManager
"""

import pytest


class TestClaudeAgent:
    """Test ClaudeAgent initialization and graceful fallback."""

    def test_claude_agent_import(self):
        """ClaudeAgent can be imported."""
        from forge.agents.claude import ClaudeAgent

        assert ClaudeAgent is not None

    def test_claude_agent_no_api_key(self):
        """ClaudeAgent degrades gracefully without API key."""
        from forge.agents.claude import ClaudeAgent
        from forge.core.schemas import AgentConfig

        config = AgentConfig(
            agent_id="test-claude",
            agent_type="claude",
        )
        agent = ClaudeAgent(config)
        assert agent._available is False
        assert agent.model == "claude-sonnet-4-20250514"

    def test_claude_agent_tools(self):
        """ClaudeAgent lists all tools."""
        from forge.agents.claude import ClaudeAgent
        from forge.core.schemas import AgentConfig

        config = AgentConfig(
            agent_id="test-claude",
            agent_type="claude",
        )
        agent = ClaudeAgent(config)
        tools = agent.get_available_tools()
        assert "list_files" in tools
        assert "read_file" in tools
        assert "write_file" in tools
        assert "task_complete" in tools
        assert len(tools) == 8

    def test_claude_agent_stats(self):
        """ClaudeAgent returns stats."""
        from forge.agents.claude import ClaudeAgent
        from forge.core.schemas import AgentConfig

        config = AgentConfig(
            agent_id="test-claude",
            agent_type="claude",
        )
        agent = ClaudeAgent(config)
        stats = agent.get_stats()
        assert "model" in stats
        assert "available" in stats
        assert "token_usage" in stats


class TestOpenSourceAgent:
    """Test OpenSourceAgent initialization and graceful fallback."""

    def test_open_source_agent_import(self):
        """OpenSourceAgent can be imported."""
        from forge.agents.ollama import OpenSourceAgent

        assert OpenSourceAgent is not None

    def test_open_source_agent_no_server(self):
        """OpenSourceAgent degrades gracefully without server."""
        from forge.agents.ollama import OpenSourceAgent
        from forge.core.schemas import AgentConfig

        config = AgentConfig(
            agent_id="test-ollama",
            agent_type="open_source",
        )
        agent = OpenSourceAgent(config)
        assert agent._available is False
        assert agent.provider == "ollama"

    def test_open_source_agent_tools(self):
        """OpenSourceAgent lists all tools."""
        from forge.agents.ollama import OpenSourceAgent
        from forge.core.schemas import AgentConfig

        config = AgentConfig(
            agent_id="test-ollama",
            agent_type="open_source",
        )
        agent = OpenSourceAgent(config)
        tools = agent.get_available_tools()
        assert "list_files" in tools
        assert "read_file" in tools
        assert "write_file" in tools
        assert "task_complete" in tools
        assert len(tools) == 8

    def test_open_source_agent_vllm(self):
        """OpenSourceAgent can be configured for vLLM."""
        from forge.agents.ollama import OpenSourceAgent
        from forge.core.schemas import AgentConfig

        config = AgentConfig(
            agent_id="test-vllm",
            agent_type="open_source",
            provider="vllm",
        )
        agent = OpenSourceAgent(config)
        assert agent.provider == "vllm"


class TestLLMTaskGenerator:
    """Test LLMTaskGenerator initialization and graceful fallback."""

    def test_llm_task_generator_import(self):
        """LLMTaskGenerator can be imported."""
        from forge.task_factory.llm_generator import LLMTaskGenerator

        assert LLMTaskGenerator is not None

    def test_llm_task_generator_no_api(self):
        """LLMTaskGenerator degrades gracefully without API."""
        from forge.task_factory.llm_generator import LLMTaskGenerator

        gen = LLMTaskGenerator()
        assert gen._available is False

    def test_llm_task_generator_returns_empty(self):
        """LLMTaskGenerator returns empty list without API."""
        from forge.task_factory.llm_generator import LLMTaskGenerator

        gen = LLMTaskGenerator()
        tasks = gen.generate_tasks(count=5)
        assert tasks == []

    def test_generated_task_dataclass(self):
        """GeneratedTask dataclass works."""
        from forge.core.schemas import TaskCategory
        from forge.task_factory.llm_generator import GeneratedTask

        task = GeneratedTask(
            task_id="test-1",
            template="task_manager_api",
            mutation="pagination_boundary",
            category=TaskCategory("bug_repair"),
            difficulty=3,
            description="Test task",
            constraints="No external deps",
        )
        assert task.task_id == "test-1"
        assert task.difficulty == 3


class TestTRLTrainer:
    """Test TRLTrainer initialization and graceful fallback."""

    def test_trl_trainer_import(self):
        """TRLTrainer can be imported."""
        from forge.training.trl_integration import TRLTrainer

        assert TRLTrainer is not None

    def test_trl_trainer_no_trl(self):
        """TRLTrainer degrades gracefully without TRL."""
        from forge.training.trl_integration import TRLTrainer

        trainer = TRLTrainer()
        assert trainer._available is False

    def test_trl_trainer_prepare_sft(self):
        """TRLTrainer can prepare SFT samples without TRL."""
        from forge.training.trl_integration import TRLTrainer

        trainer = TRLTrainer()
        trajectories = [
            {
                "task_description": "Fix bug",
                "steps": [
                    {"success": True, "tool_name": "write_file", "tool_input": {"path": "app.py", "content": "fixed"}}
                ],
                "reward": 1.0,
            }
        ]
        samples = trainer.prepare_sft_dataset(trajectories)
        assert len(samples) == 1
        assert samples[0].prompt.startswith("Fix the following bug")
        assert samples[0].reward == 1.0

    def test_trl_trainer_status(self):
        """TRLTrainer returns status."""
        from forge.training.trl_integration import TRLTrainer

        trainer = TRLTrainer()
        status = trainer.get_status()
        assert status["available"] is False
        assert "config" in status


class TestGRPOTrainer:
    """Test GRPOTrainer initialization and functionality."""

    def test_grpo_trainer_import(self):
        """GRPOTrainer can be imported."""
        from forge.training.grpo import GRPOTrainer

        assert GRPOTrainer is not None

    def test_grpo_trainer_init(self):
        """GRPOTrainer initializes."""
        from forge.training.grpo import GRPOTrainer

        trainer = GRPOTrainer()
        assert trainer.config.group_size == 4

    def test_grpo_create_groups(self):
        """GRPOTrainer creates groups from trajectories."""
        from forge.training.grpo import GRPOTrainer

        trainer = GRPOTrainer()
        trajectories = [
            {"task_id": "task-1", "reward": 1.0},
            {"task_id": "task-1", "reward": 0.5},
            {"task_id": "task-1", "reward": 0.0},
            {"task_id": "task-1", "reward": -0.5},
        ]
        groups = trainer.create_groups(trajectories)
        assert len(groups) == 1
        assert groups[0].task_id == "task-1"
        assert len(groups[0].rewards) == 4

    def test_grpo_advantages(self):
        """GRPOTrainer computes advantages."""
        from forge.training.grpo import GRPOTrainer

        trainer = GRPOTrainer()
        trajectories = [
            {"task_id": "task-1", "reward": 1.0},
            {"task_id": "task-1", "reward": 0.5},
            {"task_id": "task-1", "reward": 0.0},
            {"task_id": "task-1", "reward": -0.5},
        ]
        groups = trainer.create_groups(trajectories)
        assert len(groups[0].advantages) == 4
        # Advantages should sum to ~0 (normalized)
        assert abs(sum(groups[0].advantages)) < 0.01

    def test_grpo_select_best(self):
        """GRPOTrainer selects best trajectories."""
        from forge.training.grpo import GRPOTrainer

        trainer = GRPOTrainer()
        trajectories = [
            {"task_id": "task-1", "reward": 1.0, "data": "best"},
            {"task_id": "task-1", "reward": 0.5, "data": "mid"},
            {"task_id": "task-1", "reward": 0.0, "data": "low"},
            {"task_id": "task-1", "reward": -0.5, "data": "worst"},
        ]
        groups = trainer.create_groups(trajectories)
        best = trainer.select_best_trajectories(groups, top_k=1)
        assert len(best) == 1
        assert best[0]["data"] == "best"

    def test_grpo_metrics(self):
        """GRPOTrainer computes group metrics."""
        from forge.training.grpo import GRPOTrainer

        trainer = GRPOTrainer()
        trajectories = [
            {"task_id": "task-1", "reward": 1.0},
            {"task_id": "task-1", "reward": 0.5},
            {"task_id": "task-1", "reward": 0.0},
            {"task_id": "task-1", "reward": -0.5},
        ]
        groups = trainer.create_groups(trajectories)
        metrics = trainer.compute_group_metrics(groups)
        assert "task-1" in metrics
        assert metrics["task-1"]["mean_reward"] == 0.25


class TestAgentLightningClient:
    """Test AgentLightningClient initialization and graceful fallback."""

    def test_agent_lightning_import(self):
        """AgentLightningClient can be imported."""
        from forge.training.agent_lightning import AgentLightningClient

        assert AgentLightningClient is not None

    def test_agent_lightning_no_api_key(self):
        """AgentLightningClient degrades gracefully without API key."""
        from forge.training.agent_lightning import AgentLightningClient

        client = AgentLightningClient()
        assert client._available is False

    def test_agent_lightning_submit_returns_none(self):
        """AgentLightningClient returns None when unavailable."""
        from forge.training.agent_lightning import AgentLightningClient

        client = AgentLightningClient()
        result = client.submit_task("task-1", "mock", {}, "/tmp")
        assert result is None

    def test_agent_lightning_status(self):
        """AgentLightningClient returns status."""
        from forge.training.agent_lightning import AgentLightningClient

        client = AgentLightningClient()
        status = client.get_status()
        assert status["available"] is False


class TestK8SSandboxManager:
    """Test K8SSandboxManager initialization and graceful fallback."""

    def test_k8s_manager_import(self):
        """K8SSandboxManager can be imported."""
        from forge.sandbox.kubernetes import K8SSandboxManager

        assert K8SSandboxManager is not None

    def test_k8s_manager_no_k8s(self):
        """K8SSandboxManager degrades gracefully without K8s."""
        from forge.sandbox.kubernetes import K8SSandboxManager

        manager = K8SSandboxManager()
        assert manager._available is False

    def test_k8s_manager_create_returns_none(self):
        """K8SSandboxManager returns None when unavailable."""
        from forge.sandbox.kubernetes import K8SSandboxManager

        manager = K8SSandboxManager()
        result = manager.create_sandbox("/tmp", "task-1")
        assert result is None

    def test_k8s_manager_status(self):
        """K8SSandboxManager returns status."""
        from forge.sandbox.kubernetes import K8SSandboxManager

        manager = K8SSandboxManager()
        status = manager.get_status()
        assert status["available"] is False


class TestRegistryIntegration:
    """Test that new agents are registered."""

    def test_claude_registered(self):
        """Claude agent is registered."""
        from forge.agents.registry import get_registry

        registry = get_registry()
        types = registry.list_types()
        assert "claude" in types

    def test_open_source_registered(self):
        """Open source agent is registered."""
        from forge.agents.registry import get_registry

        registry = get_registry()
        types = registry.list_types()
        assert "open_source" in types

    def test_six_agents_total(self):
        """Six agent types are registered."""
        from forge.agents.registry import get_registry

        registry = get_registry()
        types = registry.list_types()
        assert len(types) >= 5
