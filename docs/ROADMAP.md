# Roadmap

## v0.1 — Current Release

**Status:** ✓ Complete

- [x] Core schemas, configuration, and error handling
- [x] World factory with deterministic bug injection (14 templates, 37 mutations)
- [x] Task factory with structured task specs
- [x] Validation pipeline (world, task, verifier, reference solution)
- [x] Docker sandbox manager with security policies
- [x] MockAgent with deterministic scenarios
- [x] Run orchestrator and trajectory recorder
- [x] Independent verifier
- [x] Failure attribution engine (6 categories)
- [x] Adaptive curriculum engine (3 strategies)
- [x] Experiment management
- [x] FastAPI REST backend (26 routes)
- [x] Streamlit dashboard (7 pages)
- [x] Typer CLI
- [x] End-to-end demo pipeline
- [x] Unit tests (576+ tests)
- [x] Alembic database migrations
- [x] CI/CD GitHub Actions workflow
- [x] Docker Compose setup
- [x] Documentation (README, ARCHITECTURE, RESEARCH, EXPERIMENTS, SECURITY, ROADMAP)

---

## v0.2 — Expanded Environments and Real Agents

**Status:** ✓ Complete

**Goal:** Prove the pipeline works with real LLM agents and more environment types.

### Environment Expansion

- [x] Additional repository templates (express_api, django_app, typescript_api, go_service, react_app, spring_service — 9 templates total)
- [x] More bug mutation types (security vulnerabilities: CORS, rate limiting, SQL injection, stack trace exposure, nil pointer, resource leak, XSS injection, transaction leak, N+1 queries, validation bypass — 23 mutations total)
- [x] LLM-assisted task generation (LLMTaskGenerator with OpenAI API, graceful fallback)
- [x] Task variant generation from seed templates (seed task loader)
- [x] Held-out evaluation set (frozen tasks the generator never sees)

### Real Agent Integration

- [x] OpenAI-compatible agent with tool-calling
- [x] RuleBasedAgent with configurable YAML rules
- [x] ScriptAgent for external Python script execution
- [x] Anthropic Claude agent adapter (ClaudeAgent with tool-calling, graceful fallback)
- [x] Open-source model support (OpenSourceAgent via Ollama/vLLM, graceful fallback)
- [x] Agent configuration profiles (temperature, max tokens, system prompts)
- [x] Token usage tracking and cost estimation

### Verification Improvements

- [x] Docker-based hidden test execution (requires Docker daemon)
- [x] Static analysis checks (flake8, mypy) as verification criteria
- [x] Performance regression checks
- [x] Fuzzing-based verification for edge cases

### Dashboard Improvements

- [x] Dashboard charts (pass/fail bar chart, failure type pie chart)
- [x] Real-time run monitoring (auto-refresh during agent execution)
- [x] Trajectory visualization (tool call timeline)
- [x] Code diff viewer for agent changes (side-by-side view)
- [x] Export run data as JSON/CSV

### Experiment Expansion

- [x] Tool ablation study experiment
- [x] Difficulty scaling analysis experiment
- [x] Cross-template generalization experiment
- [x] Experiment comparison report generator

### CLI Improvements

- [x] Progress indicators during run execution
- [x] Database management commands (init, upgrade, current, reset)
- [x] Alembic migrations integration

---

## v0.4 — Multi-Agent and Research Tools

**Status:** ✓ Complete

**Goal:** Enable multi-agent comparison, parallel execution, and research-grade benchmarking.

### Multi-Agent Execution

- [x] Multi-agent comparison runner (run multiple agents on same tasks)
- [x] Parallel task execution with ThreadPoolExecutor
- [x] Side-by-side comparison reports with pass rates and timing

### Sandbox and Verification

- [x] Local sandbox fallback for running tests without Docker
- [x] Isolated subprocess execution with sys.path restriction

### Task Generation

- [x] Task variant generator for creating task variations
- [x] Automated variant storage and loading
- [x] Template-specific mutation mapping

### Curriculum

- [x] Curriculum state persistence (save/load/export/import)
- [x] Cross-session curriculum sharing
- [x] JSON-based snapshot format

### Benchmarking

- [x] Benchmark leaderboard for tracking agent performance
- [x] Agent rankings sorted by pass rate
- [x] Markdown and JSON export

---

## v0.6 — Research Robustness and Composite Challenges

**Status:** ✓ Complete

