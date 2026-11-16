# Research Methodology

## Research Question

**Can validation-first environment generation and failure-attribution-aware adaptive curricula improve the generalization of autonomous software engineering agents to previously unseen tasks, compared with fixed task curricula under equivalent inference budgets?**

## Hypotheses

| ID | Hypothesis | Status |
|----|-----------|--------|
| H1 | Adaptive task generation produces more useful learning experiences than a fixed task curriculum. | Pending |
| H2 | Independent environment validation reduces misleading agent-failure signals. | Pending |
| H3 | Targeted task generation improves agent capability on related, previously unseen tasks. | Pending |
| H4 | Separating environment defects, invalid tasks, verifier failures, and genuine agent failures improves the quality of training data. | Pending |
| H5 | Adaptive task generation can improve training efficiency without increasing model size. | Pending |

These are hypotheses to investigate, not results to claim.

## Key Distinctions

It is critical to distinguish between three different kinds of "improvement":

### 1. Task Adaptation (What ForgeLab v0.1 Does)

ForgeLab generates and selects tasks based on verified agent performance. The task distribution changes, but the underlying model weights do not. This is **curriculum learning** — presenting tasks in an order or distribution that promotes learning.

**What improves:** The quality and relevance of training experiences.
**What doesn't change:** The model's neural network weights.

### 2. Agent Inference-Time Improvement

An agent may improve its performance within a single session through techniques like self-reflection, chain-of-thought prompting, or iterative refinement. This is **inference-time adaptation** — the agent uses its own reasoning to improve outputs without changing weights.

**What improves:** The agent's output quality within a session.
**What doesn't change:** The model's neural network weights.

### 3. Neural Network Training

Actual model-weight training (supervised fine-tuning, reinforcement learning, GRPO, PPO) updates the model's parameters based on training data. This is **model learning** — the model's internal representation changes.

**What improves:** The model's capabilities across all tasks.
**What changes:** The model's neural network weights.

**ForgeLab v0.1 implements only task adaptation.** The training adapter interface is designed for future integration with Hugging Face TRL, GRPO, PPO, or Microsoft Agent Lightning, but model-weight training is not part of v0.1.

## Experimental Design

### Control Variables

When comparing approaches, the following are held constant:

- Same model (same architecture, same weights)
- Same inference budget (same number of API calls or tokens)
- Same evaluation set (frozen held-out tasks)
- Same environment templates
- Same verification criteria

### Independent Variables

- Task selection strategy (static vs adaptive)
- Validation pipeline (none vs full validation)
- Task targeting (random vs weakness-focused)
- Verification authority (generator-only vs independent)

### Dependent Variables

- Success rate on held-out evaluation set
- Success rate on training tasks
- Generalization to unseen task categories
- Cost per solved task
- Number of training cycles to reach target performance

## Validation Pipeline

Every generated task passes through independent validation before reaching an agent:

```
1. World Validation
   - Repository exists and is accessible
   - Required files present
   - Dependencies install successfully
   - Public tests execute
   - Intended defect is present
   - Environment can be reset

2. Reference Solution Validation
   - Reference fix applied in separate workspace
   - Public tests pass after fix
   - Hidden tests pass after fix
   - No unrelated functionality broken

3. Initial Defect Validation
   - Unmodified environment fails hidden tests
   - Defect is detectable
   - Environment not already fixed

4. Task Validation
   - Description matches actual defect
   - Acceptance criteria achievable
   - Constraints consistent
   - Required files and dependencies exist
   - Task has sufficient information to be solvable

5. Verifier Validation
   - Verifier detects known defects (negative test)
   - Verifier accepts known correct solutions (positive test)
   - Verifier behaves consistently across runs
```

A task is released to an agent only if all validation stages pass.

## Failure Attribution

Every run outcome is classified into one of six categories:

| Category | Evidence Required | Action |
|----------|-------------------|--------|
| `agent_failure` | Valid env + valid task + working verifier + agent didn't solve | Preserve as learning signal |
| `environment_failure` | Dependency/startup/filesystem/runtime failure | Quarantine, repair world |
| `invalid_task` | Ambiguous, impossible, or contradictory task spec | Reject or revise |
| `verifier_failure` | Verifier rejects correct or accepts incorrect | Repair verifier |
| `infrastructure_failure` | Timeout, API outage, sandbox crash | Retry or abort |
| `uncertain` | Insufficient evidence for any category | Manual review |

**Key principle:** A failed agent run is never automatically a negative training example. First establish that the environment, task, and verifier were valid.

## Adaptive Curriculum

The curriculum engine tracks per-capability performance:

- `debugging`: Ability to locate and fix bugs
- `edge_case_reasoning`: Handling boundary conditions
- `testing`: Writing and running tests
- `code_navigation`: Finding relevant code in a repository
- `regression_analysis`: Identifying and fixing regressions
- `api_design`: Designing and implementing APIs

For each capability, it records: attempts, successes, failures, confidence estimate, recent performance, task difficulty, and historical changes.

**Selection strategies:**

1. **Static:** Fixed sequence of tasks
2. **Random:** Random selection from task pool
3. **Adaptive:** Targets verified weaknesses with diversity constraints

## Evaluation Metrics

| Category | Measurement |
|----------|-------------|
| Environment quality | Percentage of generated worlds passing validation |
| Task quality | Percentage of tasks independently verified as solvable |
| Verifier quality | False-positive and false-negative rates |
| Agent capability | Pass@1 and Pass@k |
| Efficiency | Cost per solved task and execution time |
| Difficulty | Success rate by difficulty category |
| Generalization | Performance on unseen environment templates |
| Learning | Change in performance across training cycles |

## Reproducibility

- All random operations use explicit seeds
- Same seed + same blueprint → identical environment
- Task and trajectory data versioned with schema versions
- Run artifacts preserved for future review
- Configuration files versioned and stored with experiments

## Limitations

1. **Single environment domain:** v0.1 supports only Python repository repair. Generalization to other domains (browser automation, database queries, etc.) requires additional templates.
2. **MockAgent is deterministic:** MockAgent scenarios are hardcoded for testing infrastructure. Real model performance requires an API-powered agent.
3. **Docker required for verification:** Hidden test execution requires a running Docker daemon. Without Docker, runs are diagnosed as `environment_failure`.
4. **No model-weight training:** v0.1 improves task selection, not model capabilities. Training adapter interface is prepared but not connected to a trainer.
5. **Small task set:** 3 seed mutations with procedural variants. Larger-scale evaluation requires more templates and mutations.
