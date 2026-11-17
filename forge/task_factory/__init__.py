"""Task factory module — structured task generation and management.

Provides:
- TaskGenerator for creating TaskSpec from world specs
- Bug mutations (pagination_boundary, empty_search, duplicate_records, etc.)
- Difficulty estimation based on task characteristics
- Task pool selection and management
- LLMTaskGenerator for LLM-assisted task generation
"""

__version__ = "0.1.0"

from forge.task_factory.difficulty import adjust_task_difficulty, estimate_task_difficulty, get_difficulty_label
from forge.task_factory.generator import TaskGenerator
from forge.task_factory.mutations import (
    BugMutation,
    get_all_mutations,
    get_mutation,
    get_mutations_by_capability,
    get_mutations_by_difficulty,
)
from forge.task_factory.selection import TaskPool

# Optional imports — available when openai is installed
try:
    from forge.task_factory.llm_generator import (
        GeneratedTask,
        LLMTaskGenerator,
    )
except ImportError:
    GeneratedTask = None  # type: ignore[misc,assignment]
    LLMTaskGenerator = None  # type: ignore[misc,assignment]

__all__ = [
    "TaskGenerator",
    "BugMutation",
    "get_all_mutations",
    "get_mutation",
    "get_mutations_by_capability",
    "get_mutations_by_difficulty",
    "estimate_task_difficulty",
    "adjust_task_difficulty",
    "get_difficulty_label",
    "TaskPool",
    "GeneratedTask",
    "LLMTaskGenerator",
]
