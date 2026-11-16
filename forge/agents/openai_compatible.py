"""OpenAI-compatible agent adapter for ForgeLab.

Connects to any OpenAI-compatible API (OpenAI, Anthropic via adapters,
Ollama, vLLM, etc.) for real LLM-powered agent execution with tool-calling.

Configuration via environment variables:
    FORGELAB_PROVIDER - Provider name (openai, anthropic, ollama, etc.)
    FORGELAB_API_KEY - API key (required for most providers)
    FORGELAB_BASE_URL - API base URL (for custom endpoints)
    FORGELAB_MODEL - Model name (e.g., gpt-4, claude-3-sonnet)
    FORGELAB_MAX_STEPS - Maximum tool-calling steps (default: 50)
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

# ---------------------------------------------------------------------------
# Tool definitions for the LLM
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in the given path.",
            "parameters": {
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
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
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
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a pattern in code files.",
            "parameters": {
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
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (creates or overwrites).",
            "parameters": {
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
    },
    {
        "type": "function",
        "function": {
            "name": "run_public_tests",
            "description": "Run the public test suite and return results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Test command to run (e.g., 'pytest tests/').",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_test_output",
            "description": "View the output of the last test run.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_git_diff",
            "description": "View the current git diff of changes made.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish_task",
            "description": "Signal that the task is complete.",
            "parameters": {
                "type": "object",
                "properties": {
                    "success": {
                        "type": "boolean",
                        "description": "Whether the agent believes the task is solved.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of changes made.",
                    },
                },
                "required": ["success"],
            },
        },
    },
]


class OpenAICompatibleAgent(BaseAgent):
    """Agent that uses an OpenAI-compatible API for tool-calling execution.

    Falls back to a clear error if the API is unavailable or misconfigured.
    Never logs API credentials.
    """

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.provider = os.environ.get("FORGELAB_PROVIDER", "openai")
        self.api_key = os.environ.get("FORGELAB_API_KEY", "")
        self.base_url = os.environ.get("FORGELAB_BASE_URL", "")
        self.model = os.environ.get("FORGELAB_MODEL", "gpt-4")
        self.max_steps = int(os.environ.get("FORGELAB_MAX_STEPS", "50"))
        self.timeout = int(os.environ.get("FORGELAB_TIMEOUT", "60"))
        self.retry_count = int(os.environ.get("FORGELAB_RETRY_COUNT", "3"))

        self._client = None
        self._last_test_output: str | None = None
        self._token_usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}

    def _get_client(self):
        """Lazy-load the OpenAI client. Returns None if not available."""
        if self._client is not None:
            return self._client

        try:
            import openai
        except ImportError:
            logger.warning("openai package not installed; install with 'pip install openai'")
            return None

        if not self.api_key:
            logger.warning("FORGELAB_API_KEY not set; cannot use OpenAI-compatible agent")
            return None

        kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": self.timeout,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url

        self._client = openai.OpenAI(**kwargs)
        return self._client

    def get_available_tools(self) -> list[str]:
        return [
            "list_files",
            "read_file",
            "search_code",
            "write_file",
            "run_public_tests",
            "inspect_test_output",
            "inspect_git_diff",
            "finish_task",
        ]

    def _build_system_prompt(self, task: TaskSpec) -> str:
        """Build the system prompt for the agent."""
        return f"""You are a software engineering agent tasked with fixing a bug in a Python repository.

Task: {task.description}

Constraints:
{chr(10).join(f'- {c}' for c in task.constraints)}

You have access to the following tools:
- list_files: List files in a directory
- read_file: Read file contents
- search_code: Search for patterns in code
- write_file: Write file contents
- run_public_tests: Run the public test suite
- inspect_test_output: View last test output
- inspect_git_diff: View current changes
- finish_task: Signal task completion

