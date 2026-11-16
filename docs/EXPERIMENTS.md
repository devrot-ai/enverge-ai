# Experiments

This document describes the experiments designed to evaluate ForgeLab's hypotheses. Each experiment compares two approaches while holding all other variables constant.

## Experiment A: Static vs Adaptive Curriculum

**Question:** Does adaptive task selection improve performance on a fixed held-out benchmark?

**Hypothesis (H1):** Adaptive task generation produces more useful learning experiences than a fixed task curriculum.

### Design

| Variable | Static Group | Adaptive Group |
|----------|-------------|----------------|
| Task selection | Fixed sequence | Failure-targeted adaptive |
| Model | Same | Same |
| Inference budget | Same | Same |
| Evaluation set | Frozen held-out tasks | Frozen held-out tasks |
| Validation | Full pipeline | Full pipeline |

### Procedure

1. Generate a set of validated tasks from the same templates.
2. **Static group:** Present tasks in a fixed order (e.g., by difficulty).
3. **Adaptive group:** Use `CurriculumSelector` with `adaptive` strategy to select tasks based on verified agent weaknesses.
4. Run both groups for the same number of cycles.
5. Evaluate both groups on the same frozen held-out evaluation set.

### Metrics

- Success rate on held-out evaluation set
- Success rate on training tasks
- Number of cycles to reach target performance
- Diversity of tasks attempted

### Running the Experiment

```bash
# Create the experiment
forgelab experiment create --name "static-vs-adaptive" --strategy adaptive

# Or via API
curl -X POST http://localhost:8000/api/v1/experiments \
  -H "Content-Type: application/json" \
  -d '{"name": "static-vs-adaptive", "strategy": "adaptive"}'
```

---

## Experiment B: Random vs Validated Environments

**Question:** How many misleading failures are caused by broken worlds?

**Hypothesis (H2):** Independent environment validation reduces misleading agent-failure signals.

### Design

| Variable | Unvalidated Group | Validated Group |
|----------|-------------------|-----------------|
| Validation | None (skip validation) | Full validation pipeline |
| Model | Same | Same |
| Task generation | Same | Same |
| Evaluation | Same | Same |

### Procedure

1. Generate the same set of tasks.
2. **Unvalidated group:** Skip all validation steps, release tasks directly to agents.
3. **Validated group:** Run full validation pipeline (world, task, verifier, reference solution).
4. Run both groups and record outcomes.
5. Compare failure attribution distributions.

### Metrics

- Percentage of runs diagnosed as `environment_failure`
- Percentage of runs diagnosed as `invalid_task`
- Percentage of runs diagnosed as `verifier_failure`
- Genuine agent failure rate
- Overall success rate

### Expected Outcome

The unvalidated group should show a higher rate of non-agent failures (environment, task, verifier), indicating that validation filters out misleading signals.

---

## Experiment C: Generic vs Targeted Challenges

**Question:** Does targeted practice improve transfer to unseen problems?

**Hypothesis (H3):** Targeted task generation improves agent capability on related, previously unseen tasks.

### Design

| Variable | Generic Group | Targeted Group |
|----------|--------------|----------------|
| Task targeting | Random selection | Weakness-focused selection |
| Model | Same | Same |
| Validation | Full pipeline | Full pipeline |
| Evaluation | Same held-out set | Same held-out set |

### Procedure

1. Run initial assessment to identify agent capabilities and weaknesses.
2. **Generic group:** Present random tasks from the pool.
3. **Targeted group:** Use `CurriculumSelector` to generate tasks focused on identified weaknesses.
4. Evaluate both groups on held-out tasks in the same capability categories.

### Metrics

- Improvement in weak capability scores
- Transfer to unseen tasks in same category
- Transfer to unseen tasks in different categories
- Cost per capability improvement

---

## Experiment D: Single-Agent vs Independent Verification

**Question:** How much does independent verification improve training-data quality?

**Hypothesis (H4):** Separating environment defects, invalid tasks, verifier failures, and genuine agent failures improves the quality of training data.

### Design

| Variable | Generator-Only | Independent Verification |
|----------|---------------|-------------------------|
| Verification | Generator self-validates | Independent validators |
| Failure attribution | All failures = agent failure | 6-category classification |
| Model | Same | Same |
| Task generation | Same | Same |

### Procedure

1. Generate the same set of tasks.
2. **Generator-only group:** Trust the generator's validation; classify all failures as agent failures.
3. **Independent group:** Run full validation pipeline with independent validators and failure classifier.
4. Compare the quality of training data produced by each approach.

### Metrics

- False positive rate (incorrectly labeled agent failures)
- False negative rate (missed genuine agent failures)
- Training data contamination rate
- Downstream model performance if training data is used

---

## Experiment Management

### Creating an Experiment

```bash
forgelab experiment create --name "my-experiment" --hypothesis "H1" --strategy adaptive
```

### Listing Experiments

```bash
forgelab experiment list
```

### Viewing Experiment Results

```bash
forgelab report --experiment-id "my-experiment"
```

### Comparing Experiments

```python
from forge.experiments.manager import ExperimentManager

manager = ExperimentManager()
comparison = manager.compare_experiments(["exp-a", "exp-b"])
print(comparison)
```

## Best Practices

1. **Hold constants:** Always use the same model, inference budget, and evaluation set when comparing approaches.
2. **Frozen evaluation set:** Never use the adaptive curriculum's generated tasks as the final evaluation set. Freeze a separate collection of tasks and templates that the generator never sees.
3. **Random seeds:** Use explicit random seeds for reproducibility.
4. **Sufficient samples:** Run enough iterations to achieve statistical significance.
5. **Document everything:** Record all configurations, seeds, and parameters with each experiment.

## Statistical Analysis

For each experiment, report:

- Mean and standard deviation of success rates
- Confidence intervals (95%)
- Statistical significance tests (e.g., paired t-test, bootstrap)
- Effect sizes (e.g., Cohen's d)

## Current Status

All four experiments are defined but not yet executed. The infrastructure supports experiment creation, run tracking, and comparison. Execution requires:

1. A running Docker daemon for verification
2. An API-powered agent (MockAgent results are simulations)
3. Sufficient task templates and mutations for statistical power