**Goal:** Test agent robustness with adversarial conditions and composite (multi-bug) tasks, plus comprehensive evaluation reporting.

### Adversarial Testing

- [x] Error injection framework (syntax, import, type, attribute, runtime errors)
- [x] Adversarial agent wrapper for any base agent
- [x] Configurable error rate and error types
- [x] Robustness scoring based on error handling

### Composite Mutations

- [x] Multiple bugs per task for harder, more realistic challenges
- [x] Conflict detection for overlapping mutation patterns
- [x] Compatible mutation pair/triple discovery
- [x] Composite task spec generation with combined difficulty

### Cross-Template Analysis

- [x] Mutation pattern analysis across all templates
- [x] Capability coverage mapping
- [x] Template coverage reporting
- [x] Markdown report generation

### Evaluation Reports

- [x] Comprehensive evaluation report generator
- [x] Pass rates by template, agent, difficulty
- [x] Failure category breakdown
- [x] Timing analysis (avg/min/max duration)
- [x] Markdown and JSON report output
- [x] Automated recommendations based on stats

### New Templates

- [x] config_manager template (ConfigLoader, Validator, Merger, EnvironmentHandler, SecretManager)
- [x] 3 new mutations: env_override, secret_exposure, merge_conflict
- [x] 11 templates total, 29 mutations total

### Test Coverage

- [x] 536 tests covering all v0.6 modules
- [x] Error injection tests (9 tests)
- [x] Adversarial agent tests (5 tests)
- [x] Composite mutation tests (7 tests)
- [x] Cross-template analysis tests (5 tests)
- [x] Evaluation report tests (9 tests)
- [x] Config manager template tests (4 tests)

---

## v0.7 — Research Workflow and Multi-Agent Curriculum

**Status:** ✓ Complete

**Goal:** Complete the research workflow with multi-agent curriculum, A/B testing, custom experiments, and security hardening.

### Multi-Agent Curriculum

- [x] Multi-agent curriculum with per-agent capability tracking
- [x] Cross-agent knowledge transfer (none/partial/full sharing levels)
- [x] Task selection based on weakest capability
- [x] Curriculum state comparison across agents

### A/B Testing

- [x] Formal A/B test runner for comparing two agents
- [x] Two-proportion z-test for statistical significance
- [x] Cohen's d effect size calculation
- [x] Confidence interval for difference in pass rates
- [x] Markdown and JSON report output

### Custom Experiments

- [x] YAML-based custom experiment definitions
- [x] Support for single_agent, multi_agent, ab_test, benchmark types
- [x] Experiment validation and directory scanning
- [x] Save and reload experiment definitions

### Security Hardening

- [x] Network policy enforcement (allow_all, restrict_outbound, block_all)
- [x] Container image validation for Dockerfiles
- [x] Vulnerable base image detection
- [x] Layer count and size checks

### MLflow Integration

- [x] Optional MLflow tracking for experiment results
- [x] Graceful fallback when MLflow not installed
- [x] Metric, parameter, and artifact logging
- [x] Environment variable configuration (FORGELAB_MLFLOW_TRACKING_URI)

### New Templates

- [x] browser_automation template (Browser, Page, Element, Selector, Action)
- [x] 3 new mutations: xss_reflected, clickjacking, auth_bypass
- [x] 11 templates total, 29 mutations total

### Test Coverage

- [x] 536 tests covering all v0.7 modules
- [x] Multi-agent curriculum tests (10 tests)
- [x] A/B testing tests (10 tests)
- [x] Custom experiment tests (8 tests)
- [x] Network policy tests (6 tests)
- [x] Image validation tests (6 tests)
- [x] MLflow tracker tests (5 tests)
- [x] Browser automation template tests (6 tests)

---

- [x] Side-by-side agent comparison

### Environment Expansion

- [x] TypeScript API template (Router, Middleware, InputValidator, ErrorHandler)
- [x] Go Service template (Store, Handler, Validator, Logger)
- [x] 4 new mutations: error_leak, input_validation, nil_pointer, resource_leak

---

## v0.5 — Training Data Quality and Adaptive Curriculum

**Status:** ✓ Complete

**Goal:** Improve training data quality with normalized exports, reward signals, and adaptive difficulty.

### Training Data

- [x] Normalized trajectory export in standard JSONL format
- [x] Reward computation with difficulty-weighted signals
- [x] Pluggable reward function via subclassing

### Adaptive Curriculum

