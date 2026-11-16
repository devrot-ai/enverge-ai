"""API module — FastAPI REST backend for ForgeLab.

Provides 26 REST routes for worlds, tasks, runs, curriculum,
experiments, and metrics with SQLAlchemy SQLite persistence.
"""

__version__ = "0.1.0"

from forge.api.app import app

__all__ = ["app"]
