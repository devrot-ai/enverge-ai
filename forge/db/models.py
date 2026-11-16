"""SQLAlchemy database models for ForgeLab.

Provides persistent storage for worlds, tasks, runs, trajectories,
verification results, and failure diagnoses using SQLite.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

Base = declarative_base()

# Current schema version — increment when models change
SCHEMA_VERSION = "1.0"


class _SchemaMeta(Base):
    """Internal table to track database schema version."""

    __tablename__ = "_schema_meta"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class WorldRecord(Base):
    __tablename__ = "worlds"

    world_id = Column(String, primary_key=True)
    world_type = Column(String, nullable=False)
    template_name = Column(String, nullable=False)
    template_version = Column(String, default="0.1")
    mutation_id = Column(String, nullable=False)
    seed = Column(Integer, nullable=True)
    world_dir = Column(Text, nullable=True)
    initial_commit = Column(String, nullable=True)
    manifest = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "world_type": self.world_type,
            "template_name": self.template_name,
            "template_version": self.template_version,
            "mutation_id": self.mutation_id,
            "seed": self.seed,
            "world_dir": self.world_dir,
            "initial_commit": self.initial_commit,
            "manifest": json.loads(self.manifest) if self.manifest else None,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TaskRecord(Base):
    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True)
    world_id = Column(String, ForeignKey("worlds.world_id"), nullable=True)
    schema_version = Column(String, default="1.0")
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    constraints_json = Column(Text, nullable=True)
    verification_method = Column(String, nullable=True)
    difficulty_level = Column(Integer, default=1)
    capabilities_json = Column(Text, nullable=True)
    validated = Column(Integer, default=0)
    validation_notes = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "world_id": self.world_id,
            "schema_version": self.schema_version,
            "category": self.category,
            "description": self.description,
            "constraints": json.loads(self.constraints_json) if self.constraints_json else [],
            "verification_method": self.verification_method,
            "difficulty_level": self.difficulty_level,
            "capabilities": json.loads(self.capabilities_json) if self.capabilities_json else [],
            "validated": bool(self.validated),
            "validation_notes": self.validation_notes,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RunRecord(Base):
    __tablename__ = "runs"

    run_id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.task_id"), nullable=True)
    agent_id = Column(String, nullable=False)
    experiment_id = Column(String, nullable=True)
    status = Column(String, default="pending")
    trajectory_json = Column(Text, nullable=True)
    verification_json = Column(Text, nullable=True)
    diagnosis_json = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    agent_believes_success = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    step_count = Column(Integer, default=0)
    metadata_json = Column(Text, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "experiment_id": self.experiment_id,
            "status": self.status,
            "trajectory": json.loads(self.trajectory_json) if self.trajectory_json else None,
            "verification": json.loads(self.verification_json) if self.verification_json else None,
            "diagnosis": json.loads(self.diagnosis_json) if self.diagnosis_json else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "agent_believes_success": bool(self.agent_believes_success),
            "passed": bool(self.passed),
            "error": self.error,
            "step_count": self.step_count,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
        }


class CurriculumRecord(Base):
    __tablename__ = "curriculum_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    curriculum_id = Column(String, nullable=False, index=True)
    strategy = Column(String, default="static")
    capability_scores_json = Column(Text, nullable=True)
    task_pool_json = Column(Text, nullable=True)
    selected_tasks_json = Column(Text, nullable=True)
    generation = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "curriculum_id": self.curriculum_id,
            "strategy": self.strategy,
            "capability_scores": json.loads(self.capability_scores_json) if self.capability_scores_json else {},
            "task_pool": json.loads(self.task_pool_json) if self.task_pool_json else [],
            "selected_tasks": json.loads(self.selected_tasks_json) if self.selected_tasks_json else [],
            "generation": self.generation,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ExperimentRecord(Base):
    __tablename__ = "experiments"

    experiment_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    hypothesis = Column(Text, nullable=True)
    config_json = Column(Text, nullable=True)
    status = Column(String, default="created")
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    metadata_json = Column(Text, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "hypothesis": self.hypothesis,
            "config": json.loads(self.config_json) if self.config_json else {},
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
        }


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

_engine: Any | None = None
_session_factory: Any | None = None


def get_engine(db_path: str = "forgelab.db"):
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{db_path}", echo=False)
    return _engine


def get_session_factory(db_path: str = "forgelab.db"):
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine(db_path)
        _session_factory = sessionmaker(bind=engine)
    return _session_factory


def _get_schema_version(session: Session) -> str | None:
    """Read the stored schema version from the database."""
    result = session.query(_SchemaMeta).filter_by(key="schema_version").first()
    return result.value if result else None


def _set_schema_version(session: Session, version: str) -> None:
    """Write the schema version to the database."""
    existing = session.query(_SchemaMeta).filter_by(key="schema_version").first()
    if existing:
        existing.value = version
        session.commit()
    else:
        meta = _SchemaMeta(key="schema_version", value=version)
        try:
            session.add(meta)
            session.commit()
        except Exception:
            # Race condition: another process inserted it — rollback and update
            session.rollback()
            session.query(_SchemaMeta).filter_by(key="schema_version").update({"value": version})
            session.commit()


def check_schema(db_path: str = "forgelab.db") -> dict[str, Any]:
    """Check the database schema version against the expected version.

    Returns a dict with:
        - expected: the current code schema version
        - actual: the stored schema version (or None if new database)
        - up_to_date: whether the database matches the code
        - needs_migration: whether a migration is required
    """
    session = get_session(db_path)
    stored = _get_schema_version(session)
    session.close()

    return {
        "expected": SCHEMA_VERSION,
        "actual": stored,
        "up_to_date": stored == SCHEMA_VERSION,
        "needs_migration": stored is not None and stored != SCHEMA_VERSION,
    }


def migrate_db(db_path: str = "forgelab.db") -> bool:
    """Migrate the database to the latest schema version.

    For v0.1, migration means recreating tables if the schema version
    doesn't match. In future versions, this will use Alembic migrations.

    Returns True if migration was successful, False otherwise.
    """
    session = get_session(db_path)
    stored = _get_schema_version(session)

    if stored == SCHEMA_VERSION:
        session.close()
        return True  # Already up to date

    if stored is None:
        # New database — just create tables and set version
        engine = get_engine(db_path)
        Base.metadata.create_all(engine)
        _set_schema_version(session, SCHEMA_VERSION)
        session.close()
        return True
    else:
        # Schema mismatch — for v0.1, recreate all tables
        # WARNING: This drops all data. Future versions will use Alembic.
        engine = get_engine(db_path)
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        _set_schema_version(session, SCHEMA_VERSION)
        session.close()
        return True


def init_db(db_path: str = "forgelab.db") -> Session:
    """Initialize the database, creating all tables and setting schema version.

    Returns a session.
    """
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    factory = get_session_factory(db_path)
    session = factory()
    _set_schema_version(session, SCHEMA_VERSION)
    return session


def get_session(db_path: str = "forgelab.db") -> Session:
    """Get a new database session."""
    factory = get_session_factory(db_path)
    return factory()