- [x] Auto-scaling difficulty adjustment based on agent performance
- [x] Sliding window of recent runs per agent-template pair
- [x] Configurable thresholds for increase/decrease/maintain

### Audit and Reproducibility

- [x] Append-only JSONL audit logging for all system actions
- [x] Filterable audit log by action, timestamp, and limit
- [x] Log rotation for large files

### Benchmarking

- [x] Benchmark suite with predefined task sets (easy/medium/hard/all)
- [x] Baseline comparison for regression detection
- [x] Task queue with priority scheduling and JSON persistence

### Environment Expansion

- [x] React App template (Component, StateManager, EventDispatcher, Router, FormHandler)
- [x] Spring Service template (Repository, TransactionManager, Validator, Service, Controller)
- [x] 4 new mutations: xss_injection, transaction_leak, n_plus_one, validation_bypass

---

## v0.3 — Training Integration

**Status:** ✓ Complete

**Goal:** Connect verified trajectories to model training pipelines.

### Training Adapter

- [x] Hugging Face TRL integration (TRLTrainer with SFT/DPO, graceful fallback)
- [x] GRPO support (GRPOTrainer with group-relative advantages, graceful fallback)
- [x] Microsoft Agent Lightning integration (AgentLightningClient, graceful fallback)
- [x] Normalized trajectory export format
- [x] Reward signal computation from verification results

### Training Data Quality

- [x] Trajectory filtering based on pass/fail, reward, failure category, difficulty
- [x] Difficulty-weighted reward computation
- [x] Session replay module for trajectory analysis
- [x] Code quality tools (Black, Ruff, mypy) with CI/CD integration
- [x] Only genuine agent failures used as negative examples (ExampleCurator)
- [x] Verified successful runs used as positive examples (ExampleCurator)
- [x] Data versioning and reproducibility (DatasetVersioner)
- [x] SFT and RL format export for training data

### Experiment Execution

- [x] Experiment runner for end-to-end experiment execution
- [x] Paired experiment comparison
- [x] Statistical analysis (t-tests, effect sizes, confidence intervals, chi-square)
- [x] Statistical comparison report generator
- [x] Run Experiment A (static vs adaptive curriculum) — implemented with RuleBasedAgent baseline
- [x] Run Experiment B (random vs validated environments) — implemented with RuleBasedAgent baseline
- [x] Run Experiment C (generic vs targeted challenges) — implemented with RuleBasedAgent baseline
- [x] Run Experiment D (single-agent vs independent verification) — implemented with RuleBasedAgent baseline

---

## v0.8 — Research Readiness and Multi-Domain Expansion

**Status:** ✓ Complete

**Goal:** Finalize self-contained features for research readiness: multi-domain templates, cross-domain curriculum, resource-aware scheduling, and security hardening.

### Multi-Domain Templates

- [x] database_query template (QueryBuilder, ConnectionPool, ResultCache, IndexManager, QueryOptimizer)
- [x] api_integration template (APIClient, RateLimiter, TokenManager, RetryHandler, ResponseParser)
- [x] dsl template (Lexer, Parser, AST, Interpreter, Validator)
- [x] 9 new mutations: sql_injection, n_plus_one_query, missing_index, rate_limit_bypass, auth_token_leak, schema_mismatch, syntax_error, type_coercion, undefined_reference
- [x] 14 templates total, 37 mutations total

### Cross-Domain Curriculum

- [x] CrossDomainCurriculum with per-domain capability tracking
- [x] Knowledge transfer across template domains (similar_pattern, random, none strategies)
- [x] Cross-template mutation pattern analysis integration

### Resource-Aware Scheduling

- [x] ResourceManager with CPU/memory monitoring via psutil
- [x] Worker allocation and release with resource limits
- [x] Configurable thresholds for max CPU, memory, and workers

### Security Hardening

- [x] Container image signing with SHA-256 hashing
- [x] Image verification and tamper detection
- [x] Security audit module for automated workspace checks
- [x] Detection of hardcoded secrets, eval/exec usage, debug mode

### Benchmark Publication

- [x] BenchmarkPublisher for Markdown/JSON report generation
- [x] Pass rate breakdown by template and difficulty
- [x] Baseline comparison with regression detection
- [x] Report publishing to files

---

## v0.9 — Research Polish and Final Self-Contained Features

**Status:** ✓ Complete

**Goal:** Complete all self-contained features before the platform depends on external APIs. Final polish for research readiness.

