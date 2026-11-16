"""Curriculum module — adaptive task selection and capability tracking.

Provides:
- CapabilityTracker for per-capability performance estimates
- CurriculumSelector with static/random/adaptive strategies
- Difficulty estimation and adjustment
- Curriculum state updates based on verified outcomes
- Curriculum decision history logging
"""

__version__ = "0.1.0"

from forge.curriculum.capability_tracker import CapabilityRecord, CapabilityTracker
from forge.curriculum.difficulty import (
    adjust_difficulty,
    compute_task_complexity,
    estimate_difficulty,
    get_difficulty_distribution,
    get_difficulty_label,
)
from forge.curriculum.history import CurriculumDecision, CurriculumHistory
from forge.curriculum.selector import CurriculumSelector
from forge.curriculum.updater import CurriculumUpdater
from forge.curriculum.autoscale import AutoScaler, DifficultyAdjustment
from forge.curriculum.multi_agent import (
    MultiAgentCurriculum,
    AgentCurriculumState,
    SharingLevel,
)

__all__ = [
    "CurriculumSelector",
    "CapabilityRecord",
    "CapabilityTracker",
    "estimate_difficulty",
    "adjust_difficulty",
    "compute_task_complexity",
    "get_difficulty_label",
    "get_difficulty_distribution",
    "CurriculumUpdater",
    "CurriculumDecision",
    "CurriculumHistory",
    "AutoScaler",
    "DifficultyAdjustment",
    "MultiAgentCurriculum",
    "AgentCurriculumState",
    "SharingLevel",
]
