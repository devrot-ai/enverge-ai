"""Catch-all route for /api/* paths on Vercel.

This file handles any path under /api/ that doesn't match a specific file.
Vercel uses [...path].py as a catch-all route pattern.
"""

# Re-export the handler from index.py
from api.index import handler  # noqa: F401
