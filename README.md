# ForgeLab

**Adaptive environment factory for autonomous software engineering agents.**

ForgeLab generates broken Python repositories, executes AI agents attempting repairs, independently verifies results, diagnoses failures, and uses verified outcomes to generate progressively harder training challenges.

## Research Question

> Can validation-first environment generation and failure-attribution-aware adaptive curricula improve autonomous coding agents' generalization to unseen tasks, compared with fixed task curricula under equivalent inference budgets?

## What Makes ForgeLab Different

| Existing Research | ForgeLab's Contribution |
|---|---|
| Echoverse generates stateful computer-use worlds | Extensible generator for terminal-based software engineering environments |
| AutoEnvScaling generates environments from agent rollouts | Rigorous environment-quality and failure-attribution layer |
| Self-HPO optimizes agent harness and policy | Experiment with improving task distributions using controlled comparisons |
| Agent Lightning connects agents to RL training | Portable environment and evaluation layer for different agents |

**Core research gap:** Can we reliably distinguish between agent failures, invalid tasks, environment defects, and verifier failures — and use that diagnosis to improve the next training cycle?

## Quick Start

```bash
# Install
cd forgelab
pip install -e .

# Check system
python -m forge.cli doctor

# Run end-to-end demo (no API keys required)
python examples/demo_pipeline.py

# Start API server
python -m uvicorn forge.api.app:app --reload --port 8000

# Start dashboard
streamlit run dashboard/app.py
```

## Architecture

```
forge/
├── core/           # Schemas, config, events, registry
├── world_factory/  # Generates broken Python repos from templates
├── task_factory/   # Creates task specs from worlds
├── validators/     # Independent world/task/verifier validation
├── agents/         # Pluggable agent interface (MockAgent, RuleBasedAgent, ScriptAgent, OpenAI)
├── runner/         # Run orchestrator and trajectory recorder
├── evaluation/     # Independent test verifier
├── diagnosis/      # Failure attribution engine (6 categories)
├── curriculum/     # Adaptive task selection
├── experiments/    # Experiment management and comparison (7 presets)
├── sandbox/        # Docker-based isolated execution
├── api/            # FastAPI REST backend
├── db/             # SQLAlchemy models (SQLite)
└── cli.py          # Typer CLI
```

## Pipeline

```
Generate World -> Validate -> Generate Task -> Validate -> Run Agent ->
Verify Independently -> Diagnose Failure -> Update Curriculum ->
Generate Targeted Tasks -> Repeat
```

## Key Features

- **World Factory**: Deterministic Python repository generation with 14 templates and 37 bug mutations (task_manager_api, data_pipeline, flask_app, express_api, django_app, typescript_api, go_service, react_app, spring_service, config_manager, browser_automation, database_query, api_integration, dsl) covering pagination, search, null handling, date parsing, session timeout, password hashing, CSRF, CORS, rate limiting, input sanitization, SQL injection, open redirect, stack trace exposure, input validation, nil pointer, resource leak, XSS injection, transaction leak, N+1 queries, validation bypass, environment override, secret exposure, merge conflict, reflected XSS, clickjacking, authentication bypass, query optimization, token management, retry logic, lexer/parser, and type coercion
- **Independent Validation**: World, task, and verifier validation before any agent runs
- **Failure Attribution**: 6-category diagnosis (agent/environment/task/verifier/infrastructure/uncertain) with evidence
- **Adaptive Curriculum**: Tracks capability scores, identifies weaknesses, generates targeted tasks
- **MockAgent**: Deterministic agent for testing without API keys
- **RuleBasedAgent**: Pattern-matching repair agent with configurable rules
- **ScriptAgent**: External script executor for custom agent logic
- **OpenAI Agent**: Real LLM tool-calling agent with 8 tools (optional, requires API key)
- **FastAPI Backend**: 26 REST routes for all operations with SQLite persistence
- **Streamlit Dashboard**: 7-page control panel with charts, code diff viewer, and real-time run monitoring
- **Typer CLI**: Full command-line interface for all operations including export and database management
- **Docker Sandbox**: Isolated execution for untrusted agent code (fail-closed security)
- **Static Analysis**: Optional flake8/mypy checks as additional verification criteria
- **Export**: Run data export as JSON/CSV via CLI and dashboard
- **Agent Profiles**: YAML-based configuration profiles (conservative, aggressive, balanced)
- **Performance Checks**: Test execution time tracking with regression detection
- **Held-out Evaluation**: Frozen benchmark task sets for consistent evaluation
- **Code Diff Viewer**: Side-by-side view of agent workspace changes in the dashboard
- **Real-time Monitoring**: Auto-refresh dashboard during running agent executions
- **Pre-built Rule Sets**: Default repair rules for RuleBasedAgent covering all 37 mutations
- **Normalized Trajectory Export**: Standard JSONL format for training data pipelines
- **Reward Computation**: Difficulty-weighted reward signals for training data quality
- **Auto-Scaling**: Automatic difficulty adjustment based on agent performance
- **Audit Logging**: Append-only JSONL audit trail for all system actions
- **Benchmark Suite**: Predefined task sets (easy/medium/hard) with baseline comparison
- **Task Queue**: Priority-based scheduling with pause/resume and JSON persistence
- **CLI Benchmark**: `forgelab benchmark run` for evaluating agents against seed or held-out tasks
- **CLI Held-out**: `forgelab heldout create/list` for managing frozen benchmark task sets
- **Data Versioning**: Versioned training dataset snapshots for reproducibility
- **Example Curator**: Positive/negative example selection from verified runs
- **SFT/RL Export**: Training data export in Supervised Fine-Tuning and RL formats
- **Experiment Runner**: End-to-end experiment execution with paired comparison
- **Statistical Analysis**: T-tests, effect sizes, confidence intervals, chi-square tests
- **CLI Train**: `forgelab train version/curate` for training data management
- **CLI Experiment**: `forgelab experiment run/report` for experiment execution and analysis

