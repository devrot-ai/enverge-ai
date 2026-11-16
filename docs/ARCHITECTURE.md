# ForgeLab Architecture

## Overview

ForgeLab is an adaptive environment factory for autonomous software engineering agents. It generates broken Python repositories, executes agents attempting repairs, independently verifies results, diagnoses failures, and uses verified outcomes to generate targeted training challenges.

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        ForgeLab Pipeline                        │
├────────────┬────────────┬───────────┬───────────┬───────────────┤
│  World     │  Task      │  Agent    │  Verify   │  Curriculum   │
│  Factory   │  Factory   │  Runner   │  & Diag   │  Engine       │
└─────┬──────┴─────┬──────┴─────┬─────┴─────┬─────┴───────┬──────┘
      │            │            │           │             │
      ▼            ▼            ▼           ▼             ▼
  Generate    Create Task   Execute     Independent   Adaptive
  Broken     Spec &        Agent in    Verification  Task Selection
  Repository  Validate     Sandbox
```

## Module Descriptions

### Core (`forge/core/`)

Shared infrastructure used by all modules.

| File | Responsibility |
|------|----------------|
| `schemas.py` | Pydantic v2 data models: `WorldSpec`, `TaskSpec`, `RunResult`, `Trajectory`, `VerificationResult`, `FailureDiagnosis`, `CurriculumState`, `ExperimentConfig` |
| `config.py` | YAML + environment variable configuration loading |
| `errors.py` | 20+ explicit exception types for all failure modes |
| `events.py` | EventEmitter pipeline for lifecycle events |
| `registry.py` | Pluggable component registry for templates, generators, agents, verifiers |

### World Factory (`forge/world_factory/`)

Generates deterministic, reproducible software environments with injected defects.

| File | Responsibility |
|------|----------------|
| `templates.py` | Repository templates (14 total): `task_manager_api`, `data_pipeline`, `flask_app`, `express_api`, `django_app`, `typescript_api`, `go_service`, `react_app`, `spring_service`, `config_manager`, `browser_automation`, `database_query`, `api_integration`, `dsl` |
| `seeder.py` | Deterministic bug mutations: 37 mutations across 14 templates including pagination, search, null handling, date parsing, session timeout, password hashing, CSRF, CORS, rate limiting, input sanitization, SQL injection, open redirect, XSS, transaction leak, N+1 queries, validation bypass, env override, secret exposure, merge conflict, clickjacking, auth bypass, query optimization, token management, retry logic, lexer/parser, and type coercion |
| `generator.py` | World generation: loads template, applies mutation, initializes git, creates manifest |
| `manifest.py` | World manifest generation and tracking |
| `composite.py` | Composite mutations: multiple bugs per task with conflict detection |
| `cross_template.py` | Cross-template mutation analysis and capability coverage |

**Key property:** Same seed + same blueprint → identical environment. Reference solutions stored separately from agent-accessible workspace.

### Task Factory (`forge/task_factory/`)

Creates structured task specifications from world definitions.

| File | Responsibility |
|------|----------------|
| `generator.py` | Maps worlds to `TaskSpec` with human-readable descriptions, constraints, and verification methods |
| `mutations.py` | Controlled bug mutation definitions with capability categorization |
| `difficulty.py` | Difficulty estimation based on mutation complexity and required capabilities |
| `selection.py` | Task pool management and variant generation |

### Validators (`forge/validators/`)

**The critical quality gate.** No task reaches an agent without passing independent validation.

| File | Responsibility |
|------|----------------|
| `world_validator.py` | Checks: repo exists, files exist, deps install, tests run, defect present, reset works |
| `world_validator.py` (TaskValidator) | Checks: description matches defect, criteria achievable, constraints consistent |
| `world_validator.py` (VerifierValidator) | Positive/negative test cases against known states |
| `world_validator.py` (ReferenceValidator) | Applies reference fix, verifies it passes hidden tests |

**Validation pipeline:**

```
World generated → WorldValidator → TaskValidator → VerifierValidator → ReferenceValidator
     │                │                │                  │                    │
     ▼                ▼                ▼                  ▼                    ▼
  Repo exists?    Description     Verifier detects   Reference fix       Task released
  Defect present? matches defect?  known defects?    passes tests?       to agent
