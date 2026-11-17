"""Ollama/vLLM open-source model adapter for ForgeLab.

Connects to local LLM servers via Ollama or vLLM for open-source model
agent execution. Supports any OpenAI-compatible API endpoint.

Configuration via environment variables:
    OLLAMA_BASE_URL - Ollama server URL (default: http://localhost:11434)
    OLLAMA_MODEL - Model name (default: llama3.1)
    VLLM_BASE_URL - vLLM server URL (default: http://localhost:8000)
    VLLM_MODEL - Model name (default: meta-llama/Llama-3.1-8B-Instruct)
    OPEN_SOURCE_PROVIDER - Provider: 'ollama' or 'vllm' (default: ollama)

Gracefully degrades if server is not reachable.
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

# OpenAI-compatible tool definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in the given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path."},
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
                    "path": {"type": "string", "description": "Relative path."},
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
                    "pattern": {"type": "string", "description": "Pattern."},
                    "path": {"type": "string", "description": "Directory."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path."},
                    "content": {"type": "string", "description": "Content."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file by replacing text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path."},
                    "old_text": {"type": "string", "description": "Text to replace."},
                    "new_text": {"type": "string", "description": "Replacement."},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute a shell command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command."},
                    "timeout": {"type": "integer", "description": "Timeout (s)."},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run pytest on the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_path": {"type": "string", "description": "Test path."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_complete",
            "description": "Signal that the task is complete.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Summary."},
                },
                "required": ["summary"],
            },
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


def _check_server_available(base_url: str) -> bool:
    """Check if the LLM server is reachable."""
    try:
        import urllib.request

        url = f"{base_url}/v1/models" if "vllm" in base_url or "8000" in base_url else f"{base_url}/api/tags"
        req = urllib.request.Request(url, method="GET")
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False


class OpenSourceAgent(BaseAgent):
    """Open-source model agent via Ollama or vLLM.

    Connects to local LLM servers for agent execution.
    Falls back to graceful error if server is unavailable.
    """

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.provider = config.provider or config.metadata.get("provider", os.environ.get("OPEN_SOURCE_PROVIDER", "ollama"))
        self.model = config.model or config.metadata.get(
            "model",
            os.environ.get("OLLAMA_MODEL", "llama3.1")
            if self.provider == "ollama"
            else os.environ.get("VLLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct"),
        )
        self.max_steps = config.max_steps or config.metadata.get("max_steps", 50)
        self.temperature = config.temperature or config.metadata.get("temperature", 0.0)

        if self.provider == "ollama":
            self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            # Ollama OpenAI-compatible endpoint
            self.api_url = f"{self.base_url}/v1"
        else:
            self.base_url = os.environ.get("VLLM_BASE_URL", "http://localhost:8000")
            self.api_url = f"{self.base_url}/v1"

        self._client = None
        self._available = False
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0}

        if _check_server_available(self.base_url):
            try:
                import openai

                self._client = openai.OpenAI(
                    api_key="ollama",  # Ollama doesn't require a key
                    base_url=self.api_url,
                )
                self._available = True
                logger.info(
                    "Open-source agent initialized: %s via %s", self.model, self.provider
                )
            except ImportError:
                logger.warning("OpenAI SDK not installed for %s agent", self.provider)
        else:
            logger.warning(
                "%s server not reachable at %s. "
                "OpenSourceAgent will return error trajectory.",
                self.provider,
                self.base_url,
            )

    def execute(
        self,
        task: TaskSpec,
        workspace: Path,
        run_config: RunConfig,
    ) -> Trajectory:
        """Execute a task using the open-source model."""
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
                tool_input={"error": f"{self.provider} server not available"},
                tool_output=f"Start {self.provider} server and ensure model is loaded.",
                duration=0.0,
                success=False,
            )
            trajectory.steps.append(step)
            trajectory.completed_at = time.time()
            trajectory.status = "failed"
            return trajectory

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Task: {task.description}\n\nConstraints: {task.constraints}",
            },
        ]

        step_num = 0
        while step_num < self.max_steps:
            step_num += 1
            step_start = time.time()

            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOLS,
                    temperature=self.temperature,
                    max_tokens=4096,
                )

                # Track token usage
                if response.usage:
                    self._token_usage["prompt_tokens"] += response.usage.prompt_tokens
                    self._token_usage["completion_tokens"] += response.usage.completion_tokens

                choice = response.choices[0]

                if choice.tool_calls:
                    for tool_call in choice.tool_calls:
                        tool_name = tool_call.function.name
                        tool_input = json.loads(tool_call.function.arguments)
                        tool_result = self._execute_tool(tool_name, tool_input, workspace)

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

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": str(tool_result.get("output", "")),
                            }
                        )

                        if tool_name == "task_complete":
                            trajectory.completed_at = time.time()
                            trajectory.status = "completed"
                            return trajectory

                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tc.model_dump() for tc in choice.tool_calls],
                        }
                    )
                else:
                    text = choice.message.content or ""
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
                    messages.append({"role": "assistant", "content": text})
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
                return {"output": "File edited", "success": True}

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
                return {"output": tool_input.get("summary", "Done"), "success": True}

            else:
                return {"output": f"Unknown tool: {tool_name}", "success": False}

        except Exception as e:
            return {"output": str(e), "success": False}

    def get_available_tools(self) -> list[str]:
        """List available tool names."""
        return [tool["function"]["name"] for tool in TOOLS]

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics."""
        stats = super().get_stats()
        stats.update(
            {
                "model": self.model,
                "provider": self.provider,
                "available": self._available,
                "token_usage": self._token_usage.copy(),
            }
        )
        return stats
