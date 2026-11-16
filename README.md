# ForgeLab

A research platform for testing and improving autonomous coding agents.

ForgeLab creates broken code repositories, runs AI agents against them, checks if the fixes actually work, figures out why they failed when they do, then uses those insights to generate better training tasks. The whole loop runs automatically.

## The Problem

Most coding agent benchmarks use static task sets. Agents memorize them. Researchers can't tell if a failure is the agent's fault or a bad task. And there's no way to automatically generate harder challenges based on what an agent struggles with.

ForgeLab addresses three gaps:

1. **Can we generate valid coding tasks programmatically?** — Yes, via template-based world generation with independent validation.
2. **Can we tell why an agent failed?** — Yes, via a 6-category failure attribution engine that distinguishes agent bugs from task bugs from environment issues.
3. **Can we use those failures to improve training?** — Yes, via adaptive curriculum that tracks capability scores and generates targeted tasks.

## How It Compares

| Project | What They Do | What ForgeLab Adds |
|---|---|---|
| [Echoverse](https://github.com/microsoft/Echoverse) | Stateful computer-use environments | Terminal-based code repair environments |
| [Orchard-Agentic](https://microsoft.github.io/Orchard-Agentic/) | Auto-scaling from agent rollouts | Validation-first generation with failure attribution |
| [Agent Lightning](https://github.com/microsoft/agent-lightning) | RL training for coding agents | Portable eval layer that works with any agent |

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
├── core/           # Schemas, config, errors, events
├── world_factory/  # Template-based broken repo generation
├── task_factory/   # Task spec creation and seed loading
├── validators/     # Independent validation
├── agents/         # Pluggable agents (4 built-in types)
├── runner/         # Run orchestration and trajectory recording
├── evaluation/     # Test verification and analysis
├── diagnosis/      # Failure attribution (6 categories)
├── curriculum/     # Adaptive task selection
├── experiments/    # Experiment management and stats
├── sandbox/        # Isolated execution (Docker + local fallback)
├── training/       # Trajectory export, rewards, data curation
├── api/            # FastAPI REST backend
├── db/             # SQLAlchemy models (SQLite)
└── cli.py          # Command-line interface
```

## The Pipeline

```
Generate World → Validate → Create Task → Run Agent →
Verify Fix → Diagnose Failure → Adapt Curriculum → Repeat
```

Each step is independent. Worlds are validated before agents see them. Fixes are verified separately from the agent. Failures are categorized so you know whether the agent, task, or environment was at fault.

## What's Included

**Environments:** 14 templates covering common patterns — APIs, data pipelines, web apps, ORMs, config systems, DSLs, browser automation, and more. 37 mutation types inject realistic bugs: null handling, SQL injection, CSRF, rate limiting, XSS, transaction leaks, and others.

**Agents:** Four built-in agent types. `MockAgent` for testing without API keys. `RuleBasedAgent` with pre-built repair rules for all 37 mutation types. `ScriptAgent` for running your own Python scripts. `OpenAI-compatible` agent with tool calling (requires API key). Plus an adversarial wrapper for stress testing.

**Evaluation:** Independent test verification (public + hidden tests), static analysis (flake8/mypy), fuzzing-based edge case testing, performance regression detection, and code diff viewing.

**Failure Diagnosis:** 6-category attribution engine — agent failure, environment failure, task failure, verifier failure, infrastructure failure, or uncertain. Each diagnosis includes evidence.

**Curriculum:** Adaptive task selection that tracks per-agent capability scores, auto-adjusts difficulty, supports cross-domain knowledge transfer, and persists state between sessions.

**Experiments:** 7 preset experiments (ablation studies, difficulty scaling, cross-template generalization, etc.), A/B testing with statistical significance, custom YAML-based experiment definitions, and MLflow integration.

**Interfaces:** FastAPI backend (26 routes), Streamlit dashboard with filtering and charts, and a full Typer CLI.

**Training Data:** Normalized trajectory export (JSONL), difficulty-weighted reward signals, positive/negative example curation, SFT and RL format export, and dataset versioning.

**Security:** Docker sandbox isolation, network policies, container image signing, and automated security audits.

## CLI

```bash
forgelab init                          # Set up database and directories
forgelab doctor                        # Check system health
forgelab world generate                # Generate a broken repo
forgelab run --task-id X               # Run an agent on a task
forgelab benchmark run --agent mock    # Evaluate an agent
forgelab experiment run --preset A     # Run a preset experiment
forgelab export --format json          # Export run data
forgelab serve                         # Start the API server
forgelab --help                        # See all commands
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

612 tests covering all modules. The full suite runs in ~15 seconds.

## Limitations

- **Docker required for hidden tests.** Without a Docker daemon, the verifier can't run hidden test suites in isolation. Runs are marked as `environment_failure` — the safe default.
- **OpenAI agent needs an API key.** Install `openai` and set `FORGELAB_API_KEY`. Without it, use MockAgent or RuleBasedAgent.
- **No model training yet.** The training adapter exports data and computes rewards, but actual RL training (GRPO/PPO) isn't implemented. The interface is ready for it.

## What's Next

- Docker-based verifier for production hidden test execution
- GRPO/PPO training adapter integration
- MLflow/W&B experiment tracking

For the full roadmap see [ROADMAP.md](docs/ROADMAP.md).

## Research References

1. [Microsoft Echoverse](https://github.com/microsoft/Echoverse) — Environment construction and grounded evaluation
2. [Orchard-Agentic](https://microsoft.github.io/Orchard-Agentic/) — AutoEnvScaling and Self-HPO
3. [Agent Lightning](https://github.com/microsoft/agent-lightning) — RL for coding agents
4. [Hugging Face TRL](https://github.com/huggingface/trl) — RL training library

## License

MIT
