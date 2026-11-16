"""Tool execution within sandboxed environments.

Provides a wrapper around ToolExecutor that runs tool calls
inside Docker containers for isolation.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from forge.agents.tools import ToolExecutor, validate_tool_args
from forge.core.errors import SandboxExecutionError


class SandboxedToolExecutor:
    """Executes agent tools inside a Docker sandbox.

    Wraps ToolExecutor to run commands within an isolated container
    instead of on the host system.
    """

    def __init__(
        self,
        workspace: Path,
        container_id: str,
        sandbox_image: str = "forgelab-sandbox:latest",
    ):
        self.workspace = workspace.resolve()
        self.container_id = container_id
        self.sandbox_image = sandbox_image
        self._local_executor = ToolExecutor(workspace)

    def execute_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        in_sandbox: bool = True,
    ) -> str:
        """Execute a tool, optionally inside the sandbox.

        Args:
            tool_name: Name of the tool to execute.
            args: Tool arguments.
            in_sandbox: Whether to run in the sandbox container.

        Returns:
            Tool output.

        Raises:
            SandboxExecutionError: If sandbox execution fails.
        """
        # Validate arguments first
        validated_args = validate_tool_args(tool_name, args)

        if not in_sandbox:
            # Fall back to local execution (for testing)
            return self._execute_local(tool_name, validated_args)

        # Execute in sandbox
        return self._execute_in_sandbox(tool_name, validated_args)

    def _execute_local(self, tool_name: str, args: dict[str, Any]) -> str:
        """Execute a tool locally (for testing without Docker)."""
        try:
            method = getattr(self._local_executor, tool_name, None)
            if method is None:
                return f"Error: Unknown tool '{tool_name}'"
            return method(args)
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error executing {tool_name}: {e}"

    def _execute_in_sandbox(self, tool_name: str, args: dict[str, Any]) -> str:
        """Execute a tool inside the Docker sandbox."""
        # For file operations, we execute Python code in the container
        code = self._build_tool_code(tool_name, args)

        try:
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    self.container_id,
                    "python",
                    "-c",
                    code,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                stderr = result.stderr.strip()
                if stderr:
                    return f"Error: {stderr}"
                return f"Error: Tool execution failed with code {result.returncode}"

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            return "Error: Tool execution timed out (60s limit)"
        except FileNotFoundError:
            raise SandboxExecutionError("Docker not found. Install Docker to run tools in sandbox.")
        except Exception as e:
            return f"Error: {e}"

    def _build_tool_code(self, tool_name: str, args: dict[str, Any]) -> str:
        """Build Python code to execute a tool inside the sandbox.

        Args:
            tool_name: Name of the tool.
            args: Tool arguments.

        Returns:
            Python code string.
        """
        args_json = json.dumps(args)

        code_templates = {
            "list_files": f"""
import os, json
args = json.loads('{args_json}')
path = args.get('path', '.') or '.'
recursive = args.get('recursive', False)
base = '/workspace'
target = os.path.join(base, path) if path else base
if not os.path.exists(target):
    print(f"Error: Path does not exist: {{target}}")
elif not os.path.isdir(target):
    print(f"Error: Not a directory: {{target}}")
else:
    files = []
    if recursive:
        for root, dirs, fnames in os.walk(target):
            for f in fnames:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, base)
                files.append(rel)
    else:
        for item in sorted(os.listdir(target)):
            full = os.path.join(target, item)
            rel = os.path.relpath(full, base)
            files.append(rel + '/' if os.path.isdir(full) else rel)
    print('\\n'.join(sorted(files)) if files else 'No files found.')
""",
            "read_file": f"""
import json
args = json.loads('{args_json}')
path = args.get('path', '')
full = '/workspace/' + path if not path.startswith('/') else path
try:
    with open(full, 'r') as f:
        content = f.read(100000)
    print(content)
except FileNotFoundError:
    print(f"Error: File not found: {{full}}")
except Exception as e:
    print(f"Error: {{e}}")
""",
            "write_file": f"""
import json, os
args = json.loads('{args_json}')
path = args.get('path', '')
content = args.get('content', '')
full = '/workspace/' + path if not path.startswith('/') else path
os.makedirs(os.path.dirname(full) or '.', exist_ok=True)
try:
    with open(full, 'w') as f:
        f.write(content)
    print(f"Successfully wrote {{len(content)}} characters to {{path}}")
except Exception as e:
    print(f"Error: {{e}}")
""",
            "search_code": f"""
import json, re, os, glob
args = json.loads('{args_json}')
pattern = args.get('pattern', '')
search_dir = args.get('path', '.') or '.'
file_type = args.get('file_type', '*.py')
base = '/workspace'
target = os.path.join(base, search_dir) if search_dir else base
matches = []
for fpath in glob.glob(os.path.join(target, '**', file_type), recursive=True):
    try:
        with open(fpath, 'r') as f:
            for i, line in enumerate(f, 1):
                if re.search(pattern, line):
                    rel = os.path.relpath(fpath, base)
                    matches.append(f"{{rel}}:{{i}}: {{line.strip()}}")
    except:
        pass
if matches:
    print('\\n'.join(matches[:100]))
else:
    print(f"No matches found for pattern: {{pattern}}")
""",
            "run_public_tests": f"""
import json, subprocess, sys
args = json.loads('{args_json}')
test_path = args.get('test_path', 'tests/test_public.py')
full = '/workspace/' + test_path
if not __import__('os').path.exists(full):
    print(f"Error: Test file not found: {{test_path}}")
else:
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', full, '-v', '--tb=short'],
        cwd='/workspace', capture_output=True, text=True, timeout=60
    )
    out = result.stdout
    if result.stderr:
        out += result.stderr
    print(out[:100000])
""",
            "inspect_git_diff": """
import subprocess
result = subprocess.run(
    ['git', 'diff'],
    cwd='/workspace', capture_output=True, text=True, timeout=30
)
if result.stdout.strip():
    print(result.stdout[:100000])
else:
    print("No changes detected.")
""",
            "finish_task": f"""
import json
args = json.loads('{args_json}')
belief = args.get('belief', 'Task completed')
print(f"Task finished. Agent belief: {{belief}}")
""",
        }

        return code_templates.get(tool_name, f"print('Error: Unknown tool {tool_name}')")

    def is_docker_available(self) -> bool:
        """Check if Docker is available.

        Returns:
            True if Docker can be executed.
        """
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