## CLI Commands

```bash
forgelab init                          # Initialize database and directories
forgelab doctor                        # Check system requirements
forgelab world generate                # Generate a broken repo
forgelab world validate --world-id X   # Validate a world
forgelab task list                     # List tasks
forgelab task validate --task-id X     # Validate a task
forgelab run --task-id X               # Run MockAgent on a task
forgelab run inspect --run-id X        # Inspect a run
forgelab curriculum inspect            # View curriculum state
forgelab experiment create --name X    # Create an experiment
forgelab export --format json          # Export run data as JSON/CSV
forgelab db upgrade                    # Apply database migrations
forgelab benchmark run --agent mock    # Run benchmark evaluation
forgelab benchmark suite --level easy  # Run easy benchmark suite
forgelab heldout create --size 10      # Create held-out task set
forgelab train version --tag v1.0      # Version training data
forgelab train curate --format sft     # Curate positive/negative examples
forgelab experiment run --preset A     # Run experiment preset
forgelab experiment report             # Statistical comparison report
forgelab snapshot capture ./workspace  # Capture workspace snapshot
forgelab snapshot list                 # List saved snapshots
forgelab coverage                      # Analyze mutation coverage
forgelab difficulty-calibrate          # Calibrate task difficulty
forgelab behavior-analyze              # Analyze agent behavior
forgelab report-generate -t research   # Generate evaluation report
forgelab serve                         # Start API server
```

## Configuration

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `FORGELAB_DB` | `forgelab.db` | Database path |
| `FORGELAB_PROVIDER` | `mock` | Agent provider (mock/openai) |
| `FORGELAB_API_KEY` | | API key for LLM agents |
| `FORGELAB_MODEL` | | Model identifier |
| `FORGELAB_MAX_STEPS` | `50` | Max tool-call steps per run |

## Testing

```bash
pytest tests/ -v
```

- **Multi-Agent Curriculum**: Per-agent capability tracking with cross-agent knowledge transfer
- **Cross-Domain Curriculum**: Knowledge transfer across template domains
- **Resource-Aware Scheduling**: CPU/memory monitoring for parallel execution
- **Container Signing**: SHA-256 hash-based sandbox integrity verification
- **Security Audit**: Automated checks for hardcoded secrets and insecure patterns
- **Benchmark Publication**: Markdown/JSON reports with baseline comparison
- **A/B Testing**: Formal statistical comparison of two agents with significance testing
- **Custom Experiments**: YAML-based experiment definitions beyond presets
- **Network Policies**: Sandbox network restriction (allow_all, restrict_outbound, block_all)
- **Image Validation**: Container image security checks for Dockerfiles
- **MLflow Integration**: Optional experiment tracking with graceful fallback
- **Browser Automation Template**: Playwright-style automation with XSS/clickjacking protection
- **CLI A/B Test**: `forgelab experiment ab-test` for comparing two agents
- **CLI Custom Experiment**: `forgelab experiment custom` for YAML-defined experiments
- **CLI Sandbox Security**: `forgelab sandbox security` for network policy enforcement
- **Dashboard Filtering**: Filter runs by agent type, status, pass/fail, and search on Runs page
- **Workspace Snapshots**: Capture and restore workspace states for reproducibility
- **Mutation Coverage Analysis**: Identify which mutations are tested and find coverage gaps
- **Difficulty Calibration**: Measure actual vs assigned difficulty and suggest adjustments
- **Agent Behavior Analysis**: Analyze tool call patterns and failure modes per agent
- **Report Templates**: Pre-built report formats (research_paper, executive_summary, technical_deep_dive)
- **612 tests** covering core schemas, world generation, mutations, validation, agents, runner, evaluation, diagnosis, curriculum, experiments, sandbox, training adapter, Alembic migrations, seed task loader, integration tests, v0.2-v0.8 features, and v0.9 features (dashboard filtering, workspace snapshots, mutation coverage, difficulty calibration, behavior analysis, report templates).

