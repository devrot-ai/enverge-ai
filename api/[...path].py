"""Catch-all route for /api/* paths on Vercel.

Delegates all requests to the main handler in index.py.
"""

from api.index import handler  # noqa: F401
