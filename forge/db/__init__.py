"""Database module — SQLAlchemy models and persistence layer.

Provides ORM models for worlds, tasks, runs, trajectories,
verification results, failure diagnoses, curriculum states, and experiments.
"""

__version__ = "0.1.0"

from forge.db.models import (
    SCHEMA_VERSION,
    CurriculumRecord,
    ExperimentRecord,
    RunRecord,
    TaskRecord,
    WorldRecord,
    check_schema,
    get_engine,
    get_session,
    get_session_factory,
    init_db,
    migrate_db,
)

__all__ = [
    "WorldRecord",
    "TaskRecord",
    "RunRecord",
    "CurriculumRecord",
    "ExperimentRecord",
    "get_engine",
    "get_session_factory",
    "init_db",
    "get_session",
    "check_schema",
    "migrate_db",
    "SCHEMA_VERSION",
]