## Current Limitations

- Verifier requires Docker daemon for hidden test execution; without Docker, runs are diagnosed as `environment_failure` (fail-closed policy)
- OpenAI agent requires `pip install openai` and `FORGELAB_API_KEY` environment variable
- MockAgent is deterministic simulation, clearly labeled as such in all records
- No model weight training (curriculum adaptation only; training adapter interface prepared for future integration)
- 14 environment templates with 37 mutations

## Roadmap

- [x] Core pipeline: generate → validate → run → verify → diagnose → adapt
- [x] 14 environment templates with 37 bug mutations
- [x] 4 agent types: MockAgent, RuleBasedAgent, ScriptAgent, OpenAI-compatible agent
- [x] FastAPI backend with 26 REST routes
- [x] Streamlit dashboard with real database integration
- [x] Typer CLI with full command set
- [x] Failure attribution engine with 6 categories
- [x] Adaptive curriculum with capability tracking
- [x] Experiment management with 7 preset experiments (ablation, difficulty scaling, cross-template)
- [x] Static analysis checks (flake8/mypy) as optional verification criteria
- [x] Run data export as JSON/CSV via CLI and dashboard
- [x] Agent configuration profiles (conservative, aggressive, balanced)
- [x] Performance regression checks with baseline tracking
- [x] Held-out evaluation set for frozen benchmarking
- [x] Trajectory visualization in dashboard
- [x] Code diff viewer — side-by-side view of agent workspace changes
- [x] Real-time run monitoring — auto-refresh dashboard during agent execution
- [x] Pre-built rule sets for RuleBasedAgent covering all 37 mutations
- [x] Benchmark runner with pass rate, capability breakdown, timing reports, and baseline comparison
- [x] CLI benchmark and held-out evaluation commands
- [x] Data versioning for training dataset reproducibility
- [x] Example curator for positive/negative training data selection
- [x] SFT and RL format export for training data
- [x] Experiment runner for end-to-end experiment execution
- [x] Statistical analysis (t-tests, effect sizes, confidence intervals)
- [x] CLI train and experiment commands
- [x] Normalized trajectory export in standard JSONL format
- [x] Reward computation with difficulty-weighted signals
- [x] Auto-scaling difficulty adjustment based on agent performance
- [x] Audit logging for all system actions
- [x] Benchmark suite with predefined task sets and baseline comparison
- [x] Task queue with priority scheduling and persistence
- [x] Cross-domain curriculum with knowledge transfer across template domains
- [x] Resource-aware scheduling with CPU/memory monitoring
- [x] Container image signing for sandbox integrity verification
- [x] Security audit module for automated workspace checks
- [x] Benchmark publication with Markdown/JSON report generation
- [x] 14 environment templates including database_query, api_integration, and dsl
- [x] Dashboard filtering on Runs page (agent type, status, pass/fail, search)
- [x] Workspace snapshot capture and restore for reproducibility
- [x] Mutation coverage analysis with gap detection
- [x] Difficulty calibration comparing assigned vs actual difficulty
- [x] Agent behavior analysis with tool call patterns and failure modes
- [x] Report templates (research_paper, executive_summary, technical_deep_dive)
- [ ] Docker-based verifier for hidden tests in production
- [ ] GRPO/PPO training adapter integration
- [ ] MLflow/W&B experiment tracking

## Research References

1. [Microsoft Echoverse](https://github.com/microsoft/Echoverse) — Environment construction and grounded evaluation
2. [Orchard-Agentic](https://microsoft.github.io/Orchard-Agentic/) — AutoEnvScaling and Self-HPO
3. [Agent Lightning](https://github.com/microsoft/agent-lightning) — RL for coding agents
4. [Hugging Face TRL](https://github.com/huggingface/trl) — RL training library

## License

MIT
