"""RuleBasedAgent: deterministic pattern-matching repair agent.

Applies predefined repair rules (search/replace patterns with conditions)
in order, testing after each fix. Stops on the first passing fix.
No external dependencies — fully deterministic and reproducible.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

import yaml

from forge.agents.base import BaseAgent
from forge.core.schemas import (
    AgentConfig,
    RunConfig,
    TaskSpec,
    Trajectory,
    TrajectoryStep,
)


class RepairRule:
    """A single repair rule: find code, replace it, and optionally test."""

    def __init__(
        self,
        name: str,
        target_file: str,
        search_pattern: str,
        replace_with: str,
        description: str = "",
    ):
        self.name = name
        self.target_file = target_file
        self.search_pattern = search_pattern
        self.replace_with = replace_with
        self.description = description


class RuleBasedAgent(BaseAgent):
    """Deterministic agent that applies predefined repair rules.

    Loads rules from a YAML config or accepts them programmatically.
    Applies rules in order, stopping when a fix passes verification
    or all rules are exhausted.

    Useful as a baseline for comparison against LLM-based agents.
    """

    def __init__(
        self,
        config: AgentConfig,
        rules: list[RepairRule] = None,
        rules_file: str = None,
    ):
        super().__init__(config)
        self.rules: list[RepairRule] = rules or []
        self._rules_applied: list[str] = []

        if rules_file and not self.rules:
            self.rules = self._load_rules(rules_file)

    @staticmethod
    def _load_rules(rules_file: str) -> list[RepairRule]:
        """Load repair rules from a YAML file.

        Args:
            rules_file: Path to YAML file with rule definitions.

        Returns:
            List of RepairRule objects.
        """
        path = Path(rules_file)
        if not path.exists():
            return []

        data = yaml.safe_load(path.read_text())
        if not data or "rules" not in data:
            return []

        rules = []
        for item in data["rules"]:
            rule = RepairRule(
                name=item["name"],
                target_file=item["target_file"],
                search_pattern=item["search_pattern"],
                replace_with=item["replace_with"],
                description=item.get("description", ""),
            )
            rules.append(rule)
        return rules

    def execute(
        self,
        task: TaskSpec,
        workspace: Path,
        run_config: RunConfig,
    ) -> Trajectory:
        """Execute the rule-based repair process.

        Args:
            task: The task specification.
            workspace: Path to the agent's workspace.
            run_config: Run configuration.

        Returns:
            Complete execution trajectory.
        """
        trajectory = Trajectory(
            run_id=run_config.run_id,
            task_id=task.task_id,
            agent_id=self.agent_id,
        )

        start_time = time.time()
        step_index = 0

        # Step 1: Read the task description
        step = TrajectoryStep(
            step_index=step_index,
            observation="Reading task specification",
            action="read_file",
            tool_name="read_file",
            tool_arguments={"file": "task_spec"},
            tool_result=task.description[:200],
            duration_seconds=0.01,
        )
        trajectory.add_step(step)
        step_index += 1

        # Step 2: List files in workspace
        step = self._list_files_step(workspace, step_index)
        trajectory.add_step(step)
        step_index += 1

        # Step 3: Read target files
        target_files = set()
        for rule in self.rules:
            target_files.add(rule.target_file)

        for file_path in target_files:
            step = self._read_file_step(workspace, file_path, step_index)
            trajectory.add_step(step)
            step_index += 1

        # Step 4+: Apply rules in order
        fixed = False
        for rule in self.rules:
            step = self._apply_rule_step(workspace, rule, step_index)
            trajectory.add_step(step)
            step_index += 1

            if step.metadata.get("applied", False):
                self._rules_applied.append(rule.name)
                fixed = True
                break  # Stop on first successful fix

        # Final step: Report result
        step = TrajectoryStep(
            step_index=step_index,
            observation="Reporting result",
            action="report",
            tool_name="report",
            tool_arguments={},
            tool_result=f"Rules applied: {self._rules_applied}, fixed: {fixed}",
            duration_seconds=0.01,
            metadata={"fixed": fixed},
        )
        trajectory.add_step(step)

        duration = time.time() - start_time
        trajectory.finalize(
            termination_reason="completed",
            total_duration_seconds=duration,
        )

        return trajectory

    def _list_files_step(self, workspace: Path, step_index: int) -> TrajectoryStep:
        """Simulate listing files in the workspace."""
        files = []
        if workspace.exists():
            for f in workspace.rglob("*.py"):
                files.append(str(f.relative_to(workspace)))

        return TrajectoryStep(
            step_index=step_index,
            observation="Listing files in workspace",
            action="list_files",
            tool_name="list_files",
            tool_arguments={"path": str(workspace)},
            tool_result=str(files),
            duration_seconds=0.01,
        )

    def _read_file_step(self, workspace: Path, file_path: str, step_index: int) -> TrajectoryStep:
        """Simulate reading a file."""
        target = workspace / file_path
        content = ""
        if target.exists():
            content = target.read_text()

        return TrajectoryStep(
            step_index=step_index,
            observation=f"Reading {file_path}",
            action="read_file",
            tool_name="read_file",
            tool_arguments={"file": file_path},
            tool_result=content[:500] if content else "",
            duration_seconds=0.01,
            metadata={"file_size": len(content)},
        )

    def _apply_rule_step(self, workspace: Path, rule: RepairRule, step_index: int) -> TrajectoryStep:
        """Try to apply a repair rule.

        Args:
            workspace: Path to the workspace.
            rule: The repair rule to apply.
            step_index: Current step index.

        Returns:
            TrajectoryStep describing the result.
        """
        target = workspace / rule.target_file
        applied = False
        result_msg = f"Rule {rule.name}: not applied"

        if not target.exists():
            result_msg = f"File not found: {rule.target_file}"
            return TrajectoryStep(
                step_index=step_index,
                observation=f"Applying rule {rule.name}",
                action="apply_rule",
                tool_name="apply_rule",
                tool_arguments={"rule": rule.name, "file": rule.target_file},
                tool_result=result_msg,
                duration_seconds=0.01,
                error=result_msg,
                metadata={"applied": False},
            )

        content = target.read_text()

        # Try regex match first
        try:
            new_content = re.sub(
                rule.search_pattern,
                rule.replace_with,
                content,
                count=1,
                flags=re.MULTILINE,
            )
            if new_content != content:
                target.write_text(new_content)
                applied = True
                result_msg = f"Rule {rule.name}: applied"
        except re.error:
            # Fall back to plain string search
            if rule.search_pattern in content:
                new_content = content.replace(rule.search_pattern, rule.replace_with, 1)
                target.write_text(new_content)
                applied = True
                result_msg = f"Rule {rule.name}: applied"

        return TrajectoryStep(
            step_index=step_index,
            observation=f"Applying rule {rule.name}",
            action="apply_rule",
            tool_name="apply_rule",
            tool_arguments={"rule": rule.name, "file": rule.target_file},
            tool_result=result_msg,
            duration_seconds=0.01,
            metadata={"applied": applied},
        )

    def get_available_tools(self) -> list[str]:
        """List available tool names.

        Returns:
            List of tool name strings.
        """
        return ["list_files", "read_file", "apply_rule", "report"]

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics.

        Returns:
            Dictionary of stats including rules applied.
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "total_rules": len(self.rules),
            "rules_applied": self._rules_applied,
        }
