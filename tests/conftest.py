"""Pytest configuration for ForgeLab test suite."""

import pytest


def pytest_configure(config):
    """Set asyncio mode for pytest-asyncio compatibility.

    Newer versions of pytest-asyncio (>=0.21) use a hook instead of
    the deprecated asyncio_mode ini option.
    """
    # pytest-asyncio >= 0.21 uses this hook for auto mode
    try:
        # Register the default loop fixture for auto mode
        if not hasattr(config, "_asyncio_mode"):
            config._asyncio_mode = "auto"
    except Exception:
        pass


@pytest.fixture
def event_loop_policy():
    """Provide a default event loop policy for async tests."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()
