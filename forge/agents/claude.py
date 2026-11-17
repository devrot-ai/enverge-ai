"""Anthropic Claude agent adapter for ForgeLab.

Connects to Anthropic's Claude API for real LLM-powered agent execution.
Uses the Anthropic Python SDK (anthropic) with tool-calling support.

Configuration via environment variables:
    ANTHROPIC_API_KEY - Required API key
    ANTHROPIC_MODEL - Model name (default: claude-sonnet-4-20250514)
    ANTHROPIC_MAX_STEPS - Maximum tool-calling steps (default: 50)
    ANTHROPIC_TEMPERATURE - Sampling temperature (default: 0.0)

Gracefully degrades to MockAgent if API key is not available.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from forge.agents.base import BaseAgent
from forge.core.schemas import (
    AgentConfig,
    RunConfig,
    TaskSpec,
    Trajectory,
    TrajectoryStep,
)

logger = logging.getLogger(__name__)

# Tool definitions for Claude
TOOLS = [
    {
        "name": "list_files",
        "description": "List files and directories in the given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path within the workspace.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_code",
        "description": "Search for a pattern in code files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Pattern to search for.",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in.",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file (creates or overwrites).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file.",
                },
                "content": {
                    "type": "string",
                    "description": "File content to write.",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Edit a file by replacing text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file.",
                },
                "old_text": {
                    "type": "string",
                    "description": "Text to replace.",
                },
                "new_text": {
                    "type": "string",
                    "description": "Replacement text.",
                },
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "execute_command",
        "description": "Execute a shell command in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds.",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "run_tests",
        "description": "Run pytest on the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_path": {
                    "type": "string",
                    "description": "Path to test file or directory.",
                },
            },
        },
    },
    {
        "name": "task_complete",
        "description": "Signal that the task is complete.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Summary of changes made.",
                },
            },
            "required": ["summary"],
        },
    },
]

SYSTEM_PROMPT = """You are an expert software engineer tasked with fixing bugs in code.

You have access to tools for reading, writing, and editing files, searching code, and running commands.

Your workflow:
1. Read the task description carefully
2. Explore the codebase to understand the structure
3. Locate the bug using search and file reading
4. Implement the fix
5. Run tests to verify your fix
6. Call task_complete when done

Be thorough and methodical. Test your changes before declaring the task complete."""


def _check_anthropic_available() -> bool:
    """Check if Anthropic SDK and API key are available."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return False
    try:
        import anthropic  # noqa: F401

        return True
    except ImportError:
        return False


