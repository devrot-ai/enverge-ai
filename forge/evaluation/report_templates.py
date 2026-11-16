"""Report templates for different audiences.

Pre-built report formats: research_paper, executive_summary, technical_deep_dive.
Uses existing evaluation data as input and outputs Markdown.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class ReportTemplate:
    """Generate reports in different formats for different audiences."""

    # Available template names
    TEMPLATES = ["research_paper", "executive_summary", "technical_deep_dive"]

    @classmethod
    def generate(cls, template_name: str, data: Dict[str, Any]) -> str:
        """Generate a report using the specified template.

        Args:
            template_name: One of 'research_paper', 'executive_summary', 'technical_deep_dive'.
            data: Dict with keys:
                - run_results: list of run result dicts
                - task_specs: list of task spec dicts (optional)
                - agent_type: str (optional)
                - title: str (optional)

        Returns:
            Markdown-formatted report string.

        Raises:
            ValueError: If template_name is not recognized.
        """
        if template_name not in cls.TEMPLATES:
            raise ValueError(
                f"Unknown template: {template_name}. "
                f"Available: {', '.join(cls.TEMPLATES)}"
            )

        if template_name == "research_paper":
            return cls._research_paper(data)
        elif template_name == "executive_summary":
            return cls._executive_summary(data)
        else:
            return cls._technical_deep_dive(data)

    @staticmethod
    def _research_paper(data: Dict[str, Any]) -> str:
        """Generate a research paper-style report with methodology and results."""
        results = data.get("run_results", [])
        title = data.get("title", "ForgeLab Experiment Report")
        agent_type = data.get("agent_type", "unknown")

        total = len(results)
        passed = sum(1 for r in results if r.get("passed"))
        pass_rate = passed / total if total > 0 else 0.0

        # Group by template
        by_template: Dict[str, Dict[str, int]] = {}
        for r in results:
            tmpl = r.get("template", "unknown")
            if tmpl not in by_template:
                by_template[tmpl] = {"total": 0, "passed": 0}
            by_template[tmpl]["total"] += 1
            if r.get("passed"):
                by_template[tmpl]["passed"] += 1

        lines = [
            f"# {title}",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d')}",
            f"**Agent:** {agent_type}",
            "",
            "## Abstract",
            "",
            f"This report presents the results of running {agent_type} on {total} tasks "
            f"across {len(by_template)} templates. The overall pass rate was "
            f"{pass_rate:.1%} ({passed}/{total}).",
            "",
            "## Methodology",
            "",
            "Tasks were generated from ForgeLab templates with injected mutations. "
            f"The {agent_type} agent was given each task and its solution was verified "
            "using public and hidden test suites.",
            "",
            "## Results",
            "",
            f"**Overall pass rate:** {pass_rate:.1%} ({passed}/{total})",
            "",
            "### Pass Rate by Template",
            "",
            "| Template | Passed | Total | Rate |",
            "|----------|--------|-------|------|",
        ]

        for tmpl, stats in sorted(by_template.items()):
            rate = stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0
            lines.append(
                f"| {tmpl} | {stats['passed']} | {stats['total']} | {rate:.1%} |"
            )

        lines.append("")
        lines.append("## Conclusion")
        lines.append("")
        if pass_rate > 0.7:
            lines.append(f"The {agent_type} agent demonstrated strong performance.")
        elif pass_rate > 0.4:
            lines.append(
                f"The {agent_type} agent showed moderate performance with room for improvement."
            )
        else:
            lines.append(
                f"The {agent_type} agent struggled with the task set, "
                "suggesting the need for further training or different strategies."
            )

        return "\n".join(lines)

    @staticmethod
    def _executive_summary(data: Dict[str, Any]) -> str:
        """Generate a high-level executive summary."""
        results = data.get("run_results", [])
        title = data.get("title", "ForgeLab Executive Summary")
        agent_type = data.get("agent_type", "unknown")

        total = len(results)
        passed = sum(1 for r in results if r.get("passed"))
        pass_rate = passed / total if total > 0 else 0.0

        # Average duration
        durations = [r.get("duration_seconds", 0) for r in results]
        avg_duration = sum(durations) / len(durations) if durations else 0

        lines = [
            f"# {title}",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "## Key Findings",
            "",
            f"- **Agent:** {agent_type}",
            f"- **Tasks evaluated:** {total}",
            f"- **Pass rate:** {pass_rate:.1%}",
            f"- **Average task duration:** {avg_duration:.1f}s",
            "",
            "## Recommendations",
            "",
        ]

        if pass_rate > 0.7:
            lines.append(
                "- The agent is performing well. Consider expanding the task set "
                "to more difficult challenges."
            )
        elif pass_rate > 0.4:
            lines.append(
                "- The agent shows promise but needs improvement. Focus on the "
                "failure categories with the highest occurrence."
            )
        else:
            lines.append(
                "- The agent requires significant improvement. Consider reviewing "
                "the agent's tool usage patterns and failure modes."
            )

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _technical_deep_dive(data: Dict[str, Any]) -> str:
        """Generate a detailed technical report with full trajectory analysis."""
        results = data.get("run_results", [])
        title = data.get("title", "ForgeLab Technical Deep Dive")
        agent_type = data.get("agent_type", "unknown")

        lines = [
            f"# {title}",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d')}",
            f"**Agent:** {agent_type}",
            "",
            "## Summary Statistics",
            "",
        ]

        total = len(results)
        passed = sum(1 for r in results if r.get("passed"))
        pass_rate = passed / total if total > 0 else 0.0

        # Failure category breakdown
        failure_cats: Dict[str, int] = {}
        for r in results:
            if not r.get("passed"):
                cat = r.get("failure_category", "unknown")
                failure_cats[cat] = failure_cats.get(cat, 0) + 1

        lines.append(f"- Total runs: {total}")
        lines.append(f"- Passed: {passed} ({pass_rate:.1%})")
        lines.append(f"- Failed: {total - passed} ({(1 - pass_rate):.1%})")
        lines.append("")

        if failure_cats:
            lines.append("## Failure Category Breakdown")
            lines.append("")
            lines.append("| Category | Count | Percentage |")
            lines.append("|----------|-------|------------|")
            for cat, count in sorted(failure_cats.items(), key=lambda x: x[1], reverse=True):
                pct = count / total * 100
                lines.append(f"| {cat} | {count} | {pct:.1f}% |")
            lines.append("")

        # Per-task details
        lines.append("## Per-Task Results")
        lines.append("")
        lines.append("| Task ID | Template | Passed | Duration (s) | Failure Category |")
        lines.append("|---------|----------|--------|--------------|------------------|")
        for r in results:
            tid = r.get("task_id", "unknown")
            tmpl = r.get("template", "unknown")
            p = "✓" if r.get("passed") else "✗"
            dur = r.get("duration_seconds", 0)
            cat = r.get("failure_category", "-") if not r.get("passed") else "-"
            lines.append(f"| {tid} | {tmpl} | {p} | {dur:.1f} | {cat} |")
        lines.append("")

        # Trajectory analysis
        lines.append("## Trajectory Analysis")
        lines.append("")
        total_steps = 0
        for r in results:
            traj = r.get("trajectory", [])
            if isinstance(traj, list):
                total_steps += len(traj)
        avg_steps = total_steps / total if total > 0 else 0
        lines.append(f"- Total trajectory steps: {total_steps}")
        lines.append(f"- Average steps per run: {avg_steps:.1f}")
        lines.append("")

        return "\n".join(lines)