```

### Sandbox (`forge/sandbox/`)

Docker-based isolated execution for running untrusted agent-generated code.

| File | Responsibility |
|------|----------------|
| `manager.py` | High-level sandbox lifecycle: create, execute, cleanup |
| `executor.py` | Command execution inside containers with resource limits |
| `reset.py` | Workspace reset and cleanup |
| `policies.py` | Security policies: non-root user, no network, resource limits, capability dropping |
| `signing.py` | Container image signing: SHA-256 hash-based integrity verification and tamper detection |
| `network.py` | Network policy enforcement: allow_all, restrict_outbound, block_all |
| `image_validation.py` | Container image security checks for Dockerfiles |

**Security principle:** Fail-closed. If Docker is unavailable, display a clear error. Never fall back to host execution.

### Agents (`forge/agents/`)

Pluggable agent interface supporting multiple execution modes.

| File | Responsibility |
|------|----------------|
| `base.py` | Abstract `BaseAgent` interface with `execute()` method |
| `mock_agent.py` | Deterministic mock agent with 4 scenarios: success, partial, failure, no_change |
| `rule_based.py` | Pattern-matching repair agent with configurable YAML rules; applies fixes in order and tests after each |
| `script_agent.py` | External Python script executor; runs custom agent logic with workspace access and timeout enforcement |
| `openai_compatible.py` | OpenAI-compatible API adapter with tool-calling support |
| `adversarial.py` | Adversarial agent wrapper: injects errors during execution to test robustness |
| `tools.py` | Agent tools: `list_files`, `read_file`, `search_code`, `write_file`, `run_public_tests`, `inspect_test_output`, `inspect_git_diff`, `finish_task` |
| `registry.py` | Agent registration and lookup (auto-registers all 4 agent types) |
| `config.py` | Agent configuration from environment variables |

**Agent tools are controlled:** No unrestricted shell access. All filesystem paths checked for traversal. Tool arguments validated against strict schemas.

### Runner (`forge/runner/`)

Orchestrates the complete execution lifecycle.

| File | Responsibility |
|------|----------------|
| `orchestrator.py` | Full lifecycle: create run → load task → init workspace → run agent → verify → diagnose → store → cleanup |
| `trajectory.py` | Trajectory recording: run_id, task_id, agent_id, step_index, observation, action, tool_name, tool_args, tool_result, duration, error |
| `tool_executor.py` | Executes agent tool calls in sandbox |
| `lifecycle.py` | Run state management and interruption handling |
| `multi_agent.py` | Multi-agent comparison runner: side-by-side agent evaluation |
| `parallel.py` | Parallel task execution with ThreadPoolExecutor |
| `queue.py` | Priority-based task queue with pause/resume and JSON persistence |
| `resource_manager.py` | Resource-aware scheduling: CPU/memory monitoring for parallel execution |
| `replay.py` | Session replay: JSON/JSONL trajectory loading and comparison |
| `snapshot.py` | Workspace snapshot: capture and restore workspace states for reproducibility |

### Evaluation (`forge/evaluation/`)

Independent verification of agent outcomes.

| File | Responsibility |
|------|----------------|
| `verifier.py` | Runs public + hidden tests in separate container, never exposes hidden tests to agent |
| `error_injection.py` | Error injection framework: syntax, import, type, attribute, runtime errors for adversarial testing |
| `report.py` | Evaluation report generator: pass rates, failure breakdown, timing, recommendations |
| `metrics.py` | Success rate, pass@k, verifier quality metrics |
| `scoring.py` | Task scoring and evaluation reports |
| `reports.py` | Versioned evaluation reports |
| `fuzzer.py` | Property-based fuzzing: generates edge-case inputs for robustness testing |
| `static_analysis.py` | Flake8/mypy static analysis as optional verification criteria |
| `performance.py` | Test execution time tracking with regression detection |
| `diff_viewer.py` | Code diff viewer: unified diffs of agent workspace changes |
| `publish.py` | Benchmark publication: Markdown/JSON reports with baseline comparison |
| `mutation_coverage.py` | Mutation coverage analysis: identifies which mutations are tested and finds gaps |
| `difficulty_calibration.py` | Difficulty calibration: measures actual vs assigned difficulty with pass-rate-based adjustments |
| `behavior_analysis.py` | Agent behavior analysis: tool call patterns and failure mode clustering per agent |
| `report_templates.py` | Report templates: pre-built formats (research_paper, executive_summary, technical_deep_dive) |

### Diagnosis (`forge/diagnosis/`)

**Core research contribution.** Evidence-based failure attribution.

| File | Responsibility |
|------|----------------|
| `classifier.py` | 6 failure categories with deterministic rules and confidence scoring |
| `rules.py` | Classification rules based on evidence signals |
| `triage.py` | Evidence collection and confidence scoring |
| `report.py` | Diagnosis reports with supporting/contradictory evidence |

**Failure categories:**

| Category | When | Action |
|----------|------|--------|
| `agent_failure` | Valid env, valid task, working verifier, agent didn't solve | Preserve as learning signal |
| `environment_failure` | Dependency/startup/filesystem/runtime failure | Quarantine, repair world |
| `invalid_task` | Ambiguous, impossible, contradictory task | Reject or revise |
| `verifier_failure` | Verifier rejects correct solution or accepts incorrect | Repair verifier |
| `infrastructure_failure` | Timeout, API outage, sandbox crash | Retry or abort |
| `uncertain` | Insufficient evidence | Manual review |

### Curriculum (`forge/curriculum/`)

Adaptive task selection based on verified agent weaknesses.

| File | Responsibility |
|------|----------------|
| `selector.py` | Static, random, and adaptive selection strategies with `CapabilityTracker` |
| `capability_tracker.py` | Per-capability performance tracking (debugging, edge_case_reasoning, testing, etc.) |
| `difficulty.py` | Difficulty estimation and adjustment |
| `updater.py` | Curriculum state updates based on verified outcomes |
| `history.py` | Curriculum decision logging |

### Experiments (`forge/experiments/`)

Experiment management and comparison.

| File | Responsibility |
|------|----------------|
| `manager.py` | Experiment lifecycle, run tracking, metrics computation |
| `config.py` | Experiment configuration |
| `comparison.py` | Cross-experiment result comparison |
| `artifacts.py` | Artifact management |

### Database (`forge/db/`)

Persistent storage with SQLAlchemy + SQLite.

| File | Responsibility |
|------|----------------|
| `models.py` | SQLAlchemy models: `WorldRecord`, `TaskRecord`, `RunRecord`, `CurriculumRecord`, `ExperimentRecord` |

### API (`forge/api/`)

FastAPI REST backend with 26 routes.

Key endpoints: `/health`, `/api/v1/worlds`, `/api/v1/tasks`, `/api/v1/runs`, `/api/v1/curriculum`, `/api/v1/experiments`, `/api/v1/metrics`.

Long-running agent executions handled as background tasks.

### Dashboard (`dashboard/`)

Streamlit engineering control panel with 7 pages: Overview, Worlds, Tasks, Runs, Failure Analysis, Curriculum, Experiments.

### CLI (`forge/cli.py`)

Typer-based CLI with commands: `init`, `doctor`, `world generate/validate`, `task list/validate`, `agent list`, `run execute/inspect`, `curriculum inspect`, `experiment create/list/run/report`, `snapshot capture/restore/list`, `coverage`, `difficulty-calibrate`, `behavior-analyze`, `report-generate`, `serve`.

## Data Flow

```
1. WorldGenerator creates broken repo from template + mutation
2. TaskGenerator creates TaskSpec from WorldSpec
3. Validators independently verify world, task, verifier, reference solution
4. RunOrchestrator creates isolated workspace and executes agent
5. Agent uses controlled tools to inspect, edit, and test code
6. Verifier runs hidden tests in separate container
7. FailureClassifier diagnoses the outcome
8. CurriculumSelector updates capability tracker and selects next task
9. Results persisted to SQLite database
10. Dashboard displays real-time metrics
```

## Design Principles

1. **Validation-first:** No task reaches an agent without independent validation.
2. **Fail-closed security:** Untrusted code never runs on the host.
3. **Evidence-based diagnosis:** Every failure classification includes supporting evidence.
4. **Reproducibility:** Same seed produces same environment.
5. **Pluggable agents:** Swap agents without changing the pipeline.
6. **No fabricated metrics:** All dashboard data from real stored results.
7. **Clear separation:** MockAgent results never mixed with real model results.
