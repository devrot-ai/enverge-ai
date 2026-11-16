"""ForgeLab Streamlit Dashboard.

A research-lab control panel for monitoring and managing ForgeLab operations.
Connects to the SQLite database to display real metrics from worlds, tasks,
runs, failure diagnoses, and curriculum state.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

from forge.db.models import (
    CurriculumRecord,
    ExperimentRecord,
    RunRecord,
    TaskRecord,
    WorldRecord,
    get_session,
    init_db,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ForgeLab",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = os.environ.get("FORGELAB_DB", "forgelab.db")
BASE_DIR = Path(os.environ.get("FORGELAB_BASE_DIR", str(Path.cwd())))
DB_FULL_PATH = str(BASE_DIR / DB_PATH)

# Ensure DB exists
if not Path(DB_FULL_PATH).exists():
    init_db(DB_FULL_PATH)


def get_db():
    """Get a database session."""
    return get_session(DB_FULL_PATH)


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

page = st.sidebar.selectbox(
    "Navigate",
    ["Overview", "Worlds", "Tasks", "Runs", "Failure Analysis", "Curriculum", "Experiments"],
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Database:** `{DB_PATH}`")
st.sidebar.markdown(f"**Base dir:** `{BASE_DIR}`")

# ---------------------------------------------------------------------------
# Overview Page
# ---------------------------------------------------------------------------


def render_overview():
    st.title("ForgeLab — Overview")
    st.caption("Research-grade adaptive environment factory for autonomous agents")

    session = get_db()
    try:
        total_worlds = session.query(WorldRecord).count()
        total_tasks = session.query(TaskRecord).count()
        validated_tasks = session.query(TaskRecord).filter_by(validated=1).count()
        total_runs = session.query(RunRecord).count()
        completed_runs = session.query(RunRecord).filter_by(status="completed").count()
        passed_runs = session.query(RunRecord).filter_by(passed=1).count()
        failed_runs = session.query(RunRecord).filter_by(status="failed").count()
        running_runs = session.query(RunRecord).filter_by(status="running").count()
    finally:
        session.close()

    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Worlds", total_worlds)
    col2.metric("Tasks", f"{validated_tasks}/{total_tasks}", help="Validated / Total")
    col3.metric("Runs", total_runs)
    col4.metric("Passed", passed_runs)
    col5.metric("Running", running_runs)

    st.markdown("---")

    # Success rate with chart
    if total_runs > 0:
        success_rate = passed_runs / total_runs
        st.subheader(f"Success Rate: {success_rate:.1%}")
        st.progress(success_rate)

        # Pass/Fail bar chart
        try:
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_trace(go.Bar(name="Passed", x=["Runs"], y=[passed_runs], marker_color="#2ecc71"))
            fig.add_trace(go.Bar(name="Failed", x=["Runs"], y=[total_runs - passed_runs], marker_color="#e74c3c"))
            fig.update_layout(barmode="group", height=250, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            pass

    # Failure breakdown
    st.subheader("Failure Attribution")
    session = get_db()
    try:
        diagnoses: list[dict[str, Any]] = []
        for run in session.query(RunRecord).filter(RunRecord.diagnosis_json.isnot(None)).all():
            if run.diagnosis_json:
                try:
                    diag = json.loads(run.diagnosis_json)
                    diag["run_id"] = run.run_id
                    diagnoses.append(diag)
                except json.JSONDecodeError:
                    pass
    finally:
        session.close()

    if diagnoses:
        # Failure type pie chart
        try:
            from collections import Counter

            import plotly.graph_objects as go

            categories = [d.get("category", "unknown") for d in diagnoses]
            counts = Counter(categories)
            colors = {
                "agent_failure": "#e74c3c",
                "environment_failure": "#e67e22",
                "task_failure": "#f39c12",
                "validation_failure": "#9b59b6",
                "sandbox_failure": "#3498db",
                "unknown": "#95a5a6",
            }
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=list(counts.keys()),
                        values=list(counts.values()),
                        marker_colors=[colors.get(k, "#95a5a6") for k in counts.keys()],
                    )
                ]
            )
            fig.update_layout(height=350, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            pass

        # Group by category
        from collections import defaultdict

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for d in diagnoses:
            grouped[d.get("category", "unknown")].append(d)

        for cat, details in sorted(grouped.items()):
            with st.expander(f"{cat} ({len(details)} runs)"):
                for detail in details[:5]:
                    st.write(f"- **{detail.get('run_id', 'unknown')}** (confidence: {detail.get('confidence', 0):.2f})")
                    for ev in detail.get("evidence", [])[:2]:
                        st.write(f"  - {ev}")
    else:
        st.info("No failure diagnoses yet. Run some agents to collect data.")

    # Recent runs
    st.subheader("Recent Runs")
    session = get_db()
    try:
        recent = session.query(RunRecord).order_by(RunRecord.started_at.desc()).limit(10).all()
        if recent:
            import pandas as pd

            rows = []
            for r in recent:
                rows.append(
                    {
                        "Run ID": r.run_id,
                        "Task": r.task_id,
                        "Agent": r.agent_id,
                        "Status": r.status,
                        "Passed": "✓" if r.passed else "✗",
                        "Duration": f"{r.duration_seconds:.1f}s" if r.duration_seconds else "—",
                    }
                )
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No runs yet. Generate a world, create a task, and run an agent.")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Worlds Page
# ---------------------------------------------------------------------------


def render_worlds():
    st.title("Environment Factory")

    session = get_db()
    try:
        worlds = session.query(WorldRecord).order_by(WorldRecord.created_at.desc()).all()
    finally:
        session.close()

    if worlds:
        import pandas as pd

        rows = []
        for w in worlds:
            rows.append(
                {
                    "World ID": w.world_id,
                    "Template": w.template_name,
                    "Mutation": w.mutation_id,
                    "Seed": w.seed or "—",
                    "Created": w.created_at.strftime("%Y-%m-%d %H:%M") if w.created_at else "—",
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No worlds generated yet. Use the CLI: `forgelab world generate`")


# ---------------------------------------------------------------------------
# Tasks Page
# ---------------------------------------------------------------------------


def render_tasks():
    st.title("Task Laboratory")

    validated_only = st.sidebar.checkbox("Show validated only", value=False)

    session = get_db()
    try:
        query = session.query(TaskRecord)
        if validated_only:
            query = query.filter_by(validated=1)
        tasks = query.order_by(TaskRecord.created_at.desc()).all()
    finally:
        session.close()

    if tasks:
        import pandas as pd

        rows = []
        for t in tasks:
            rows.append(
                {
                    "Task ID": t.task_id,
                    "World": t.world_id,
                    "Category": t.category,
                    "Difficulty": t.difficulty_level,
                    "Validated": "✓" if t.validated else "✗",
                    "Description": (
                        (t.description[:80] + "...") if len(t.description or "") > 80 else (t.description or "")
                    ),
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No tasks generated yet.")


# ---------------------------------------------------------------------------
# Runs Page
# ---------------------------------------------------------------------------


def render_runs():
    st.title("Agent Runs")

    # Auto-refresh for running agents
    session = get_db()
    try:
        running_count = session.query(RunRecord).filter_by(status="running").count()
    finally:
        session.close()

    if running_count > 0:
        st.info(f"🔄 {running_count} run(s) currently executing — auto-refreshing every 5 seconds...")
        st.empty().rerun()

    # --- Filters ---
    session = get_db()
    try:
        all_runs = session.query(RunRecord).order_by(RunRecord.started_at.desc()).limit(200).all()
    finally:
        session.close()

    if not all_runs:
        st.info("No runs yet.")
        return

    # Build filter options from data
    agent_types = sorted({r.agent_id for r in all_runs if r.agent_id})
    statuses = sorted({r.status for r in all_runs if r.status})
    templates = sorted({r.task_id for r in all_runs if r.task_id})  # task_id as proxy

    st.subheader("Filters")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        filter_agent = st.selectbox("Agent Type", ["All"] + agent_types, key="filter_agent")
    with col_f2:
        filter_status = st.selectbox("Status", ["All"] + statuses, key="filter_status")
    with col_f3:
        filter_passed = st.selectbox("Passed", ["All", "Passed", "Failed"], key="filter_passed")
    with col_f4:
        filter_search = st.text_input("Search (task/run ID)", key="filter_search")

    # Apply filters
    runs = all_runs
    if filter_agent != "All":
        runs = [r for r in runs if r.agent_id == filter_agent]
    if filter_status != "All":
        runs = [r for r in runs if r.status == filter_status]
    if filter_passed == "Passed":
        runs = [r for r in runs if r.passed]
    elif filter_passed == "Failed":
        runs = [r for r in runs if not r.passed]
    if filter_search:
        search_lower = filter_search.lower()
        runs = [
            r for r in runs
            if search_lower in str(r.task_id or "").lower()
            or search_lower in str(r.run_id or "").lower()
        ]

    if not runs:
        st.info("No runs match the current filters.")
        return

    # Summary
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Runs", len(runs))
    col2.metric("Passed", sum(1 for r in runs if r.passed))
    col3.metric("Failed", sum(1 for r in runs if not r.passed and r.status == "failed"))

    # Export button
    if st.button("Export as JSON"):
        from forge.api.export import export_runs as do_export

        data = do_export(f"sqlite:///{DB_FULL_PATH}", format="json")
        st.download_button("Download JSON", data, file_name="forgelab_runs.json", mime="application/json")
    if st.button("Export as CSV"):
        from forge.api.export import export_runs as do_export

        data = do_export(f"sqlite:///{DB_FULL_PATH}", format="csv")
        st.download_button("Download CSV", data, file_name="forgelab_runs.csv", mime="text/csv")

    # Run list
    st.subheader("Run Details")
    for run in runs[:20]:
        with st.expander(
            f"`{run.run_id}` — {run.status} | Agent: {run.agent_id} | " f"{'✓ Passed' if run.passed else '✗ Failed'}"
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Task:** `{run.task_id}`")
                st.write(f"**Agent:** `{run.agent_id}`")
                st.write(f"**Status:** {run.status}")
                st.write(f"**Duration:** {run.duration_seconds:.1f}s")
                st.write(f"**Steps:** {run.step_count}")
            with col2:
                st.write(f"**Started:** {run.started_at}")
                st.write(f"**Finished:** {run.finished_at}")
                if run.error:
                    st.error(run.error[:500])

            # Trajectory visualization
            if run.trajectory_json:
                try:
                    traj = json.loads(run.trajectory_json)
                    steps = traj.get("steps", [])
                    st.write(f"**Trajectory steps:** {len(steps)}")

                    if steps:
                        # Trajectory timeline chart
                        if st.button(f"View trajectory timeline for {run.run_id}", key=f"traj_{run.run_id}"):
                            traj_rows = []
                            for step in steps:
                                tool = step.get("tool_name", "unknown")
                                duration = step.get("duration_seconds", 0)
                                error = step.get("error", "")
                                status = "error" if error else ("success" if duration > 0 else "pending")
                                traj_rows.append(
                                    {
                                        "Step": step.get("step_index", 0),
                                        "Tool": tool,
                                        "Duration (s)": f"{duration:.3f}",
                                        "Status": status,
                                    }
                                )
                            import pandas as pd

                            traj_df = pd.DataFrame(traj_rows)
                            st.dataframe(traj_df, use_container_width=True, hide_index=True)

                            # Timeline bar chart
                            try:
                                import plotly.graph_objects as go

                                fig = go.Figure()
                                colors = {"success": "#2ecc71", "error": "#e74c3c", "pending": "#95a5a6"}
                                step_indices = [s.get("step_index", 0) for s in steps]
                                durations = [s.get("duration_seconds", 0) for s in steps]
                                statuses = ["error" if s.get("error") else "success" for s in steps]
                                colors_list = [colors.get(s, "#3498db") for s in statuses]
                                fig.add_trace(
                                    go.Bar(
                                        x=step_indices,
                                        y=durations,
                                        marker_color=colors_list,
                                        name="Duration",
                                    )
                                )
                                fig.update_layout(
                                    height=250,
                                    xaxis_title="Step",
                                    yaxis_title="Duration (s)",
                                    showlegend=False,
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            except ImportError:
                                pass

                            # Detailed step view
                            for step in steps[:10]:
                                with st.expander(
                                    f"Step {step.get('step_index', '?')}: "
                                    f"{step.get('tool_name', 'unknown')} "
                                    f"({step.get('duration_seconds', 0):.3f}s)"
                                ):
                                    st.write(f"**Tool:** {step.get('tool_name', 'N/A')}")
                                    if step.get("tool_arguments"):
                                        st.write("**Arguments:**")
                                        st.json(step["tool_arguments"])
                                    if step.get("tool_result"):
                                        result = step["tool_result"]
                                        if len(str(result)) > 500:
                                            st.write(f"**Result:** {str(result)[:500]}...")
                                        else:
                                            st.write(f"**Result:** {result}")
                                    if step.get("error"):
                                        st.error(step["error"])
                except json.JSONDecodeError:
                    pass

            # Verification
            if run.verification_json:
                try:
                    verif = json.loads(run.verification_json)
                    st.write(f"**Verification passed:** {verif.get('passed', False)}")
                except json.JSONDecodeError:
                    pass

            # Diagnosis
            if run.diagnosis_json:
                try:
                    diag = json.loads(run.diagnosis_json)
                    st.write(f"**Diagnosis:** {diag.get('primary_category', 'unknown')}")
                    st.write(f"**Confidence:** {diag.get('confidence', 0):.2f}")
                    if diag.get("supporting_evidence"):
                        for ev in diag["supporting_evidence"]:
                            st.write(f"  - {ev}")
                except json.JSONDecodeError:
                    pass

            # Code diff viewer
            if run.trajectory_json:
                try:
                    traj = json.loads(run.trajectory_json)
                    steps = traj.get("steps", [])
                    # Extract file changes from trajectory
                    file_states = {}
                    for step in steps:
                        tool = step.get("tool_name", "")
                        args = step.get("tool_arguments", {})
                        result = step.get("tool_result", "")
                        if tool == "read_file" and args.get("file_path"):
                            fname = args["file_path"]
                            if fname not in file_states:
                                file_states[fname] = {}
                            if "original" not in file_states[fname] and isinstance(result, str):
                                file_states[fname]["original"] = result
                        elif tool == "write_file" and args.get("file_path"):
                            fname = args["file_path"]
                            content = args.get("content", "")
                            if fname not in file_states:
                                file_states[fname] = {}
                            file_states[fname]["modified"] = content

                    # Show diffs for changed files
                    changed_files = {
                        fname: states
                        for fname, states in file_states.items()
                        if "original" in states and "modified" in states and states["original"] != states["modified"]
                    }

                    if changed_files:
                        st.write(f"**Files changed:** {len(changed_files)}")
                        for fname, states in list(changed_files.items())[:5]:
                            with st.expander(f"`{fname}`"):
                                orig_lines = states["original"].splitlines()
                                mod_lines = states["modified"].splitlines()

                                col_a, col_b = st.columns(2)
                                with col_a:
                                    st.code(states["original"], language="python", line_numbers=True)
                                with col_b:
                                    st.code(states["modified"], language="python", line_numbers=True)
                except json.JSONDecodeError:
                    pass

            # Live status indicator for running runs
            if run.status == "running":
                st.info(f"🔄 **Running** — Step {run.step_count} | Duration: {run.duration_seconds:.1f}s")
                st.caption("This run is currently executing. Refresh to see updated progress.")


# ---------------------------------------------------------------------------
# Failure Analysis Page
# ---------------------------------------------------------------------------


def render_failure_analysis():
    st.title("Failure Analysis")
    st.caption(
        "ForgeLab distinguishes between agent failures, environment defects, "
        "invalid tasks, verifier failures, and infrastructure issues."
    )

    session = get_db()
    try:
        runs = session.query(RunRecord).filter(RunRecord.diagnosis_json.isnot(None)).all()
    finally:
        session.close()

    if not runs:
        st.info("No failure diagnoses yet.")
        return

    # Category breakdown
    category_counts: dict[str, int] = {}
    category_details: dict[str, list[dict[str, Any]]] = {}

    for run in runs:
        if run.diagnosis_json:
            try:
                diag = json.loads(run.diagnosis_json)
                cat = diag.get("primary_category", "unknown")
                category_counts[cat] = category_counts.get(cat, 0) + 1
                if cat not in category_details:
                    category_details[cat] = []
                category_details[cat].append(
                    {
                        "run_id": run.run_id,
                        "task_id": run.task_id,
                        "agent_id": run.agent_id,
                        "confidence": diag.get("confidence", 0),
                        "evidence": diag.get("supporting_evidence", []),
                    }
                )
            except json.JSONDecodeError:
                pass

    # Summary table
    import pandas as pd

    st.subheader("Failure Categories")
    df = pd.DataFrame(
        [
            {"Category": cat, "Count": count, "Percentage": f"{count / len(runs):.1%}"}
            for cat, count in sorted(category_counts.items(), key=lambda x: -x[1])
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Detail per category
    for cat, details in category_details.items():
        with st.expander(f"{cat} ({len(details)} runs)"):
            for detail in details[:5]:
                st.write(f"- **{detail['run_id']}** (confidence: {detail['confidence']:.2f})")
                for ev in detail["evidence"][:2]:
                    st.write(f"  - {ev}")


# ---------------------------------------------------------------------------
# Curriculum Page
# ---------------------------------------------------------------------------


def render_curriculum():
    st.title("Adaptive Curriculum")

    session = get_db()
    try:
        records = session.query(CurriculumRecord).order_by(CurriculumRecord.updated_at.desc()).all()
    finally:
        session.close()

    if not records:
        st.info("No curriculum data yet. Runs will update the curriculum automatically.")
        return

    latest = records[0]
    st.subheader("Current State")
    col1, col2, col3 = st.columns(3)
    col1.metric("Strategy", latest.strategy)
    col2.metric("Generation", latest.generation)
    col3.metric("Task Pool", len(latest.task_pool_json) if latest.task_pool_json else 0)

    if latest.capability_scores_json:
        try:
            scores = json.loads(latest.capability_scores_json)
            st.subheader("Capability Scores")
            import pandas as pd

            df = pd.DataFrame(
                [
                    {"Capability": cap, "Score": f"{score:.3f}"}
                    for cap, score in sorted(scores.items(), key=lambda x: -x[1])
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        except json.JSONDecodeError:
            pass

    # History
    st.subheader("Curriculum History")
    if len(records) > 1:
        import pandas as pd

        rows = []
        for rec in records[:20]:
            rows.append(
                {
                    "Generation": rec.generation,
                    "Strategy": rec.strategy,
                    "Updated": rec.updated_at.strftime("%Y-%m-%d %H:%M") if rec.updated_at else "—",
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Experiments Page
# ---------------------------------------------------------------------------


def render_experiments():
    st.title("Experiments")

    session = get_db()
    try:
        experiments = session.query(ExperimentRecord).order_by(ExperimentRecord.started_at.desc()).all()
    finally:
        session.close()

    if experiments:
        import pandas as pd

        rows = []
        for exp in experiments:
            rows.append(
                {
                    "Experiment ID": exp.experiment_id,
                    "Name": exp.name,
                    "Status": exp.status,
                    "Hypothesis": (
                        (exp.hypothesis[:80] + "...") if len(exp.hypothesis or "") > 80 else (exp.hypothesis or "")
                    ),
                    "Started": exp.started_at.strftime("%Y-%m-%d %H:%M") if exp.started_at else "—",
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No experiments created yet.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


PAGES = {
    "Overview": render_overview,
    "Worlds": render_worlds,
    "Tasks": render_tasks,
    "Runs": render_runs,
    "Failure Analysis": render_failure_analysis,
    "Curriculum": render_curriculum,
    "Experiments": render_experiments,
}

PAGES[page]()
