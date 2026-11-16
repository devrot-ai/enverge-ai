"""Agents module — pluggable agent interface and implementations.

Provides:
- BaseAgent abstract interface
- MockAgent for deterministic testing without API keys
- OpenAICompatibleAgent for real LLM tool-calling
- Agent tools (list_files, read_file, write_file, etc.)
- Agent registry and configuration
"""

__version__ = "0.1.0"

from forge.agents.base import BaseAgent
from forge.agents.config import create_mock_config, load_agent_config_from_env, merge_agent_configs
from forge.agents.mock_agent import MockAgent
from forge.agents.openai_compatible import OpenAICompatibleAgent
from forge.agents.registry import AgentRegistry, get_registry, register_agent
from forge.agents.tools import (
    ToolDefinition,
    ToolExecutor,
    create_tool_executor,
    get_all_tools,
    validate_path,
    validate_tool_args,
)

__all__ = [
    "BaseAgent",
    "MockAgent",
    "OpenAICompatibleAgent",
    "ToolDefinition",
    "ToolExecutor",
    "get_all_tools",
    "create_tool_executor",
    "validate_path",
    "validate_tool_args",
    "AgentRegistry",
    "get_registry",
    "register_agent",
    "load_agent_config_from_env",
    "create_mock_config",
    "merge_agent_configs",
]