Start by exploring the repository structure, then identify the bug, fix it, run tests to verify, and call finish_task when done.
"""

    def _execute_tool_call(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        workspace: Path,
    ) -> str:
        """Execute a tool call and return the result."""
        try:
            if tool_name == "list_files":
                target = workspace / tool_args.get("path", ".")
                if not str(target.resolve()).startswith(str(workspace.resolve())):
                    return "Error: Path traversal detected."
                items = []
                if target.is_dir():
                    for item in target.iterdir():
                        items.append(item.name)
                return json.dumps({"files": sorted(items)})

            elif tool_name == "read_file":
                target = workspace / tool_args.get("path", "")
                if not str(target.resolve()).startswith(str(workspace.resolve())):
                    return "Error: Path traversal detected."
                if not target.is_file():
                    return f"Error: File not found: {target}"
                return target.read_text(encoding="utf-8", errors="replace")

            elif tool_name == "search_code":
                pattern = tool_args.get("pattern", "")
                search_dir = workspace / tool_args.get("path", ".")
                if not str(search_dir.resolve()).startswith(str(workspace.resolve())):
                    return "Error: Path traversal detected."
                results = []
                for py_file in search_dir.rglob("*.py"):
                    try:
                        content = py_file.read_text(encoding="utf-8", errors="replace")
                        for i, line in enumerate(content.splitlines(), 1):
                            if pattern in line:
                                results.append(f"{py_file.relative_to(workspace)}:{i}: {line.strip()}")
                    except Exception:
                        pass
                return json.dumps({"matches": results[:50]})

            elif tool_name == "write_file":
                target = workspace / tool_args.get("path", "")
                if not str(target.resolve()).startswith(str(workspace.resolve())):
                    return "Error: Path traversal detected."
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(tool_args.get("content", ""), encoding="utf-8")
                return f"File written: {target.relative_to(workspace)}"

            elif tool_name == "run_public_tests":
                command = tool_args.get("command", "pytest tests/ -v")
                import subprocess

                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=str(workspace),
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                self._last_test_output = result.stdout + result.stderr
                return self._last_test_output

            elif tool_name == "inspect_test_output":
                return self._last_test_output or "No test output available."

            elif tool_name == "inspect_git_diff":
                import subprocess

                result = subprocess.run(
                    ["git", "diff"],
                    cwd=str(workspace),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return result.stdout or "No changes detected."

            elif tool_name == "finish_task":
                return "Task completion signaled."

            else:
                return f"Error: Unknown tool '{tool_name}'."

        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def execute(
        self,
        task: TaskSpec,
        workspace: Path,
        run_config: RunConfig,
    ) -> Trajectory:
        """Execute the agent using the OpenAI-compatible API."""
        client = self._get_client()
        if client is None:
            # Return a trajectory with a single error step
            step = TrajectoryStep(
                step_index=0,
                observation="API not configured.",
                action="error",
                tool_name=None,
                tool_arguments={},
                tool_result="OpenAI client not available. Set FORGELAB_API_KEY and install 'openai' package.",
                duration_seconds=0.0,
                error="API not configured",
            )
            traj = Trajectory(
                run_id=run_config.run_id,
                task_id=task.task_id,
                agent_id=self.agent_id,
            )
            traj.add_step(step)
            traj.finalize("api_not_configured", 0.0)
            return traj

        system_prompt = self._build_system_prompt(task)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Explore the repository at {workspace} and fix the bug described in the task.",
            },
        ]

        steps: list[TrajectoryStep] = []
        step_index = 0
        start_time = time.time()
        agent_believes_success = False

        while step_index < self.max_steps:
            step_start = time.time()

            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOLS,
                    temperature=0.0,
                )
            except Exception as e:
                error_msg = f"API error: {str(e)}"
                logger.error(error_msg)
                step = TrajectoryStep(
                    step_index=step_index,
                    observation=error_msg,
                    action="error",
                    tool_name=None,
                    tool_arguments={},
                    tool_result=error_msg,
                    duration_seconds=time.time() - step_start,
                    error=error_msg,
                )
                steps.append(step)
                messages.append({"role": "assistant", "content": error_msg})
                step_index += 1
                continue

            # Track token usage
            if hasattr(response, "usage") and response.usage:
                self._token_usage["prompt_tokens"] += response.usage.prompt_tokens or 0
                self._token_usage["completion_tokens"] += response.usage.completion_tokens or 0

            choice = response.choices[0]
            message = choice.message

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    tool_result = self._execute_tool_call(tool_name, tool_args, workspace)

                    step_duration = time.time() - step_start
                    step = TrajectoryStep(
                        step_index=step_index,
                        observation=str(messages[-1].get("content", "")) if messages else "",
                        action=tool_name,
                        tool_name=tool_name,
                        tool_arguments=tool_args,
                        tool_result=tool_result,
                        duration_seconds=step_duration,
                    )
                    steps.append(step)

                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call.model_dump()],
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result,
                        }
                    )

                    if tool_name == "finish_task":
                        agent_believes_success = tool_args.get("success", False)
                        step_index += 1
                        break

                    step_index += 1
            else:
                # Text response without tool call
                text = message.content or ""
                step = TrajectoryStep(
                    step_index=step_index,
                    observation=str(messages[-1].get("content", "")) if messages else "",
                    action="reason",
                    tool_name=None,
                    tool_arguments={},
                    tool_result=text,
                    duration_seconds=time.time() - step_start,
                )
                steps.append(step)
                messages.append({"role": "assistant", "content": text})
                step_index += 1

            if agent_believes_success:
                break

        duration = time.time() - start_time
        traj = Trajectory(
            run_id=run_config.run_id,
            task_id=task.task_id,
            agent_id=self.agent_id,
        )
        for step in steps:
            traj.add_step(step)
        traj.finalize(
            "completed" if agent_believes_success else "max_steps_reached",
            duration,
            self._token_usage.copy(),
        )
        return traj

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats.update(
            {
                "provider": self.provider,
                "model": self.model,
                "max_steps": self.max_steps,
                "token_usage": self._token_usage.copy(),
            }
        )
        return stats