class ClaudeAgent(BaseAgent):
    """Anthropic Claude agent with tool-calling support.

    Uses the Anthropic Python SDK to execute tasks with Claude models.
    Falls back to graceful error if API is unavailable.
    """

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.model = config.model or config.metadata.get("model", "claude-sonnet-4-20250514")
        self.max_steps = config.max_steps or config.metadata.get("max_steps", 50)
        self.temperature = config.temperature or config.metadata.get("temperature", 0.0)
        self._client = None
        self._available = False
        self._token_usage = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

        if _check_anthropic_available():
            try:
                import anthropic

                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
                base_url = os.environ.get("ANTHROPIC_BASE_URL")
                self._client = anthropic.Anthropic(
                    api_key=api_key,
                    base_url=base_url,
                )
                self._available = True
                logger.info("Claude agent initialized with model %s", self.model)
            except Exception as e:
                logger.warning("Failed to initialize Claude agent: %s", e)
        else:
            logger.warning(
                "Anthropic SDK or API key not available. "
                "ClaudeAgent will return error trajectory."
            )

    def execute(
        self,
        task: TaskSpec,
        workspace: Path,
        run_config: RunConfig,
    ) -> Trajectory:
        """Execute a task using Claude with tool-calling."""
        trajectory = Trajectory(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            task_id=task.task_id,
            steps=[],
            started_at=time.time(),
            completed_at=None,
            status="running",
        )

        if not self._available:
            step = TrajectoryStep(
                step_number=0,
                tool_name="error",
                tool_input={"error": "Anthropic API not available"},
                tool_output="Install `anthropic` package and set ANTHROPIC_API_KEY.",
                duration=0.0,
                success=False,
            )
            trajectory.steps.append(step)
            trajectory.completed_at = time.time()
            trajectory.status = "failed"
            return trajectory

        # Build messages
        messages = [
            {
                "role": "user",
                "content": f"Task: {task.description}\n\nConstraints: {task.constraints}",
            }
        ]

        step_num = 0
        while step_num < self.max_steps:
            step_num += 1
            step_start = time.time()

            try:
                response = self._client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=self.temperature,
                    system=SYSTEM_PROMPT,
                    messages=messages,
                    tools=TOOLS,
                )

                # Track token usage
                if hasattr(response, "usage"):
                    self._token_usage["input_tokens"] += response.usage.input_tokens
                    self._token_usage["output_tokens"] += response.usage.output_tokens

                # Check for tool calls
                if any(
                    block.type == "tool_use" for block in response.content
                ):
                    # Add assistant message
                    messages.append(
                        {
                            "role": "assistant",
                            "content": response.content,
                        }
                    )

                    # Execute each tool call
                    for block in response.content:
                        if block.type == "tool_use":
                            tool_name = block.name
                            tool_input = block.input
                            tool_result = self._execute_tool(
                                tool_name, tool_input, workspace
                            )

                            duration = time.time() - step_start
                            trajectory.steps.append(
                                TrajectoryStep(
                                    step_number=step_num,
                                    tool_name=tool_name,
                                    tool_input=tool_input,
                                    tool_output=str(tool_result),
                                    duration=duration,
                                    success=tool_result.get("success", True),
                                )
                            )

                            # Add tool result
                            messages.append(
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "tool_result",
                                            "tool_use_id": block.id,
                                            "content": str(tool_result.get("output", "")),
                                        }
                                    ],
                                }
                            )

                            # Check if task complete
                            if tool_name == "task_complete":
                                trajectory.completed_at = time.time()
                                trajectory.status = "completed"
                                return trajectory

                else:
                    # Text response only
                    text = ""
                    for block in response.content:
                        if block.type == "text":
                            text += block.text

                    duration = time.time() - step_start
                    trajectory.steps.append(
                        TrajectoryStep(
                            step_number=step_num,
                            tool_name="text_response",
                            tool_input={},
                            tool_output=text,
                            duration=duration,
                            success=True,
                        )
                    )
                    messages.append(
                        {"role": "assistant", "content": text}
                    )
                    # If no tool call, agent may be done
                    break

            except Exception as e:
                duration = time.time() - step_start
                trajectory.steps.append(
                    TrajectoryStep(
                        step_number=step_num,
                        tool_name="error",
                        tool_input={},
                        tool_output=str(e),
                        duration=duration,
                        success=False,
                    )
                )
                trajectory.completed_at = time.time()
                trajectory.status = "failed"
                return trajectory

        trajectory.completed_at = time.time()
        trajectory.status = "completed"
        return trajectory

    def _execute_tool(
        self, tool_name: str, tool_input: dict[str, Any], workspace: Path
    ) -> dict[str, Any]:
        """Execute a tool call inline."""
        try:
            if tool_name == "list_files":
                target = workspace / tool_input.get("path", ".")
                if not str(target.resolve()).startswith(str(workspace.resolve())):
                    return {"output": "Error: Path traversal detected.", "success": False}
                items = []
                if target.is_dir():
                    for item in target.iterdir():
                        items.append(item.name)
                return {"output": json.dumps({"files": sorted(items)}), "success": True}

            elif tool_name == "read_file":
                target = workspace / tool_input.get("path", "")
                if not str(target.resolve()).startswith(str(workspace.resolve())):
                    return {"output": "Error: Path traversal detected.", "success": False}
                if not target.is_file():
                    return {"output": f"Error: File not found: {target}", "success": False}
                return {"output": target.read_text(encoding="utf-8", errors="replace"), "success": True}

            elif tool_name == "search_code":
                pattern = tool_input.get("pattern", "")
                search_dir = workspace / tool_input.get("path", ".")
                if not str(search_dir.resolve()).startswith(str(workspace.resolve())):
                    return {"output": "Error: Path traversal detected.", "success": False}
                results = []
                for py_file in search_dir.rglob("*.py"):
                    try:
                        content = py_file.read_text(encoding="utf-8", errors="replace")
                        for i, line in enumerate(content.splitlines(), 1):
                            if pattern in line:
                                results.append(
                                    f"{py_file.relative_to(workspace)}:{i}: {line.strip()}"
                                )
                    except Exception:
                        pass
                return {"output": json.dumps({"matches": results[:50]}), "success": True}

            elif tool_name == "write_file":
                target = workspace / tool_input.get("path", "")
                if not str(target.resolve()).startswith(str(workspace.resolve())):
                    return {"output": "Error: Path traversal detected.", "success": False}
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(tool_input.get("content", ""), encoding="utf-8")
                return {
                    "output": f"File written: {target.relative_to(workspace)}",
                    "success": True,
                }

            elif tool_name == "edit_file":
                target = workspace / tool_input.get("path", "")
                if not str(target.resolve()).startswith(str(workspace.resolve())):
                    return {"output": "Error: Path traversal detected.", "success": False}
                content = target.read_text(encoding="utf-8", errors="replace")
                old = tool_input.get("old_text", "")
                new = tool_input.get("new_text", "")
                if old not in content:
                    return {"output": "Error: Text not found in file.", "success": False}
                target.write_text(content.replace(old, new), encoding="utf-8")
                return {"output": "File edited successfully", "success": True}

            elif tool_name == "execute_command":
                import subprocess

                cmd = tool_input.get("command", "")
                timeout = tool_input.get("timeout", 30)
                result = subprocess.run(
                    cmd, shell=True, cwd=str(workspace),
                    capture_output=True, text=True, timeout=timeout,
                )
                output = result.stdout
                if result.stderr:
                    output += result.stderr
                return {"output": output[:10000], "success": result.returncode == 0}

            elif tool_name == "run_tests":
                import subprocess

                test_path = tool_input.get("test_path", str(workspace))
                result = subprocess.run(
                    ["python", "-m", "pytest", test_path, "-v", "--tb=short"],
                    cwd=str(workspace), capture_output=True, text=True, timeout=60,
                )
                output = result.stdout
                if result.stderr:
                    output += result.stderr
                return {"output": output[:10000], "success": result.returncode == 0}

            elif tool_name == "task_complete":
                return {
                    "output": tool_input.get("summary", "Task complete"),
                    "success": True,
                }

            else:
                return {"output": f"Unknown tool: {tool_name}", "success": False}

        except Exception as e:
            return {"output": str(e), "success": False}

    def get_available_tools(self) -> list[str]:
        """List available tool names."""
        return [tool["name"] for tool in TOOLS]

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics including token usage."""
        stats = super().get_stats()
        stats.update(
            {
                "model": self.model,
                "available": self._available,
                "token_usage": self._token_usage.copy(),
            }
        )
        return stats