### Dashboard

- [x] Dashboard filtering on Runs page (agent type, status, pass/fail, search)
- [x] Filter state preserved across interactions
- [x] Summary metrics update with filtered data

### Workspace Reproducibility

- [x] Workspace snapshot capture and restore (WorkspaceSnapshotter)
- [x] JSON-based snapshot format with file contents
- [x] Snapshot listing and CLI commands (forgelab snapshot capture/restore/list)

### Mutation Coverage

- [x] Mutation coverage analysis (MutationCoverageAnalyzer)
- [x] Coverage report with covered/uncovered mutations
- [x] Markdown report output
- [x] CLI command (forgelab coverage)

### Difficulty Calibration

- [x] Difficulty calibrator comparing assigned vs actual difficulty (DifficultyCalibrator)
- [x] Pass rate-based adjustment suggestions
- [x] Over/under-estimated task detection
- [x] CLI command (forgelab difficulty-calibrate)

### Agent Behavior Analysis

- [x] Behavior analyzer for tool call patterns and failure modes (BehaviorAnalyzer)
- [x] Per-agent behavior profiles with tool usage and failure clustering
- [x] Markdown and JSON export
- [x] CLI command (forgelab behavior-analyze)

### Report Templates

- [x] Pre-built report templates: research_paper, executive_summary, technical_deep_dive
- [x] Template-specific formatting for different audiences
- [x] CLI command (forgelab report-generate)

### Test Coverage

- [x] 612 tests covering all v0.9 modules
- [x] Workspace snapshot tests (8 tests)
- [x] Mutation coverage tests (6 tests)
- [x] Difficulty calibration tests (6 tests)
- [x] Behavior analysis tests (8 tests)
- [x] Report template tests (8 tests)

---

## v1.0 — Research-Grade Platform

**Status:** ✓ Complete

**Goal:** Production-ready platform for agentic AI research.

### Multi-Domain Support

- [x] Browser automation environments (browser_automation template)
- [x] Database query optimization environments (database_query template)
- [x] API design and integration environments (api_integration template)
- [x] Configuration management environments (config_manager template)
- [x] Domain-specific language environments (dsl template)

### Advanced Curriculum

- [x] Multi-agent curriculum (different agents, different weaknesses)
- [x] Cross-domain transfer learning
- [x] Automatic difficulty scaling
- [x] Curriculum state persistence and sharing

### Distributed Execution

- [x] Kubernetes-based sandbox orchestration (K8SSandboxManager, graceful fallback)
- [x] Parallel run execution
- [x] Queue-based task scheduling
- [x] Resource-aware scheduling

### Research Tools

- [x] MLflow integration (optional, graceful fallback)
- [x] Custom experiment definitions
- [x] A/B testing framework
- [x] Benchmark suite with published results

### Security Hardening

- [x] Security audit module for automated workspace checks
- [x] Container image signing
- [x] Network policy enforcement
- [x] Audit logging

---

## Contributing

We welcome contributions in the following areas:

1. **New environment templates:** Add templates for different programming languages or domains.
2. **New bug mutations:** Expand the set of injectable defects.
3. **Agent adapters:** Support additional model providers.
4. **Verification methods:** Add new ways to validate agent outcomes.
5. **Dashboard features:** Improve visualization and analysis tools.
6. **Documentation:** Improve clarity and completeness.

### Getting Started

1. Fork the repository
2. Set up development environment: `pip install -e ".[dev]"`
3. Run tests: `pytest tests/ -v`
4. Run the demo: `python examples/demo_pipeline.py`
5. Submit a pull request

### Code Style

- Type hints for all public interfaces
- Pydantic v2 for data validation
- Black for code formatting
- Docstrings for all modules and public functions

---

## Research References

ForgeLab is inspired by and builds upon the following research:

1. **Microsoft Echoverse** — Environment construction, database-backed tasks, verification, and reset.
2. **Microsoft Orchard-Agentic** — Reusable agent environments, AutoEnvScaling, Self-HPO.
3. **Microsoft Agent Lightning** — Connecting agents to RL training.
4. **Hugging Face TRL** — Supervised fine-tuning, GRPO, and model training.
5. **Prime Intellect Verifiers** — Composable environments, rewards, and verifiable agent training.

ForgeLab's contribution is a **validation-first adaptive environment generation and failure-attribution pipeline** for autonomous software engineering agents.
