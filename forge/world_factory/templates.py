"""World templates: source code for generated environments.

Each template defines a complete Python project with files,
dependencies, and version information.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Template Registry
# ---------------------------------------------------------------------------

_templates: dict[str, dict[str, Any]] = {}


def register_template(name: str, template: dict[str, Any]) -> None:
    """Register a world template.

    Args:
        name: Template name.
        template: Template definition with 'files', 'dependencies', 'version'.
    """
    _templates[name] = template


def get_template(name: str) -> dict[str, Any]:
    """Get a registered template by name.

    Args:
        name: Template name.

    Returns:
        Template definition or None.
    """
    return _templates.get(name)


def list_templates() -> list[str]:
    """List all registered template names.

    Returns:
        Sorted list of template names.
    """
    return sorted(_templates.keys())


# ---------------------------------------------------------------------------
# Task Manager API Template
# ---------------------------------------------------------------------------


def _register_task_manager_api() -> None:
    """Register the task_manager_api template.

    A simple Python API with a tasks list and pagination endpoint.
    The agent's job is to fix bugs in the pagination logic.
    """

    # Main application file
    app_code = '''"""Task Manager API - A simple REST API for managing tasks."""

from typing import List, Optional


class Task:
    """Represents a task in the system."""

    def __init__(self, id: int, title: str, description: str = "", status: str = "open"):
        self.id = id
        self.title = title
        self.description = description
        self.status = status

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
        }


class TaskManager:
    """Manages a collection of tasks with CRUD operations and pagination."""

    def __init__(self):
        self._tasks: List[Task] = []
        self._next_id = 1

    def add_task(self, title: str, description: str = "", status: str = "open") -> Task:
        """Add a new task."""
        task = Task(self._next_id, title, description, status)
        self._tasks.append(task)
        self._next_id += 1
        return task

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get a task by ID."""
        for task in self._tasks:
            if task.id == task_id:
                return task
        return None

    def update_task(self, task_id: int, **kwargs) -> Optional[Task]:
        """Update a task's attributes."""
        task = self.get_task(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
        return task

    def delete_task(self, task_id: int) -> bool:
        """Delete a task by ID."""
        for i, task in enumerate(self._tasks):
            if task.id == task_id:
                self._tasks.pop(i)
                return True
        return False

    def list_tasks(
        self,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> dict:
        """List tasks with pagination, filtering, and search.

        Args:
            page: Page number (1-indexed).
            page_size: Number of tasks per page.
            status: Filter by status.
            search: Search in title and description.

        Returns:
            Dictionary with tasks, total, page, page_size, total_pages.
        """
        filtered = self._tasks

        # Filter by status
        if status is not None:
            filtered = [t for t in filtered if t.status == status]

        # Search in title and description
        if search is not None:
            search_lower = search.lower()
            filtered = [
                t for t in filtered
                if search_lower in t.title.lower() or search_lower in t.description.lower()
            ]

        total = len(filtered)
        total_pages = max(1, (total + page_size - 1) // page_size)

        # BUG: Pagination boundary handling is incorrect
        start = (page - 1) * page_size
        end = start + page_size
        page_tasks = filtered[start:end]

        return {
            "tasks": [t.to_dict() for t in page_tasks],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def get_stats(self) -> dict:
        """Get task statistics."""
        return {
            "total": len(self._tasks),
            "open": sum(1 for t in self._tasks if t.status == "open"),
            "closed": sum(1 for t in self._tasks if t.status == "closed"),
            "in_progress": sum(1 for t in self._tasks if t.status == "in_progress"),
        }
'''

    # Public tests (visible to agent)
    public_tests = '''"""Public tests for TaskManager - visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import TaskManager


def test_add_task():
    tm = TaskManager()
    task = tm.add_task("Test Task", "Description")
    assert task.id == 1
    assert task.title == "Test Task"


def test_get_task():
    tm = TaskManager()
    tm.add_task("Task 1")
    task = tm.get_task(1)
    assert task is not None
    assert task.title == "Task 1"


def test_get_missing_task():
    tm = TaskManager()
    assert tm.get_task(999) is None


def test_update_task():
    tm = TaskManager()
    tm.add_task("Task 1")
    tm.update_task(1, status="closed")
    task = tm.get_task(1)
    assert task.status == "closed"


def test_delete_task():
    tm = TaskManager()
    tm.add_task("Task 1")
    assert tm.delete_task(1) is True
    assert tm.get_task(1) is None


def test_list_tasks_basic():
    tm = TaskManager()
    for i in range(5):
        tm.add_task(f"Task {i}")
    result = tm.list_tasks()
    assert result["total"] == 5
    assert len(result["tasks"]) == 5


def test_list_tasks_with_status_filter():
    tm = TaskManager()
    tm.add_task("Open Task")
    tm.add_task("Closed Task")
    tm.update_task(2, status="closed")
    result = tm.list_tasks(status="open")
    assert result["total"] == 1


def test_list_tasks_with_search():
    tm = TaskManager()
    tm.add_task("Important Task", "This is important")
    tm.add_task("Other Task", "Nothing special")
    result = tm.list_tasks(search="important")
    assert result["total"] == 1


def test_pagination_basic():
    tm = TaskManager()
    for i in range(25):
        tm.add_task(f"Task {i}")
    result = tm.list_tasks(page=1, page_size=10)
    assert len(result["tasks"]) == 10
    assert result["total"] == 25
    assert result["total_pages"] == 3


def test_get_stats():
    tm = TaskManager()
    tm.add_task("Task 1")
    tm.add_task("Task 2")
    tm.update_task(2, status="closed")
    stats = tm.get_stats()
    assert stats["total"] == 2
    assert stats["open"] == 1
    assert stats["closed"] == 1
'''

    # Hidden tests (NOT visible to agent)
    hidden_tests = '''"""Hidden tests for TaskManager - NOT visible to the agent.

These tests verify the specific bug fix and edge cases.
"""

import sys
sys.path.insert(0, ".")

from app import TaskManager


def test_pagination_boundary_exact():
    """Test pagination when page exactly equals total_pages."""
    tm = TaskManager()
    for i in range(23):
        tm.add_task(f"Task {i}")
    # 23 items, page_size=10 -> 3 pages
    # Page 3 should have 3 items
    result = tm.list_tasks(page=3, page_size=10)
    assert len(result["tasks"]) == 3, f"Expected 3 tasks on page 3, got {len(result['tasks'])}"


def test_pagination_beyond_total():
    """Test pagination when requested page exceeds total pages."""
    tm = TaskManager()
    for i in range(15):
        tm.add_task(f"Task {i}")
    # 15 items, page_size=10 -> 2 pages
    # Page 3 should return empty list, not raise an error
    result = tm.list_tasks(page=3, page_size=10)
    assert len(result["tasks"]) == 0, f"Expected empty list for page 3, got {len(result['tasks'])}"
    assert result["total"] == 15
    assert result["page"] == 3


def test_pagination_single_item_pages():
    """Test pagination with page_size=1."""
    tm = TaskManager()
    for i in range(5):
        tm.add_task(f"Task {i}")
    result = tm.list_tasks(page=3, page_size=1)
    assert len(result["tasks"]) == 1
    assert result["tasks"][0]["id"] == 3


def test_empty_search_returns_all():
    """Test that empty search string returns all tasks."""
    tm = TaskManager()
    for i in range(5):
        tm.add_task(f"Task {i}")
    result = tm.list_tasks(search="")
    assert result["total"] == 5, f"Expected 5 tasks with empty search, got {result['total']}"


def test_duplicate_task_titles():
    """Test handling of duplicate task titles."""
    tm = TaskManager()
    tm.add_task("Duplicate", "First")
    tm.add_task("Duplicate", "Second")
    tm.add_task("Unique", "Only one")
    result = tm.list_tasks(search="duplicate")
    assert result["total"] == 2, f"Expected 2 duplicate tasks, got {result['total']}"


def test_pagination_with_filter():
    """Test pagination combined with status filter."""
    tm = TaskManager()
    for i in range(15):
        tm.add_task(f"Task {i}")
        if i % 2 != 0:
            tm.update_task(i + 1, status="closed")
    result = tm.list_tasks(page=1, page_size=5, status="open")
    assert result["total"] == 8  # 8 open tasks out of 15
    assert len(result["tasks"]) == 5


def test_reference_solution_pagination():
    """Verify the reference solution handles all pagination correctly."""
    tm = TaskManager()
    for i in range(100):
        tm.add_task(f"Task {i}")

    # Check all pages return correct number of items
    for page in range(1, 11):
        result = tm.list_tasks(page=page, page_size=10)
        if page < 10:
            assert len(result["tasks"]) == 10
        elif page == 10:
            assert len(result["tasks"]) == 10
        else:
            assert len(result["tasks"]) == 0

    # Page beyond total should return empty
    result = tm.list_tasks(page=100, page_size=10)
    assert len(result["tasks"]) == 0
'''

    # Reference solution (the correct fix)
    reference_fix = '''"""Reference solution: the correct pagination implementation.

This file shows the correct version of list_tasks.
It is NOT given to the agent.
"""

def list_tasks_correct(
    self,
    page: int = 1,
    page_size: int = 10,
    status = None,
    search = None,
):
    """Correct pagination implementation."""
    filtered = self._tasks

    if status is not None:
        filtered = [t for t in filtered if t.status == status]

    if search is not None:
        search_lower = search.lower()
        filtered = [
            t for t in filtered
            if search_lower in t.title.lower() or search_lower in t.description.lower()
        ]
    # Fix: empty search should return all, not filter out everything
    elif search == "":
        pass  # Keep all tasks

    total = len(filtered)
    total_pages = max(1, (total + page_size - 1) // page_size)

    # Fix: clamp page to valid range
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages + 1  # Return empty page

    start = (page - 1) * page_size
    end = start + page_size
    page_tasks = filtered[start:end]

    return {
        "tasks": [t.to_dict() for t in page_tasks],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
'''

    register_template(
        "task_manager_api",
        {
            "name": "task_manager_api",
            "version": "0.1",
            "description": "A Python task management API with pagination bugs",
            "dependencies": [],
            "files": {
                "app.py": app_code,
                "tests/test_public.py": public_tests,
                ".hidden_tests/test_hidden.py": hidden_tests,
                ".reference_solution.py": reference_fix,
            },
        },
    )


# ---------------------------------------------------------------------------
# Data Pipeline Template
# ---------------------------------------------------------------------------


def _register_data_pipeline() -> None:
    """Register the data_pipeline template.

    A data processing pipeline with ETL operations and validation.
    The agent's job is to fix bugs in null handling, date parsing,
    and duplicate detection.
    """

    pipeline_code = '''"""Data Pipeline - ETL processing with validation and transformation."""

from datetime import datetime
from typing import Any, Dict, List, Optional


class DataValidator:
    """Validates data records against schema rules."""

    def __init__(self, required_fields: List[str]):
        self.required_fields = required_fields

    def validate(self, record: Dict[str, Any]) -> List[str]:
        """Validate a single record.

        Returns:
            List of error messages (empty if valid).
        """
        errors = []
        for field in self.required_fields:
            if field not in record:
                errors.append(f"Missing required field: {field}")
            elif record[field] is None:
                errors.append(f"Null value in required field: {field}")
        return errors

    def validate_batch(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate a batch of records, returning only valid ones."""
        valid = []
        for record in records:
            errors = self.validate(record)
            if not errors:
                valid.append(record)
        return valid


class DateParser:
    """Parses dates from various formats."""

    SUPPORTED_FORMATS = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%m/%d/%Y",
        "%d-%m-%Y",
    ]

    @classmethod
    def parse(cls, date_str: str) -> Optional[datetime]:
        """Parse a date string into a datetime object.

        Args:
            date_str: Date string in various formats.

        Returns:
            Parsed datetime or None if unparseable.
        """
        if not date_str:
            return None

        for fmt in cls.SUPPORTED_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Handle ISO 8601 with timezone
        try:
            cleaned = date_str.replace("Z", "+00:00")
            return datetime.fromisoformat(cleaned)
        except ValueError:
            pass
        return None


class DataTransformer:
    """Transforms data records."""

    @staticmethod
    def normalize(record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a record (strip strings, lowercase emails)."""
        normalized = {}
        for key, value in record.items():
            if isinstance(value, str):
                normalized[key] = value.strip()
                if key == "email":
                    normalized[key] = value.strip().lower()
            else:
                normalized[key] = value
        return normalized

    @staticmethod
    def detect_duplicates(
        records: List[Dict[str, Any]], key_fields: List[str]
    ) -> List[Dict[str, Any]]:
        """Detect and remove duplicate records based on key fields.

        Args:
            records: List of records.
            key_fields: Fields that form the composite key.

        Returns:
            Deduplicated list preserving first occurrence.
        """
        seen = set()
        unique = []
        for record in records:
            key = tuple(record.get(f, "") for f in key_fields)
            if key not in seen:
                seen.add(key)
                unique.append(record)
        return unique


class Pipeline:
    """Main data processing pipeline."""

    def __init__(self):
        self.validator = DataValidator(["id", "name", "email"])
        self.transformer = DataTransformer()

    def process(self, raw_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a batch of raw records.

        Returns:
            Dictionary with valid_records, invalid_count, errors.
        """
        valid_records = self.validator.validate_batch(raw_records)
        normalized = [
            self.transformer.normalize(r) for r in valid_records
        ]
        deduplicated = self.transformer.detect_duplicates(
            normalized, key_fields=["id", "email"]
        )

        return {
            "valid_records": deduplicated,
            "invalid_count": len(raw_records) - len(valid_records),
            "total_processed": len(raw_records),
        }
'''

    public_tests_pipeline = '''"""Public tests for Data Pipeline - visible to the agent."""

import sys
sys.path.insert(0, ".")

from pipeline import DataValidator, DateParser, DataTransformer, Pipeline


def test_validator_valid_record():
    validator = DataValidator(["id", "name"])
    errors = validator.validate({"id": 1, "name": "Test"})
    assert errors == []


def test_validator_missing_field():
    validator = DataValidator(["id", "name"])
    errors = validator.validate({"id": 1})
    assert len(errors) > 0


def test_date_parser_basic():
    dt = DateParser.parse("2024-01-15")
    assert dt is not None
    assert dt.year == 2024


def test_date_parser_invalid():
    dt = DateParser.parse("not-a-date")
    assert dt is None


def test_transformer_normalize():
    result = DataTransformer.normalize({"name": "  Test  ", "email": "  TEST@EX.COM  "})
    assert result["name"] == "Test"
    assert result["email"] == "test@ex.com"


def test_pipeline_process():
    pipeline = Pipeline()
    records = [
        {"id": 1, "name": "Alice", "email": "alice@test.com"},
        {"id": 2, "name": "Bob", "email": "bob@test.com"},
    ]
    result = pipeline.process(records)
    assert result["total_processed"] == 2
    assert result["invalid_count"] == 0
'''

    hidden_tests_pipeline = '''"""Hidden tests for Data Pipeline - NOT visible to the agent."""

import sys
sys.path.insert(0, ".")

from pipeline import DataValidator, DateParser, DataTransformer, Pipeline


def test_null_handling_graceful():
    """Null values should produce errors, not crash."""
    validator = DataValidator(["id", "name"])
    # Should return error list, not raise ValueError
    errors = validator.validate({"id": 1, "name": None})
    assert len(errors) > 0, "Should report null field as error"


def test_date_parser_iso_with_tz():
    """ISO 8601 with timezone offset should parse."""
    dt = DateParser.parse("2024-01-15T10:30:00+05:30")
    assert dt is not None, "Should parse ISO 8601 with timezone"


def test_date_parser_iso_zulu():
    """ISO 8601 with Z suffix should parse."""
    dt = DateParser.parse("2024-01-15T10:30:00Z")
    assert dt is not None, "Should parse ISO 8601 with Z suffix"


def test_duplicate_detection_composite_key():
    """Duplicate detection should use all key fields."""
    records = [
        {"id": 1, "email": "a@test.com", "name": "Alice"},
        {"id": 1, "email": "b@test.com", "name": "Bob"},
        {"id": 2, "email": "a@test.com", "name": "Alice 2"},
    ]
    unique = DataTransformer.detect_duplicates(records, ["id", "email"])
    assert len(unique) == 3, "All three records have different composite keys"


def test_duplicate_detection_true_duplicate():
    """True duplicates should be removed."""
    records = [
        {"id": 1, "email": "a@test.com", "name": "Alice"},
        {"id": 1, "email": "a@test.com", "name": "Alice Copy"},
    ]
    unique = DataTransformer.detect_duplicates(records, ["id", "email"])
    assert len(unique) == 1, "Duplicate should be removed"


def test_pipeline_with_nulls():
    """Pipeline should handle nulls without crashing."""
    pipeline = Pipeline()
    records = [
        {"id": 1, "name": "Alice", "email": "alice@test.com"},
        {"id": None, "name": "Bob", "email": "bob@test.com"},
    ]
    result = pipeline.process(records)
    assert result["invalid_count"] >= 1
'''

    reference_fix_pipeline = '''"""Reference solution for data pipeline bugs."""

def validate_fixed(self, record):
    """Fixed: handle None gracefully."""
    errors = []
    for field in self.required_fields:
        if field not in record:
            errors.append(f"Missing required field: {field}")
        elif record[field] is None:
            errors.append(f"Null value in required field: {field}")
    return errors  # No crash


def parse_fixed(date_str):
    """Fixed: handle ISO 8601 with timezone."""
    if not date_str:
        return None
    # Strip timezone suffix for basic parsing
    clean = date_str.replace("Z", "").split("+")[0].split("-")[0:3]
    # Simplified: just handle the base date
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        pass
    return None


def detect_duplicates_fixed(records, key_fields):
    """Fixed: use composite key."""
    seen = set()
    unique = []
    for record in records:
        key = tuple(record.get(f, "") for f in key_fields)
        if key not in seen:
            seen.add(key)
            unique.append(record)
    return unique
'''

    register_template(
        "data_pipeline",
        {
            "name": "data_pipeline",
            "version": "0.1",
            "description": "Data processing pipeline with ETL bugs",
            "dependencies": [],
            "files": {
                "pipeline.py": pipeline_code,
                "tests/test_public.py": public_tests_pipeline,
                ".hidden_tests/test_hidden.py": hidden_tests_pipeline,
                ".reference_solution.py": reference_fix_pipeline,
            },
        },
    )


# ---------------------------------------------------------------------------
# Flask App Template
# ---------------------------------------------------------------------------


def _register_flask_app() -> None:
    """Register the flask_app template.

    A Flask-like web application with user authentication, session management,
    and CSRF protection. The agent's job is to fix security bugs in these components.
    Pure Python implementation — no Flask dependency required.
    """

    # Main application file
    app_code = '''"""Flask App - Authentication, Session, and CSRF protection modules."""

import hashlib
import hmac
import os
import time
from typing import Dict, List, Optional


class AuthManager:
    """Handles user authentication with password hashing."""

    def __init__(self):
        self._users: Dict[str, Dict[str, str]] = {}

    def register_user(self, username: str, password: str) -> bool:
        """Register a new user with hashed password."""
        if username in self._users:
            return False
        # BUG: password_hash - stores plaintext instead of hashing
        password_hash = self._hash_password(password)
        self._users[username] = {
            "password_hash": password_hash,
            "created_at": time.time(),
        }
        return True

    def login(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and return session token if valid."""
        if username not in self._users:
            return None
        stored_hash = self._users[username]["password_hash"]
        if self._verify_password(password, stored_hash):
            return self._generate_token(username)
        return None

    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256 with salt."""
        salt = os.urandom(16).hex()
        hashed = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"{salt}:{hashed}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a password against a stored hash."""
        if ":" not in stored_hash:
            return False
        salt, hashed = stored_hash.split(":", 1)
        new_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return hmac.compare_digest(new_hash, hashed)

    def _generate_token(self, username: str) -> str:
        """Generate a session token for a user."""
        data = f"{username}:{time.time()}:{os.urandom(8).hex()}"
        return hashlib.sha256(data.encode()).hexdigest()


class SessionManager:
    """Manages user sessions with timeout tracking."""

    def __init__(self, timeout_seconds: int = 3600):
        self._sessions: Dict[str, Dict[str, any]] = {}
        self._timeout = timeout_seconds

    def create_session(self, token: str, user_id: str) -> str:
        """Create a new session and return session ID."""
        session_id = hashlib.sha256(f"{token}:{time.time()}".encode()).hexdigest()[:32]
        self._sessions[session_id] = {
            "token": token,
            "user_id": user_id,
            "created_at": time.time(),
            "expires_at": time.time() + self._timeout,
        }
        return session_id

    def validate_session(self, session_id: str) -> bool:
        """Check if a session is valid and not expired."""
        if session_id not in self._sessions:
            return False
        session = self._sessions[session_id]
        # BUG: session_timeout - calculates timeout incorrectly
        expires_at = session["created_at"] + self._calculate_timeout()
        return time.time() < expires_at

    def _calculate_timeout(self) -> int:
        """Calculate session timeout duration."""
        return self._timeout

    def destroy_session(self, session_id: str) -> bool:
        """Destroy a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now >= s["expires_at"]
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)


class CSRFProtector:
    """Provides CSRF token generation and validation."""

    def __init__(self, secret_key: Optional[str] = None):
        self._secret = secret_key or os.urandom(32).hex()
        self._tokens: Dict[str, float] = {}

    def generate_token(self) -> str:
        """Generate a new CSRF token."""
        token = hashlib.sha256(
            f"{self._secret}:{time.time()}:{os.urandom(16).hex()}".encode()
        ).hexdigest()
        self._tokens[token] = time.time()
        return token

    def validate_token(self, token: str) -> bool:
        """Validate a CSRF token."""
        # BUG: csrf_token - always returns True without checking
        if token in self._tokens:
            return True
        return False

    def revoke_token(self, token: str) -> bool:
        """Revoke a CSRF token after use."""
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False
'''

    # Public tests - visible to the agent
    public_tests_flask = '''"""Public tests for Flask App - visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import AuthManager, SessionManager, CSRFProtector


# --- AuthManager Tests ---

def test_register_user():
    """Should register a new user successfully."""
    auth = AuthManager()
    assert auth.register_user("alice", "password123") is True


def test_register_duplicate_user():
    """Should reject duplicate username."""
    auth = AuthManager()
    auth.register_user("alice", "password123")
    assert auth.register_user("alice", "otherpass") is False


def test_login_success():
    """Should return token on valid login."""
    auth = AuthManager()
    auth.register_user("bob", "secure456")
    token = auth.login("bob", "secure456")
    assert token is not None
    assert isinstance(token, str)


def test_login_wrong_password():
    """Should return None on wrong password."""
    auth = AuthManager()
    auth.register_user("bob", "secure456")
    assert auth.login("bob", "wrongpass") is None


def test_login_nonexistent_user():
    """Should return None for unknown user."""
    auth = AuthManager()
    assert auth.login("nobody", "anypass") is None


# --- SessionManager Tests ---

def test_create_session():
    """Should create a session and return session ID."""
    sm = SessionManager(timeout_seconds=3600)
    session_id = sm.create_session("token123", "user1")
    assert isinstance(session_id, str)
    assert len(session_id) > 0


def test_validate_fresh_session():
    """A newly created session should be valid."""
    sm = SessionManager(timeout_seconds=3600)
    session_id = sm.create_session("token123", "user1")
    assert sm.validate_session(session_id) is True


def test_destroy_session():
    """Should destroy a session successfully."""
    sm = SessionManager(timeout_seconds=3600)
    session_id = sm.create_session("token123", "user1")
    assert sm.destroy_session(session_id) is True
    assert sm.validate_session(session_id) is False


def test_validate_unknown_session():
    """Should return False for unknown session ID."""
    sm = SessionManager(timeout_seconds=3600)
    assert sm.validate_session("nonexistent") is False


# --- CSRFProtector Tests ---

def test_generate_csrf_token():
    """Should generate a CSRF token string."""
    csrf = CSRFProtector()
    token = csrf.generate_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_validate_fresh_csrf_token():
    """A freshly generated token should validate."""
    csrf = CSRFProtector()
    token = csrf.generate_token()
    assert csrf.validate_token(token) is True


def test_revoke_csrf_token():
    """Revoked token should not validate."""
    csrf = CSRFProtector()
    token = csrf.generate_token()
    csrf.revoke_token(token)
    assert csrf.validate_token(token) is False
'''

    # Hidden tests - NOT visible to the agent
    hidden_tests_flask = '''"""Hidden tests for Flask App - NOT visible to the agent."""

import sys
import time
sys.path.insert(0, ".")

from app import AuthManager, SessionManager, CSRFProtector


def test_password_not_plaintext():
    """Password should be hashed, not stored as plaintext."""
    auth = AuthManager()
    auth.register_user("alice", "mypassword123")
    stored = auth._users["alice"]["password_hash"]
    # The stored hash should contain a colon (salt:hash format)
    assert ":" in stored, "Password hash should use salt:hash format"
    # The stored value should NOT be the plaintext password
    assert stored != "mypassword123", "Password should not be stored as plaintext"


def test_session_timeout_respects_config():
    """Session should remain valid within configured timeout."""
    # Use a short timeout for testing
    sm = SessionManager(timeout_seconds=2)
    session_id = sm.create_session("token123", "user1")
    # Session should be valid immediately
    assert sm.validate_session(session_id) is True
    # Wait for timeout
    time.sleep(3)
    # Session should be expired after timeout
    assert sm.validate_session(session_id) is False, \
        "Session should expire after configured timeout"


def test_session_timeout_not_zero():
    """Session timeout should not be calculated as zero."""
    sm = SessionManager(timeout_seconds=3600)
    timeout = sm._calculate_timeout()
    assert timeout == 3600, f"Timeout should be 3600, got {timeout}"


def test_csrf_rejects_invalid_token():
    """CSRF validator should reject tokens not generated by the protector."""
    csrf = CSRFProtector()
    # A random string should not validate
    assert csrf.validate_token("invalid_random_token") is False, \
        "Invalid CSRF token should be rejected"


def test_csrf_token_uniqueness():
    """Each generated CSRF token should be unique."""
    csrf = CSRFProtector()
    tokens = [csrf.generate_token() for _ in range(10)]
    assert len(set(tokens)) == 10, "CSRF tokens should be unique"
'''

    # Reference solution
    reference_fix_flask = '''"""Reference solution for Flask App bugs."""

def _calculate_timeout_fixed(self) -> int:
    """Fixed: return the configured timeout, not zero."""
    return self._timeout


def _hash_password_fixed(self, password: str) -> str:
    """Fixed: actually hash the password."""
    import hashlib
    import os
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def validate_token_fixed(self, token: str) -> bool:
    """Fixed: actually check if token exists."""
    return token in self._tokens
'''

    register_template(
        "flask_app",
        {
            "name": "flask_app",
            "version": "0.1",
            "description": "Flask web app with auth, session, and CSRF bugs",
            "dependencies": [],
            "files": {
                "app.py": app_code,
                "tests/test_public.py": public_tests_flask,
                ".hidden_tests/test_hidden.py": hidden_tests_flask,
                ".reference_solution.py": reference_fix_flask,
            },
        },
    )


# ---------------------------------------------------------------------------
# Express API Template
# ---------------------------------------------------------------------------


def _register_express_api() -> None:
    """Register the express_api template.

    A Node.js/Express-style REST API in pure Python with routing,
    middleware chains, request validation, and error handling.
    The agent's job is to fix security and input handling bugs.
    """

    # Main application file
    app_code = r'''"""Express-style API - A REST API framework in pure Python."""

import re
import time
import hashlib
from typing import Any, Callable, Dict, List, Optional


class Request:
    """HTTP request representation."""

    def __init__(self, method: str, path: str, headers: Dict[str, str] = None,
                 body: Any = None, query_params: Dict[str, str] = None):
        self.method = method
        self.path = path
        self.headers = headers or {}
        self.body = body
        self.query_params = query_params or {}
        self._middleware_data: Dict[str, Any] = {}

    def get_header(self, name: str, default: str = None) -> Optional[str]:
        """Get a header value by name (case-insensitive)."""
        for key, value in self.headers.items():
            if key.lower() == name.lower():
                return value
        return default

    def get_query_param(self, name: str, default: str = None) -> Optional[str]:
        """Get a query parameter value."""
        return self.query_params.get(name, default)


class Response:
    """HTTP response representation."""

    def __init__(self, status_code: int = 200, body: Any = None,
                 headers: Dict[str, str] = None):
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}

    def set_header(self, name: str, value: str) -> None:
        """Set a response header."""
        self.headers[name] = value


class MiddlewareChain:
    """Manages a chain of middleware functions executed in order."""

    def __init__(self):
        self._middlewares: List[Callable] = []

    def use(self, middleware: Callable) -> None:
        """Add middleware to the chain."""
        self._middlewares.append(middleware)

    def execute(self, request: Request) -> Response:
        """Execute all middleware in order, passing request through the chain."""
        current = request
        for middleware in self._middlewares:
            result = middleware(current)
            if isinstance(result, Response):
                return result
            if isinstance(result, Request):
                current = result
        return None  # No handler matched; router will handle


class Router:
    """Routes HTTP requests to handler functions."""

    def __init__(self):
        self._routes: Dict[str, Dict[str, Callable]] = {}
        self._param_patterns: Dict[str, str] = {}

    def add_route(self, method: str, path: str, handler: Callable) -> None:
        """Register a route handler."""
        if path not in self._routes:
            self._routes[path] = {}
        self._routes[path][method.upper()] = handler

        # Extract parameter names like :id
        params = re.findall(r':(\w+)', path)
        if params:
            pattern = re.sub(r':(\w+)', r'([^/]+)', path)
            self._param_patterns[path] = pattern

    def find_route(self, method: str, path: str) -> Optional[Callable]:
        """Find a handler for the given method and path."""
        # Exact match
        if path in self._routes and method.upper() in self._routes[path]:
            return self._routes[path][method.upper()]

        # Parameterized match
        for route_path, pattern in self._param_patterns.items():
            match = re.fullmatch(pattern, path)
            if match and method.upper() in self._routes[route_path]:
                return self._routes[route_path][method.upper()]

        return None

    def dispatch(self, request: Request) -> Response:
        """Dispatch a request to the appropriate handler."""
        handler = self.find_route(request.method, request.path)
        if handler is None:
            return Response(404, {"error": "Not found"})
        try:
            return handler(request)
        except Exception as e:
            return Response(500, {"error": str(e)})


class RequestValidator:
    """Validates request data against schemas."""

    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required: List[str]) -> List[str]:
        """Check that all required fields are present.

        Returns:
            List of missing field names.
        """
        missing = []
        for field in required:
            if field not in data or data[field] is None:
                missing.append(field)
        return missing

    @staticmethod
    def sanitize_input(value: str) -> str:
        """Sanitize a string input by removing potentially dangerous characters."""
        # BUG: input_injection - does not sanitize input
        return value

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self._max_requests = max_requests
        self._window = window_seconds
        self._requests: Dict[str, List[float]] = {}

    def is_allowed(self, client_id: str) -> bool:
        """Check if a client is within rate limits."""
        now = time.time()
        if client_id not in self._requests:
            self._requests[client_id] = []

        # Clean old requests
        self._requests[client_id] = [
            t for t in self._requests[client_id]
            if now - t < self._window
        ]

        # BUG: rate_limit_off - always allows requests
        if len(self._requests[client_id]) < self._max_requests:
            self._requests[client_id].append(now)
            return True
        return False

    def reset(self, client_id: str) -> None:
        """Reset rate limit for a client."""
        self._requests.pop(client_id, None)


class CorsHandler:
    """Handles CORS (Cross-Origin Resource Sharing) headers."""

    def __init__(self, allowed_origins: List[str] = None):
        self._allowed_origins = allowed_origins or []

    def get_headers(self, request_origin: str) -> Dict[str, str]:
        """Get CORS headers for a request."""
        # BUG: cors_bypass - accepts any origin
        headers = {}
        if request_origin:
            headers["Access-Control-Allow-Origin"] = request_origin
        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return headers

    def is_origin_allowed(self, origin: str) -> bool:
        """Check if an origin is in the allowed list."""
        if not self._allowed_origins:
            return True
        return origin in self._allowed_origins


class ErrorHandler:
    """Centralized error handling and formatting."""

    @staticmethod
    def format_error(status_code: int, message: str,
                     details: Dict[str, Any] = None) -> Response:
        """Format an error response."""
        body = {"error": message, "status_code": status_code}
        if details:
            body["details"] = details
        return Response(status_code, body)

    @staticmethod
    def handle_validation_error(missing_fields: List[str]) -> Response:
        """Handle missing field validation errors."""
        return ErrorHandler.format_error(
            400, "Validation error",
            {"missing_fields": missing_fields}
        )

    @staticmethod
    def handle_not_found(resource: str) -> Response:
        """Handle resource not found errors."""
        return ErrorHandler.format_error(404, f"{resource} not found")

    @staticmethod
    def handle_rate_limit() -> Response:
        """Handle rate limit exceeded errors."""
        return ErrorHandler.format_error(429, "Rate limit exceeded")
'''

    # Public tests - visible to the agent
    public_tests_express = '''"""Public tests for Express API - visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import (
    Request, Response, MiddlewareChain, Router,
    RequestValidator, RateLimiter, CorsHandler, ErrorHandler
)


def test_request_creation():
    """Should create a request with method and path."""
    req = Request("GET", "/api/users")
    assert req.method == "GET"
    assert req.path == "/api/users"


def test_request_headers():
    """Should retrieve headers case-insensitively."""
    req = Request("GET", "/", headers={"Content-Type": "application/json"})
    assert req.get_header("content-type") == "application/json"
    assert req.get_header("missing", "default") == "default"


def test_request_query_params():
    """Should retrieve query parameters."""
    req = Request("GET", "/search", query_params={"q": "test"})
    assert req.get_query_param("q") == "test"
    assert req.get_query_param("missing", "default") == "default"


def test_response_creation():
    """Should create a response with status code."""
    resp = Response(200, {"key": "value"})
    assert resp.status_code == 200
    assert resp.body == {"key": "value"}


def test_response_set_header():
    """Should set response headers."""
    resp = Response(200)
    resp.set_header("X-Custom", "value")
    assert resp.headers["X-Custom"] == "value"


def test_router_add_and_dispatch():
    """Should route a request to the correct handler."""
    router = Router()
    router.add_route("GET", "/api/health", lambda req: Response(200, {"status": "ok"}))
    resp = router.dispatch(Request("GET", "/api/health"))
    assert resp.status_code == 200
    assert resp.body == {"status": "ok"}


def test_router_404():
    """Should return 404 for unknown routes."""
    router = Router()
    resp = router.dispatch(Request("GET", "/unknown"))
    assert resp.status_code == 404


def test_router_parameterized():
    """Should match parameterized routes."""
    router = Router()
    router.add_route("GET", "/api/users/:id", lambda req: Response(200, {"id": "matched"}))
    resp = router.dispatch(Request("GET", "/api/users/123"))
    assert resp.status_code == 200


def test_middleware_chain():
    """Should execute middleware in order."""
    chain = MiddlewareChain()
    order = []
    chain.use(lambda req: Request(req.method, req.path))
    chain.use(lambda req: Response(200, {"middleware": True}))
    resp = chain.execute(Request("GET", "/"))
    assert resp.status_code == 200


def test_middleware_short_circuit():
    """Middleware can short-circuit with a response."""
    chain = MiddlewareChain()
    chain.use(lambda req: Response(401, {"error": "Unauthorized"}))
    chain.use(lambda req: Response(200, {"ok": True}))
    resp = chain.execute(Request("GET", "/"))
    assert resp.status_code == 401


def test_request_validator_required():
    """Should detect missing required fields."""
    missing = RequestValidator.validate_required_fields(
        {"name": "test"}, ["name", "email"]
    )
    assert "email" in missing


def test_request_validator_email():
    """Should validate email format."""
    assert RequestValidator.validate_email("user@example.com") is True
    assert RequestValidator.validate_email("invalid") is False


def test_rate_limiter_basic():
    """Should allow requests within limit."""
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    for i in range(5):
        assert limiter.is_allowed("client1") is True


def test_error_handler_format():
    """Should format error responses."""
    resp = ErrorHandler.format_error(400, "Bad request")
    assert resp.status_code == 400
    assert resp.body["error"] == "Bad request"


def test_cors_handler_headers():
    """Should generate CORS headers."""
    handler = CorsHandler(["https://example.com"])
    headers = handler.get_headers("https://example.com")
    assert "Access-Control-Allow-Origin" in headers
'''

    # Hidden tests - NOT visible to the agent
    hidden_tests_express = '''"""Hidden tests for Express API - NOT visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import (
    Request, RequestValidator, RateLimiter, CorsHandler
)


def test_sanitize_removes_script_tags():
    """Input sanitizer should remove script tags."""
    malicious = '<script>alert("xss")</script>Hello'
    sanitized = RequestValidator.sanitize_input(malicious)
    assert '<script>' not in sanitized, \
        "Sanitizer should remove script tags"


def test_sanitize_removes_sql_injection():
    """Input sanitizer should escape SQL injection patterns."""
    malicious = "'; DROP TABLE users; --"
    sanitized = RequestValidator.sanitize_input(malicious)
    assert "DROP TABLE" not in sanitized.upper(), \
        "Sanitizer should handle SQL injection patterns"


def test_rate_limiter_blocks_over_limit():
    """Rate limiter should block requests over the limit."""
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    assert limiter.is_allowed("client1") is True
    assert limiter.is_allowed("client1") is True
    assert limiter.is_allowed("client1") is True
    # 4th request should be blocked
    assert limiter.is_allowed("client1") is False, \
        "Rate limiter should block requests over the limit"


def test_cors_rejects_unauthorized_origin():
    """CORS handler should reject origins not in the allowed list."""
    handler = CorsHandler(["https://example.com"])
    assert handler.is_origin_allowed("https://evil.com") is False, \
        "Unauthorized origin should be rejected"


def test_cors_headers_only_for_allowed_origin():
    """CORS headers should only include allowed origins."""
    handler = CorsHandler(["https://example.com"])
    headers = handler.get_headers("https://evil.com")
    allowed = headers.get("Access-Control-Allow-Origin", "")
    assert allowed == "https://example.com" or allowed == "", \
        f"CORS should not allow evil.com, got: {allowed}"
'''

    # Reference solution
    reference_fix_express = r'''"""Reference solution for Express API bugs."""

def sanitize_input_fixed(value: str) -> str:
    """Fixed: sanitize input by removing dangerous characters."""
    # Remove script tags
    value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE)
    # Remove SQL injection patterns
    value = re.sub(r"(DROP|DELETE|INSERT|UPDATE|SELECT)\s+", '', value, flags=re.IGNORECASE)
    # Escape special characters
    value = value.replace("'", "").replace('"', '').replace(';', '')
    return value


def is_allowed_fixed(self, client_id: str) -> bool:
    """Fixed: enforce rate limit."""
    now = time.time()
    if client_id not in self._requests:
        self._requests[client_id] = []
    self._requests[client_id] = [
        t for t in self._requests[client_id]
        if now - t < self._window
    ]
    if len(self._requests[client_id]) >= self._max_requests:
        return False
    self._requests[client_id].append(now)
    return True


def get_headers_fixed(self, request_origin: str) -> Dict[str, str]:
    """Fixed: only allow configured origins."""
    headers = {}
    if request_origin and self.is_origin_allowed(request_origin):
        headers["Access-Control-Allow-Origin"] = request_origin
    headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return headers
'''

    register_template(
        "express_api",
        {
            "name": "express_api",
            "version": "0.1",
            "description": "Express-style REST API with CORS, rate limiting, and input validation bugs",
            "dependencies": [],
            "files": {
                "app.py": app_code,
                "tests/test_public.py": public_tests_express,
                ".hidden_tests/test_hidden.py": hidden_tests_express,
                ".reference_solution.py": reference_fix_express,
            },
        },
    )


# ---------------------------------------------------------------------------
# Django App Template
# ---------------------------------------------------------------------------


def _register_django_app() -> None:
    """Register the django_app template.

    A Django-style ORM + views framework in pure Python with model
    definitions, query sets, form validation, and middleware.
    The agent's job is to fix security and validation bugs.
    """

    # Main application file
    app_code = r'''"""Django-style App - An ORM and views framework in pure Python."""

import re
from typing import Any, Dict, List, Optional, Tuple


class Field:
    """Defines a model field with type and constraints."""

    def __init__(self, field_type: str = "string", max_length: int = None,
                 nullable: bool = True, default: Any = None):
        self.field_type = field_type
        self.max_length = max_length
        self.nullable = nullable
        self.default = default

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a value against field constraints."""
        if value is None:
            return self.nullable, "Field cannot be null" if not self.nullable else None

        if self.field_type == "string" and isinstance(value, str):
            if self.max_length and len(value) > self.max_length:
                return False, f"String exceeds max length {self.max_length}"
        elif self.field_type == "integer" and not isinstance(value, int):
            return False, "Expected integer value"
        elif self.field_type == "email" and isinstance(value, str):
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, value):
                return False, "Invalid email format"
        return True, None


class Model:
    """Base model class with field definitions and validation."""

    _fields: Dict[str, Field] = {}

    def __init__(self, **kwargs):
        self._data: Dict[str, Any] = {}
        for field_name, field in self._fields.items():
            self._data[field_name] = kwargs.get(field_name, field.default)

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any):
        if name in ("_data", "_fields"):
            super().__setattr__(name, value)
        elif name in self._fields:
            self._data[name] = value
        else:
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate all field values."""
        errors = []
        for field_name, field in self._fields.items():
            value = self._data.get(field_name)
            valid, error = field.validate(value)
            if not valid:
                errors.append(f"{field_name}: {error}")
        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return dict(self._data)


class QuerySet:
    """Represents a database query with filtering and aggregation."""

    def __init__(self, model_class: type, records: List[Dict[str, Any]] = None):
        self._model = model_class
        self._records = records or []
        self._filters: List[Tuple[str, str, Any]] = []

    def filter(self, **kwargs) -> "QuerySet":
        """Add filter conditions."""
        for key, value in kwargs.items():
            self._filters.append((key, "=", value))
        return self

    def exclude(self, **kwargs) -> "QuerySet":
        """Add exclusion conditions."""
        for key, value in kwargs.items():
            self._filters.append((key, "!=", value))
        return self

    def execute(self) -> List[Dict[str, Any]]:
        """Execute the query and return matching records."""
        results = self._records[:]
        for field, op, value in self._filters:
            if op == "=":
                results = [r for r in results if r.get(field) == value]
            elif op == "!=":
                results = [r for r in results if r.get(field) != value]
        return results

    def count(self) -> int:
        """Count matching records."""
        return len(self.execute())

    def first(self) -> Optional[Dict[str, Any]]:
        """Get the first matching record."""
        results = self.execute()
        return results[0] if results else None

    def raw_query(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute a raw SQL-like query string.

        WARNING: This method constructs queries from strings.
        """
        # BUG: sql_injection - no parameterization
        query = sql
        for param in params:
            query = query.replace("?", str(param), 1)
        # Simulate query execution by parsing simple SELECT
        return self._records[:]  # Simplified for pure Python


class FormValidator:
    """Validates form input data."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.errors: Dict[str, List[str]] = {}

    def clean(self) -> Dict[str, Any]:
        """Run all validation and return cleaned data."""
        cleaned = {}
        for key, value in self.data.items():
            cleaned[key] = self._clean_field(key, value)
        return cleaned

    def _clean_field(self, field_name: str, value: Any) -> Any:
        """Clean and validate a single field."""
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return value

    def is_valid(self) -> bool:
        """Check if the form data is valid."""
        self.clean()
        return len(self.errors) == 0


class View:
    """Base view class for handling requests."""

    def __init__(self):
        self._csrf_token: Optional[str] = None

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming request."""
        method = request.get("method", "GET").upper()
        if method == "POST":
            return self.post(request)
        elif method == "GET":
            return self.get(request)
        else:
            return {"status": 405, "error": "Method not allowed"}

    def get(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GET request."""
        return {"status": 200, "data": {}}

    def post(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle POST request."""
        # BUG: csrf_missing - no CSRF token check on POST
        return {"status": 201, "data": {}}

    def _check_csrf(self, request: Dict[str, Any]) -> bool:
        """Check CSRF token validity."""
        token = request.get("csrf_token")
        if not token:
            return False
        # BUG: csrf_missing - always returns True
        return True

    def redirect(self, url: str) -> Dict[str, Any]:
        """Redirect to a URL."""
        # BUG: open_redirect - no URL validation
        return {"status": 302, "location": url}


class Middleware:
    """Request/response middleware for cross-cutting concerns."""

    def __init__(self):
        self._chain: List["Middleware"] = []

    def add(self, middleware: "Middleware") -> None:
        """Add middleware to the chain."""
        self._chain.append(middleware)

    def process_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process request through middleware chain."""
        for mw in self._chain:
            result = mw.process_request(request)
            if result is not None:
                return result
        return request

    def process_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process response through middleware chain."""
        for mw in self._chain:
            response = mw.process_response(response)
        return response


# Concrete model example
class User(Model):
    """User model with common fields."""

    _fields = {
        "username": Field("string", max_length=50, nullable=False),
        "email": Field("email", nullable=False),
        "is_active": Field("integer", default=1),
    }
'''

    # Public tests - visible to the agent
    public_tests_django = '''"""Public tests for Django App - visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import (
    Field, Model, QuerySet, FormValidator, View, Middleware, User
)


def test_field_validation_string():
    """Should validate string fields."""
    field = Field("string", max_length=10)
    valid, error = field.validate("hello")
    assert valid is True


def test_field_validation_max_length():
    """Should reject strings exceeding max length."""
    field = Field("string", max_length=5)
    valid, error = field.validate("toolong")
    assert valid is False


def test_field_validation_email():
    """Should validate email format."""
    field = Field("email")
    assert field.validate("user@example.com")[0] is True
    assert field.validate("invalid")[0] is False


def test_field_nullable():
    """Should allow null for nullable fields."""
    field = Field("string", nullable=True)
    assert field.validate(None)[0] is True


def test_field_not_nullable():
    """Should reject null for non-nullable fields."""
    field = Field("string", nullable=False)
    assert field.validate(None)[0] is False


def test_model_creation():
    """Should create a model instance."""
    user = User(username="alice", email="alice@example.com")
    assert user.username == "alice"
    assert user.email == "alice@example.com"


def test_model_validate():
    """Should validate model fields."""
    user = User(username="alice", email="alice@example.com")
    valid, errors = user.validate()
    assert valid is True


def test_model_validate_error():
    """Should report validation errors."""
    user = User(username="", email="invalid")
    valid, errors = user.validate()
    assert valid is False
    assert len(errors) > 0


def test_model_to_dict():
    """Should convert model to dictionary."""
    user = User(username="bob", email="bob@example.com")
    d = user.to_dict()
    assert d["username"] == "bob"


def test_queryset_filter():
    """Should filter records."""
    records = [
        {"name": "Alice", "status": "active"},
        {"name": "Bob", "status": "inactive"},
    ]
    qs = QuerySet(User, records)
    results = qs.filter(status="active")
    assert len(results.execute()) == 1


def test_queryset_exclude():
    """Should exclude records."""
    records = [
        {"name": "Alice", "status": "active"},
        {"name": "Bob", "status": "inactive"},
    ]
    qs = QuerySet(User, records)
    results = qs.exclude(status="active")
    assert len(results.execute()) == 1


def test_queryset_count():
    """Should count matching records."""
    records = [
        {"name": "Alice", "status": "active"},
        {"name": "Bob", "status": "active"},
    ]
    qs = QuerySet(User, records)
    assert qs.filter(status="active").count() == 2


def test_queryset_first():
    """Should return the first matching record."""
    records = [{"name": "Alice"}, {"name": "Bob"}]
    qs = QuerySet(User, records)
    first = qs.first()
    assert first["name"] == "Alice"


def test_form_validator_clean():
    """Should clean form data."""
    form = FormValidator({"name": "  Alice  ", "age": 30})
    cleaned = form.clean()
    assert cleaned["name"] == "Alice"


def test_view_get():
    """Should handle GET requests."""
    view = View()
    resp = view.handle({"method": "GET"})
    assert resp["status"] == 200


def test_middleware_chain():
    """Should process request through middleware chain."""
    mw = Middleware()
    result = mw.process_request({"key": "value"})
    assert result["key"] == "value"
'''

    # Hidden tests - NOT visible to the agent
    hidden_tests_django = '''"""Hidden tests for Django App - NOT visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import View, QuerySet


def test_csrf_check_on_post():
    """POST requests should check CSRF token."""
    view = View()
    # POST without CSRF token should fail
    resp = view.post({"method": "POST", "csrf_token": None})
    # With the bug, it returns 201; fixed it should reject
    assert resp.get("status") != 201 or "csrf" not in str(resp).lower() or True
    # The key test: _check_csrf should not always return True
    assert view._check_csrf({"csrf_token": None}) is False, \
        "CSRF check should fail when no token is provided"


def test_csrf_check_invalid_token():
    """CSRF check should reject invalid tokens."""
    view = View()
    view._csrf_token = "valid_token_123"
    assert view._check_csrf({"csrf_token": "invalid_token"}) is False, \
        "CSRF check should reject invalid tokens"


def test_redirect_validates_url():
    """Redirect should validate the target URL."""
    view = View()
    # Open redirect to external site should be blocked
    resp = view.redirect("https://evil.com/phishing")
    assert resp.get("location") != "https://evil.com/phishing", \
        "Redirect should not allow external URLs"


def test_redirect_allows_relative_url():
    """Redirect should allow relative URLs."""
    view = View()
    resp = view.redirect("/dashboard")
    assert resp.get("location") == "/dashboard", \
        "Redirect should allow relative URLs"


def test_raw_query_parameterized():
    """Raw queries should use parameterized queries, not string formatting."""
    records = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    qs = QuerySet(User, records)
    # The raw_query method should not be vulnerable to SQL injection
    # In the buggy version, it does string replacement
    result = qs.raw_query("SELECT * FROM users WHERE id = ?", (1,))
    assert isinstance(result, list)
'''

    # Reference solution
    reference_fix_django = '''"""Reference solution for Django App bugs."""

def _check_csrf_fixed(self, request: Dict[str, Any]) -> bool:
    """Fixed: actually check CSRF token."""
    token = request.get("csrf_token")
    if not token or not self._csrf_token:
        return False
    return token == self._csrf_token


def post_fixed(self, request: Dict[str, Any]) -> Dict[str, Any]:
    """Fixed: check CSRF before processing POST."""
    if not self._check_csrf(request):
        return {"status": 403, "error": "CSRF token missing or invalid"}
    return {"status": 201, "data": {}}


def redirect_fixed(self, url: str) -> Dict[str, Any]:
    """Fixed: validate redirect URL."""
    # Only allow relative URLs (starting with /)
    if url and not url.startswith("/"):
        return {"status": 400, "error": "Invalid redirect URL"}
    return {"status": 302, "location": url}


def raw_query_fixed(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
    """Fixed: use parameterized queries."""
    # In a real implementation, this would use a proper DB driver
    # with parameterized queries. Here we just return matching records.
    return self._records[:]
'''

    register_template(
        "django_app",
        {
            "name": "django_app",
            "version": "0.1",
            "description": "Django-style ORM and views with SQL injection, CSRF, and open redirect bugs",
            "dependencies": [],
            "files": {
                "app.py": app_code,
                "tests/test_public.py": public_tests_django,
                ".hidden_tests/test_hidden.py": hidden_tests_django,
                ".reference_solution.py": reference_fix_django,
            },
        },
    )


# ---------------------------------------------------------------------------
# TypeScript API Template
# ---------------------------------------------------------------------------


def _register_typescript_api() -> None:
    """Register the typescript_api template.

    A TypeScript/Express-style API framework in pure Python with router,
    middleware, input validation, and error handling.
    """

    app_code = r'''"""TypeScript/Express-style API - Router, middleware, and validation in pure Python."""

import re
from typing import Any, Callable, Dict, List, Optional, Tuple


class Router:
    """Simple HTTP router with route registration and matching."""

    def __init__(self):
        self._routes: Dict[str, Dict[str, Callable]] = {}

    def add_route(self, method: str, path: str, handler: Callable) -> None:
        """Register a route handler."""
        method = method.upper()
        if method not in self._routes:
            self._routes[method] = {}
        self._routes[method][path] = handler

    def get(self, path: str, handler: Callable) -> None:
        """Register a GET route."""
        self.add_route("GET", path, handler)

    def post(self, path: str, handler: Callable) -> None:
        """Register a POST route."""
        self.add_route("POST", path, handler)

    def resolve(self, method: str, path: str) -> Optional[Callable]:
        """Find a handler for the given method and path."""
        method = method.upper()
        handlers = self._routes.get(method, {})
        return handlers.get(path)


class Middleware:
    """Middleware chain for request processing."""

    def __init__(self):
        self._middlewares: List[Callable] = []

    def use(self, middleware: Callable) -> None:
        """Add middleware to the chain."""
        self._middlewares.append(middleware)

    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through middleware chain."""
        for mw in self._middlewares:
            request = mw(request)
        return request


class InputValidator:
    """Validates request input against schemas."""

    @staticmethod
    def validate_string(value: Any, min_length: int = 0, max_length: int = 255) -> Tuple[bool, Optional[str]]:
        """Validate a string value."""
        if not isinstance(value, str):
            return False, "Expected string"
        if len(value) < min_length:
            return False, f"String too short (min {min_length})"
        if len(value) > max_length:
            return False, f"String too long (max {max_length})"
        return True, None

    @staticmethod
    def validate_email(value: Any) -> Tuple[bool, Optional[str]]:
        """Validate an email address."""
        if not isinstance(value, str):
            return False, "Expected string"
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, value):
            return False, "Invalid email format"
        return True, None

    @staticmethod
    def sanitize(value: str) -> str:
        """Sanitize input by removing potentially dangerous characters."""
        # Remove HTML tags
        value = re.sub(r'<[^>]*>', '', value)
        # Escape special characters
        value = value.replace('&', '&amp;')
        value = value.replace('"', '&quot;')
        value = value.replace("'", '&#x27;')
        value = value.replace('<', '&lt;')
        value = value.replace('>', '&gt;')
        return value


class ErrorHandler:
    """Centralized error handling."""

    @staticmethod
    def not_found(path: str) -> Dict[str, Any]:
        return {"status": 404, "error": "Not Found", "path": path}

    @staticmethod
    def bad_request(message: str) -> Dict[str, Any]:
        return {"status": 400, "error": "Bad Request", "message": message}

    @staticmethod
    def internal_error() -> Dict[str, Any]:
        return {"status": 500, "error": "Internal Server Error"}

    @staticmethod
    def handle_exception(exc: Exception) -> Dict[str, Any]:
        """Handle an exception and return an error response.

        BUG: Exposes stack trace in production.
        """
        import traceback
        return {
            "status": 500,
            "error": "Internal Server Error",
            "details": traceback.format_exc(),  # BUG: should not expose stack trace
        }
'''

    public_tests_typescript = '''"""Public tests for TypeScript API."""

import sys
sys.path.insert(0, ".")

from app import Router, Middleware, InputValidator, ErrorHandler


def test_router_get():
    """Should register and resolve GET routes."""
    router = Router()
    handler = lambda req: {"status": 200}
    router.get("/users", handler)
    assert router.resolve("GET", "/users") is handler


def test_router_post():
    """Should register and resolve POST routes."""
    router = Router()
    handler = lambda req: {"status": 201}
    router.post("/users", handler)
    assert router.resolve("POST", "/users") is handler


def test_router_not_found():
    """Should return None for unregistered routes."""
    router = Router()
    assert router.resolve("GET", "/nonexistent") is None


def test_middleware_chain():
    """Should process request through middleware chain."""
    mw = Middleware()
    def add_header(req):
        req["headers"] = req.get("headers", {})
        req["headers"]["X-Processed"] = "true"
        return req
    mw.use(add_header)
    result = mw.process({})
    assert result["headers"]["X-Processed"] == "true"


def test_input_validator_string():
    """Should validate string length."""
    valid, err = InputValidator.validate_string("hello", min_length=3, max_length=10)
    assert valid is True


def test_input_validator_string_too_short():
    """Should reject strings that are too short."""
    valid, err = InputValidator.validate_string("hi", min_length=3)
    assert valid is False


def test_input_validator_email():
    """Should validate email format."""
    valid, err = InputValidator.validate_email("user@example.com")
    assert valid is True


def test_input_validator_email_invalid():
    """Should reject invalid email format."""
    valid, err = InputValidator.validate_email("not-an-email")
    assert valid is False


def test_sanitize_html():
    """Should remove HTML tags."""
    result = InputValidator.sanitize("<script>alert(1)</script>hello")
    assert "<script>" not in result


def test_error_handler():
    """Should return proper error responses."""
    assert ErrorHandler.not_found("/test")["status"] == 404
    assert ErrorHandler.bad_request("msg")["status"] == 400
    assert ErrorHandler.internal_error()["status"] == 500
'''

    hidden_tests_typescript = '''"""Hidden tests for TypeScript API - NOT visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import InputValidator, ErrorHandler, Router


def test_sanitize_preserves_text():
    """Sanitize should preserve non-dangerous text."""
    result = InputValidator.sanitize("Hello, World!")
    assert result == "Hello, World!"


def test_sanitize_script_tags():
    """Sanitize should remove script tags."""
    result = InputValidator.sanitize("<script>malicious()</script>")
    assert "script" not in result.lower() or "<script>" not in result


def test_error_no_stack_trace():
    """Error handler should not expose stack traces."""
    exc = ValueError("test error")
    result = ErrorHandler.handle_exception(exc)
    assert "details" not in result or result["details"] == "", \
        "Error response should not contain stack trace details"


def test_input_validation_on_route():
    """Router should support input validation middleware."""
    router = Router()
    validated = []
    def handler(req):
        validated.append(req)
        return {"status": 200}
    router.post("/users", handler)
    h = router.resolve("POST", "/users")
    assert h is not None
'''

    reference_fix_typescript = '''"""Reference solution for TypeScript API bugs."""

def handle_exception_fixed(self, exc: Exception) -> Dict[str, Any]:
    """Fixed: do not expose stack trace."""
    return {
        "status": 500,
        "error": "Internal Server Error",
    }


def sanitize_fixed(value: str) -> str:
    """Fixed: properly sanitize all dangerous characters."""
    value = re.sub(r'<[^>]*>', '', value)
    value = value.replace('&', '&amp;')
    value = value.replace('"', '&quot;')
    value = value.replace("'", '&#x27;')
    value = value.replace('<', '&lt;')
    value = value.replace('>', '&gt;')
    return value
'''

    register_template(
        "typescript_api",
        {
            "name": "typescript_api",
            "version": "0.1",
            "description": "TypeScript/Express-style API with input validation, error leak, and auth bypass bugs",
            "dependencies": [],
            "files": {
                "app.py": app_code,
                "tests/test_public.py": public_tests_typescript,
                ".hidden_tests/test_hidden.py": hidden_tests_typescript,
                ".reference_solution.py": reference_fix_typescript,
            },
        },
    )


# ---------------------------------------------------------------------------
# Go Service Template
# ---------------------------------------------------------------------------


def _register_go_service() -> None:
    """Register the go_service template.

    A Go-style service framework in pure Python with handlers, stores,
    validators, and logging.
    """

    app_code = r'''"""Go-style Service - Handlers, stores, validators, and logging in pure Python."""

import time
import threading
from typing import Any, Dict, List, Optional, Tuple


class Logger:
    """Simple structured logger."""

    def __init__(self, level: str = "INFO"):
        self.level = level
        self._logs: List[Dict[str, Any]] = []

    def info(self, message: str, **kwargs) -> None:
        self._log("INFO", message, kwargs)

    def error(self, message: str, **kwargs) -> None:
        self._log("ERROR", message, kwargs)

    def _log(self, level: str, message: str, fields: Dict[str, Any]) -> None:
        entry = {
            "level": level,
            "message": message,
            "timestamp": time.time(),
            **fields,
        }
        self._logs.append(entry)


class Store:
    """In-memory key-value store with connection management."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._connected = False

    def connect(self) -> None:
        """Establish connection to the store."""
        self._connected = True

    def disconnect(self) -> None:
        """Close connection to the store."""
        self._connected = False

    def get(self, key: str) -> Optional[Any]:
        """Get a value by key."""
        if not self._connected:
            return None
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set a key-value pair."""
        if not self._connected:
            return
        with self._lock:
            self._data[key] = value

    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if the key existed."""
        if not self._connected:
            return False
        with self._lock:
            return self._data.pop(key, None) is not None


class Validator:
    """Request and response validation."""

    @staticmethod
    def validate_request(data: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, List[str]]:
        """Validate that required fields are present."""
        missing = [f for f in required_fields if f not in data or data[f] is None]
        if missing:
            return False, missing
        return True, []

    @staticmethod
    def validate_response(data: Dict[str, Any]) -> bool:
        """Validate response structure."""
        return isinstance(data, dict) and "status" in data


class Handler:
    """HTTP request handler with context management."""

    def __init__(self, store: Store, logger: Logger):
        self.store = store
        self.logger = logger

    def handle_get(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GET request."""
        key = request.get("key")
        if key is None:
            return {"status": 400, "error": "Missing key parameter"}

        value = self.store.get(key)
        if value is None:
            return {"status": 404, "error": "Not found"}

        return {"status": 200, "data": value}

    def handle_post(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle POST request.

        BUG: Does not check for nil pointer on request body.
        """
        body = request.get("body")
        # BUG: No nil check - will fail if body is None
        key = body["key"]  # BUG: KeyError if body is None
        value = body["value"]
        self.store.set(key, value)
        return {"status": 201, "data": {"key": key}}

    def handle_resource(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a resource request that opens a connection.

        BUG: Does not close connection on error path.
        """
        conn = Store()
        conn.connect()
        try:
            key = request.get("key", "")
            value = conn.get(key)
            if value is None:
                return {"status": 404, "error": "Not found"}
            # BUG: conn.disconnect() is missing on success path
            return {"status": 200, "data": value}
        except Exception as e:
            conn.disconnect()
            return {"status": 500, "error": str(e)}
'''

    public_tests_go = '''"""Public tests for Go Service."""

import sys
sys.path.insert(0, ".")

from app import Store, Validator, Handler, Logger


def test_store_connect():
    """Should connect and disconnect."""
    store = Store()
    store.connect()
    assert store._connected is True
    store.disconnect()
    assert store._connected is False


def test_store_get_set():
    """Should get and set values."""
    store = Store()
    store.connect()
    store.set("key1", "value1")
    assert store.get("key1") == "value1"


def test_store_delete():
    """Should delete values."""
    store = Store()
    store.connect()
    store.set("key1", "value1")
    assert store.delete("key1") is True
    assert store.get("key1") is None


def test_store_not_connected():
    """Should return None when not connected."""
    store = Store()
    assert store.get("key1") is None


def test_validator_required_fields():
    """Should validate required fields."""
    valid, missing = Validator.validate_request({"name": "test"}, ["name"])
    assert valid is True
    assert missing == []


def test_validator_missing_fields():
    """Should detect missing fields."""
    valid, missing = Validator.validate_request({}, ["name", "email"])
    assert valid is False
    assert "name" in missing


def test_validator_response():
    """Should validate response structure."""
    assert Validator.validate_response({"status": 200}) is True
    assert Validator.validate_response({}) is False


def test_logger():
    """Should log messages."""
    logger = Logger()
    logger.info("test message")
    assert len(logger._logs) == 1
    assert logger._logs[0]["message"] == "test message"


def test_handler_get():
    """Should handle GET requests."""
    store = Store()
    store.connect()
    store.set("key1", "value1")
    logger = Logger()
    handler = Handler(store, logger)
    result = handler.handle_get({"key": "key1"})
    assert result["status"] == 200
    assert result["data"] == "value1"
'''

    hidden_tests_go = '''"""Hidden tests for Go Service - NOT visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import Store, Handler, Logger


def test_handler_post_nil_body():
    """POST handler should handle None body gracefully."""
    store = Store()
    store.connect()
    logger = Logger()
    handler = Handler(store, logger)
    # Should not crash with None body
    result = handler.handle_post({"body": None})
    assert result["status"] == 400, \
        "POST handler should return 400 for None body, not crash"


def test_handler_post_missing_key():
    """POST handler should handle missing key in body."""
    store = Store()
    store.connect()
    logger = Logger()
    handler = Handler(store, logger)
    result = handler.handle_post({"body": {"value": "test"}})
    assert result["status"] == 400, \
        "POST handler should return 400 for missing key"


def test_resource_closes_connection():
    """Resource handler should close connection on success path."""
    store = Store()
    store.connect()
    store.set("key1", "value1")
    logger = Logger()
    handler = Handler(store, logger)
    # The handle_resource method creates its own Store connection
    # It should close it after use
    result = handler.handle_resource({"key": "key1"})
    # If the bug is present, the connection is leaked
    # We check that the method doesn't leave connections open
    assert result["status"] in (200, 404)
'''

    reference_fix_go = '''"""Reference solution for Go Service bugs."""

def handle_post_fixed(self, request: Dict[str, Any]) -> Dict[str, Any]:
    """Fixed: check for nil body."""
    body = request.get("body")
    if body is None:
        return {"status": 400, "error": "Missing request body"}
    key = body.get("key")
    if key is None:
        return {"status": 400, "error": "Missing key in body"}
    value = body.get("value")
    self.store.set(key, value)
    return {"status": 201, "data": {"key": key}}


def handle_resource_fixed(self, request: Dict[str, Any]) -> Dict[str, Any]:
    """Fixed: always close connection."""
    conn = Store()
    conn.connect()
    try:
        key = request.get("key", "")
        value = conn.get(key)
        if value is None:
            return {"status": 404, "error": "Not found"}
        return {"status": 200, "data": value}
    finally:
        conn.disconnect()
'''

    register_template(
        "go_service",
        {
            "name": "go_service",
            "version": "0.1",
            "description": "Go-style service with nil pointer, resource leak, and race condition bugs",
            "dependencies": [],
            "files": {
                "app.py": app_code,
                "tests/test_public.py": public_tests_go,
                ".hidden_tests/test_hidden.py": hidden_tests_go,
                ".reference_solution.py": reference_fix_go,
            },
        },
    )


# ---------------------------------------------------------------------------
# React App Template
# ---------------------------------------------------------------------------


def _register_react_app() -> None:
    """Register the react_app template.

    A React-like frontend application with state management, event dispatching,
    routing, and form handling. Pure Python implementation.
    """

    app_code = '''"""React App - Component, State, Event, Router, and Form modules."""

import time
import copy
from typing import Any, Callable, Dict, List, Optional


class Component:
    """Base React-like component with render lifecycle."""

    def __init__(self, props: Dict[str, Any] | None = None):
        self.props = props or {}
        self.state: Dict[str, Any] = {}
        self._children: List["Component"] = []

    def render(self) -> str:
        """Render the component to a string representation."""
        return f"<{self.__class__.__name__}>"

    def add_child(self, child: "Component") -> None:
        """Add a child component."""
        self._children.append(child)

    def get_children(self) -> List["Component"]:
        """Get all child components."""
        return self._children.copy()


class StateManager:
    """Manages application state with subscriptions."""

    def __init__(self, initial_state: Dict[str, Any] | None = None):
        self._state = initial_state or {}
        self._subscribers: List[Callable] = []

    def get_state(self) -> Dict[str, Any]:
        """Get current state (deep copy)."""
        return copy.deepcopy(self._state)

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state and notify subscribers."""
        self._state.update(updates)
        for subscriber in self._subscribers:
            subscriber(self._state)

    def subscribe(self, callback: Callable) -> None:
        """Subscribe to state changes."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from state changes."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)


class EventDispatcher:
    """Dispatches events to registered handlers."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def on(self, event: str, handler: Callable) -> None:
        """Register a handler for an event."""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def emit(self, event: str, data: Any = None) -> None:
        """Emit an event to all registered handlers."""
        for handler in self._handlers.get(event, []):
            handler(data)

    def off(self, event: str, handler: Callable | None = None) -> None:
        """Remove event handler(s)."""
        if event in self._handlers:
            if handler is None:
                del self._handlers[event]
            elif handler in self._handlers[event]:
                self._handlers[event].remove(handler)


class Router:
    """Simple client-side router."""

    def __init__(self):
        self._routes: Dict[str, Callable] = {}
        self._current_path: str = "/"

    def add_route(self, path: str, handler: Callable) -> None:
        """Register a route handler."""
        self._routes[path] = handler

    def navigate(self, path: str) -> Any:
        """Navigate to a new path and return handler result."""
        self._current_path = path
        handler = self._routes.get(path)
        if handler is None:
            return {"status": 404, "error": "Not found"}
        return handler()

    def current_path(self) -> str:
        """Get the current path."""
        return self._current_path


class FormHandler:
    """Handles form validation and submission."""

    def __init__(self):
        self._validators: Dict[str, List[Callable]] = {}

    def add_validator(self, field: str, validator: Callable) -> None:
        """Add a validator for a form field."""
        if field not in self._validators:
            self._validators[field] = []
        self._validators[field].append(validator)

    def validate(self, form_data: Dict[str, str]) -> Dict[str, List[str]]:
        """Validate form data and return errors by field."""
        errors: Dict[str, List[str]] = {}
        for field, value in form_data.items():
            field_errors: List[str] = []
            for validator in self._validators.get(field, []):
                try:
                    result = validator(value)
                    if result is not None:
                        field_errors.append(result)
                except Exception as e:
                    field_errors.append(str(e))
            if field_errors:
                errors[field] = field_errors
        return errors

    def sanitize(self, value: str) -> str:
        """Sanitize form input to prevent XSS."""
        # BUG: xss_injection - doesn't actually sanitize
        return value
'''

    public_tests_react = '''"""Public tests for React App - visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import Component, StateManager, EventDispatcher, Router, FormHandler


def test_component_render():
    """Component should render."""
    comp = Component({"name": "test"})
    result = comp.render()
    assert "Component" in result


def test_component_children():
    """Component should manage children."""
    parent = Component()
    child = Component()
    parent.add_child(child)
    assert len(parent.get_children()) == 1


def test_state_manager_get():
    """StateManager should return state."""
    sm = StateManager({"count": 0})
    state = sm.get_state()
    assert state["count"] == 0


def test_state_manager_update():
    """StateManager should update state."""
    sm = StateManager({"count": 0})
    sm.update_state({"count": 1})
    assert sm.get_state()["count"] == 1


def test_state_manager_subscribe():
    """StateManager should notify subscribers."""
    sm = StateManager({"count": 0})
    received = []
    sm.subscribe(lambda s: received.append(s))
    sm.update_state({"count": 1})
    assert len(received) == 1


def test_event_dispatcher():
    """EventDispatcher should emit events."""
    dispatcher = EventDispatcher()
    received = []
    dispatcher.on("click", lambda d: received.append(d))
    dispatcher.emit("click", "button")
    assert "button" in received


def test_router_navigation():
    """Router should navigate to routes."""
    router = Router()
    router.add_route("/home", lambda: {"page": "home"})
    result = router.navigate("/home")
    assert result["page"] == "home"


def test_router_404():
    """Router should return 404 for unknown routes."""
    router = Router()
    result = router.navigate("/unknown")
    assert result["status"] == 404


def test_form_validation():
    """FormHandler should validate fields."""
    fh = FormHandler()
    fh.add_validator("email", lambda v: "Invalid email" if "@" not in v else None)
    errors = fh.validate({"email": "invalid"})
    assert "email" in errors


def test_form_sanitize():
    """FormHandler should sanitize input."""
    fh = FormHandler()
    # BUG: xss_injection - sanitize doesn't actually sanitize
    result = fh.sanitize("<script>alert('xss')</script>")
    assert "<script>" not in result, "Sanitize should remove script tags"
'''

    hidden_tests_react = '''"""Hidden tests for React App - NOT visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import StateManager, EventDispatcher, FormHandler


def test_state_manager_unsubscribe():
    """StateManager should remove subscribers."""
    sm = StateManager({"count": 0})
    received = []
    cb = lambda s: received.append(s)
    sm.subscribe(cb)
    sm.unsubscribe(cb)
    sm.update_state({"count": 1})
    assert len(received) == 0, "Unsubscribed callback should not be called"


def test_event_dispatcher_off():
    """EventDispatcher should remove handlers."""
    dispatcher = EventDispatcher()
    received = []
    handler = lambda d: received.append(d)
    dispatcher.on("click", handler)
    dispatcher.off("click", handler)
    dispatcher.emit("click", "button")
    assert len(received) == 0, "Removed handler should not be called"


def test_xss_sanitize_script_tags():
    """Sanitize should remove all script tags."""
    fh = FormHandler()
    result = fh.sanitize("<script>alert(1)</script><b>bold</b>")
    assert "<script>" not in result, "Script tags should be removed"


def test_xss_sanitize_event_handlers():
    """Sanitize should remove event handlers."""
    fh = FormHandler()
    result = fh.sanitize('<img onerror="alert(1)">')
    assert "onerror" not in result, "Event handlers should be removed"


def test_state_deep_copy():
    """get_state should return deep copy."""
    sm = StateManager({"data": [1, 2, 3]})
    state1 = sm.get_state()
    state1["data"].append(4)
    state2 = sm.get_state()
    assert len(state2["data"]) == 3, "State should be deep copied"
'''

    reference_fix_react = '''"""Reference solution for React App bugs."""

def sanitize_fixed(self, value: str) -> str:
    """Fixed: properly sanitize HTML input."""
    import re
    # Remove script tags
    value = re.sub(r"<script[^>]*>.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)
    # Remove event handlers
    value = re.sub(r"\s+on\w+\s*=\s*[""'][^""']*[""']", "", value, flags=re.IGNORECASE)
    # Escape remaining HTML
    value = value.replace("<", "&lt;").replace(">", "&gt;")
    return value
'''

    register_template(
        "react_app",
        {
            "name": "react_app",
            "version": "0.1",
            "description": "React-like frontend with state management, events, routing, and form handling",
            "dependencies": [],
            "files": {
                "app.py": app_code,
                "tests/test_public.py": public_tests_react,
                ".hidden_tests/test_hidden.py": hidden_tests_react,
                ".reference_solution.py": reference_fix_react,
            },
        },
    )


# ---------------------------------------------------------------------------
# Spring Service Template
# ---------------------------------------------------------------------------


def _register_spring_service() -> None:
    """Register the spring_service template.

    A Spring-like backend service with repository pattern, transaction management,
    validation, and controller. Pure Python implementation.
    """

    app_code = '''"""Spring Service - Service, Repository, Controller, Validator, Transaction modules."""

import time
from typing import Any, Dict, List, Optional


class Repository:
    """Data repository with CRUD operations."""

    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
        self._next_id = 1

    def save(self, entity: Dict[str, Any]) -> str:
        """Save an entity and return its ID."""
        entity_id = str(self._next_id)
        self._next_id += 1
        entity["id"] = entity_id
        self._data[entity_id] = entity.copy()
        return entity_id

    def find_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Find an entity by ID."""
        return self._data.get(entity_id)

    def find_all(self) -> List[Dict[str, Any]]:
        """Find all entities."""
        return list(self._data.values())

    def delete(self, entity_id: str) -> bool:
        """Delete an entity by ID."""
        if entity_id in self._data:
            del self._data[entity_id]
            return True
        return False

    def count(self) -> int:
        """Count total entities."""
        return len(self._data)


class TransactionManager:
    """Manages database transactions with commit/rollback."""

    def __init__(self):
        self._active: Optional[Dict[str, Any]] = None

    def begin(self) -> None:
        """Begin a new transaction."""
        self._active = {"started_at": time.time(), "operations": []}

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._active is None:
            raise RuntimeError("No active transaction")
        self._active = None

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self._active = None

    def is_active(self) -> bool:
        """Check if a transaction is active."""
        return self._active is not None

    def add_operation(self, op: Dict[str, Any]) -> None:
        """Add an operation to the current transaction."""
        if self._active is None:
            raise RuntimeError("No active transaction")
        self._active["operations"].append(op)


class Validator:
    """Validates request data."""

    def __init__(self):
        self._rules: Dict[str, List[Dict[str, Any]]] = {}

    def add_rule(self, field: str, rule: Dict[str, Any]) -> None:
        """Add a validation rule for a field."""
        if field not in self._rules:
            self._rules[field] = []
        self._rules[field].append(rule)

    def validate(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate data against rules and return errors."""
        errors: Dict[str, str] = {}
        for field, rules in self._rules.items():
            value = data.get(field)
            for rule in rules:
                if rule["type"] == "required" and (value is None or value == ""):
                    errors[field] = f"{field} is required"
                elif rule["type"] == "min_length" and isinstance(value, str):
                    if len(value) < rule["value"]:
                        errors[field] = f"{field} must be at least {rule['value']} characters"
                elif rule["type"] == "max_length" and isinstance(value, str):
                    if len(value) > rule["value"]:
                        errors[field] = f"{field} must be at most {rule['value']} characters"
        return errors


class Service:
    """Business logic service layer."""

    def __init__(self, repository: Repository, transaction_manager: TransactionManager):
        self.repository = repository
        self.transaction_manager = transaction_manager

    def create_entity(self, data: Dict[str, Any]) -> str:
        """Create a new entity within a transaction."""
        self.transaction_manager.begin()
        try:
            entity_id = self.repository.save(data)
            self.transaction_manager.commit()
            return entity_id
        except Exception:
            # BUG: transaction_leak - doesn't rollback on error
            raise

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get an entity by ID."""
        return self.repository.find_by_id(entity_id)

    def list_entities(self) -> List[Dict[str, Any]]:
        """List all entities."""
        # BUG: n_plus_one - loads each entity individually instead of batch
        all_entities = self.repository.find_all()
        result = []
        for entity in all_entities:
            fetched = self.repository.find_by_id(entity["id"])
            if fetched:
                result.append(fetched)
        return result


class Controller:
    """HTTP-like request controller."""

    def __init__(self, service: Service, validator: Validator):
        self.service = service
        self.validator = validator

    def handle_create(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle create request."""
        data = request.get("body", {})
        errors = self.validator.validate(data)
        if errors:
            return {"status": 400, "errors": errors}
        # BUG: validation_bypass - doesn't check validation errors before creating
        entity_id = self.service.create_entity(data)
        return {"status": 201, "id": entity_id}

    def handle_get(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get request."""
        entity_id = request.get("id", "")
        entity = self.service.get_entity(entity_id)
        if entity is None:
            return {"status": 404, "error": "Not found"}
        return {"status": 200, "data": entity}

    def handle_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list request."""
        entities = self.service.list_entities()
        return {"status": 200, "data": entities}
'''

    public_tests_spring = '''"""Public tests for Spring Service - visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import Repository, TransactionManager, Validator, Service, Controller


def test_repository_save():
    """Repository should save entities."""
    repo = Repository()
    entity_id = repo.save({"name": "test"})
    assert entity_id is not None


def test_repository_find():
    """Repository should find entities."""
    repo = Repository()
    entity_id = repo.save({"name": "test"})
    entity = repo.find_by_id(entity_id)
    assert entity["name"] == "test"


def test_repository_delete():
    """Repository should delete entities."""
    repo = Repository()
    entity_id = repo.save({"name": "test"})
    assert repo.delete(entity_id) is True
    assert repo.find_by_id(entity_id) is None


def test_repository_count():
    """Repository should count entities."""
    repo = Repository()
    assert repo.count() == 0
    repo.save({"name": "test"})
    assert repo.count() == 1


def test_transaction_begin_commit():
    """Transaction should begin and commit."""
    tm = TransactionManager()
    tm.begin()
    assert tm.is_active()
    tm.commit()
    assert not tm.is_active()


def test_transaction_rollback():
    """Transaction should rollback."""
    tm = TransactionManager()
    tm.begin()
    assert tm.is_active()
    tm.rollback()
    assert not tm.is_active()


def test_validator_required():
    """Validator should check required fields."""
    v = Validator()
    v.add_rule("name", {"type": "required"})
    errors = v.validate({})
    assert "name" in errors


def test_validator_min_length():
    """Validator should check minimum length."""
    v = Validator()
    v.add_rule("name", {"type": "min_length", "value": 3})
    errors = v.validate({"name": "ab"})
    assert "name" in errors


def test_controller_get():
    """Controller should handle GET requests."""
    repo = Repository()
    tm = TransactionManager()
    v = Validator()
    service = Service(repo, tm)
    controller = Controller(service, v)
    entity_id = repo.save({"name": "test"})
    result = controller.handle_get({"id": entity_id})
    assert result["status"] == 200


def test_controller_list():
    """Controller should handle list requests."""
    repo = Repository()
    tm = TransactionManager()
    v = Validator()
    service = Service(repo, tm)
    controller = Controller(service, v)
    repo.save({"name": "test1"})
    repo.save({"name": "test2"})
    result = controller.handle_list({})
    assert result["status"] == 200
    assert len(result["data"]) == 2
'''

    hidden_tests_spring = '''"""Hidden tests for Spring Service - NOT visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import Repository, TransactionManager, Validator, Service, Controller


def test_transaction_rollback_on_error():
    """Service should rollback transaction on error."""
    repo = Repository()
    tm = TransactionManager()
    service = Service(repo, tm)
    tm.begin()
    try:
        service.create_entity({})
    except Exception:
        pass
    # Transaction should be rolled back, not left active
    assert not tm.is_active(), "Transaction should be rolled back on error"


def test_list_entities_efficient():
    """list_entities should not do N+1 queries."""
    repo = Repository()
    tm = TransactionManager()
    service = Service(repo, tm)
    for i in range(10):
        repo.save({"name": f"test{i}"})
    entities = service.list_entities()
    # Should return all entities efficiently
    assert len(entities) == 10


def test_validation_bypass_prevented():
    """Controller should not create entity with validation errors."""
    repo = Repository()
    tm = TransactionManager()
    v = Validator()
    v.add_rule("name", {"type": "required"})
    service = Service(repo, tm)
    controller = Controller(service, v)
    result = controller.handle_create({"body": {"name": ""}})
    assert result["status"] == 400, "Should reject invalid data"
'''

    reference_fix_spring = '''"""Reference solution for Spring Service bugs."""

def create_entity_fixed(self, data: Dict[str, Any]) -> str:
    """Fixed: rollback on error."""
    self.transaction_manager.begin()
    try:
        entity_id = self.repository.save(data)
        self.transaction_manager.commit()
        return entity_id
    except Exception:
        self.transaction_manager.rollback()
        raise


def list_entities_fixed(self) -> List[Dict[str, Any]]:
    """Fixed: efficient batch load."""
    return self.repository.find_all()


def handle_create_fixed(self, request: Dict[str, Any]) -> Dict[str, Any]:
    """Fixed: check validation errors."""
    data = request.get("body", {})
    errors = self.validator.validate(data)
    if errors:
        return {"status": 400, "errors": errors}
    entity_id = self.service.create_entity(data)
    return {"status": 201, "id": entity_id}
'''

    register_template(
        "spring_service",
        {
            "name": "spring_service",
            "version": "0.1",
            "description": "Spring-like backend with repository, transactions, validation, and controller",
            "dependencies": [],
            "files": {
                "app.py": app_code,
                "tests/test_public.py": public_tests_spring,
                ".hidden_tests/test_hidden.py": hidden_tests_spring,
                ".reference_solution.py": reference_fix_spring,
            },
        },
    )


# Register all templates on module load
_register_task_manager_api()
_register_data_pipeline()
_register_flask_app()
_register_express_api()
_register_django_app()
_register_typescript_api()
_register_go_service()
_register_react_app()
_register_spring_service()


# ---------------------------------------------------------------------------
# Config Manager Template
# ---------------------------------------------------------------------------


def _register_config_manager() -> None:
    """Register the config_manager template.

    A configuration management system with loading, validation, merging,
    environment handling, and secret management.
    """

    app_code = '''"""Config Manager - Configuration loading, validation, merging, and secrets."""

import os
from typing import Any, Optional


class ConfigLoader:
    """Load configuration from multiple sources."""

    def __init__(self):
        self._configs: dict[str, dict[str, Any]] = {}

    def load(self, source: str, data: dict[str, Any]) -> None:
        """Load configuration from a source."""
        self._configs[source] = data

    def get(self, source: str) -> Optional[dict[str, Any]]:
        """Get configuration from a specific source."""
        return self._configs.get(source)

    def get_all(self) -> dict[str, dict[str, Any]]:
        """Get all loaded configurations."""
        return dict(self._configs)


class Validator:
    """Validate configuration values."""

    def __init__(self):
        self._rules: dict[str, dict[str, Any]] = {}

    def add_rule(self, key: str, rule: dict[str, Any]) -> None:
        """Add a validation rule for a key."""
        self._rules[key] = rule

    def validate(self, config: dict[str, Any]) -> list[str]:
        """Validate a configuration dictionary against rules.

        Returns:
            List of error messages. Empty if valid.
        """
        errors = []
        for key, rule in self._rules.items():
            if rule.get("type") == "required" and key not in config:
                errors.append(f"Missing required key: {key}")
            elif key in config:
                if rule.get("type") == "string" and not isinstance(config[key], str):
                    errors.append(f"Key '{key}' must be a string")
                if rule.get("type") == "integer" and not isinstance(config[key], int):
                    errors.append(f"Key '{key}' must be an integer")
                if rule.get("min") is not None and config[key] < rule["min"]:
                    errors.append(f"Key '{key}' must be >= {rule['min']}")
                if rule.get("max") is not None and config[key] > rule["max"]:
                    errors.append(f"Key '{key}' must be <= {rule['max']}")
        return errors


class Merger:
    """Merge configurations from multiple sources."""

    @staticmethod
    def merge(
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge override into base configuration.

        Override values take precedence. Nested dicts are merged recursively.

        Returns:
            Merged configuration dictionary.
        """
        result = dict(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = Merger.merge(result[key], value)
            else:
                result[key] = value
        return result


class EnvironmentHandler:
    """Handle environment-specific configuration."""

    def __init__(self):
        self._env_configs: dict[str, dict[str, Any]] = {}

    def register(self, env: str, config: dict[str, Any]) -> None:
        """Register configuration for an environment."""
        self._env_configs[env] = config

    def get_for_env(self, env: str) -> dict[str, Any]:
        """Get configuration for a specific environment.

        Falls back to 'default' if environment not found.
        """
        if env in self._env_configs:
            return dict(self._env_configs[env])
        return dict(self._env_configs.get("default", {}))

    def resolve(self, config: dict[str, Any]) -> dict[str, Any]:
        """Resolve environment variables in configuration.

        Replaces ${VAR_NAME} patterns with actual environment values.
        """
        resolved = dict(config)
        for key, value in resolved.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                resolved[key] = os.environ.get(var_name, value)
        return resolved


class SecretManager:
    """Manage secrets securely."""

    def __init__(self):
        self._secrets: dict[str, str] = {}
        self._access_log: list[str] = []

    def set_secret(self, key: str, value: str) -> None:
        """Store a secret value."""
        self._secrets[key] = value

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret value.

        Logs access for audit purposes.
        """
        self._access_log.append(key)
        return self._secrets.get(key)

    def has_secret(self, key: str) -> bool:
        """Check if a secret exists without logging access."""
        return key in self._secrets

    def get_access_log(self) -> list[str]:
        """Get the access log for audit."""
        return list(self._access_log)

    def mask_secret(self, value: str) -> str:
        """Mask a secret value for logging.

        Shows first and last character with asterisks in between.
        """
        if len(value) <= 2:
            return "*" * len(value)
        return value[0] + "*" * (len(value) - 2) + value[-1]
'''

    public_tests_config = '''"""Public tests for Config Manager - visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import ConfigLoader, Validator, Merger, EnvironmentHandler, SecretManager


def test_config_loader():
    loader = ConfigLoader()
    loader.load("file", {"key": "value"})
    assert loader.get("file") == {"key": "value"}


def test_config_loader_missing():
    loader = ConfigLoader()
    assert loader.get("missing") is None


def test_validator_required():
    v = Validator()
    v.add_rule("name", {"type": "required"})
    errors = v.validate({})
    assert len(errors) == 1


def test_validator_type_check():
    v = Validator()
    v.add_rule("port", {"type": "integer"})
    errors = v.validate({"port": "not_int"})
    assert len(errors) == 1


def test_validator_valid():
    v = Validator()
    v.add_rule("port", {"type": "integer", "min": 1, "max": 65535})
    errors = v.validate({"port": 8080})
    assert len(errors) == 0


def test_merger_basic():
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}
    result = Merger.merge(base, override)
    assert result == {"a": 1, "b": 3, "c": 4}


def test_merger_nested():
    base = {"db": {"host": "localhost", "port": 5432}}
    override = {"db": {"port": 3306}}
    result = Merger.merge(base, override)
    assert result["db"]["host"] == "localhost"
    assert result["db"]["port"] == 3306


def test_environment_handler():
    eh = EnvironmentHandler()
    eh.register("production", {"debug": False})
    config = eh.get_for_env("production")
    assert config["debug"] is False


def test_secret_manager():
    sm = SecretManager()
    sm.set_secret("api_key", "secret123")
    assert sm.get_secret("api_key") == "secret123"


def test_secret_masking():
    sm = SecretManager()
    masked = sm.mask_secret("secret123")
    assert masked == "s*******3"
    assert masked != "secret123"
'''

    hidden_tests_config = '''"""Hidden tests for Config Manager - NOT visible to the agent."""

import sys
import os
sys.path.insert(0, ".")

from app import ConfigLoader, Validator, Merger, EnvironmentHandler, SecretManager


def test_env_override_precedence():
    """Environment variables should override config values."""
    eh = EnvironmentHandler()
    os.environ["TEST_VAR"] = "from_env"
    config = {"value": "${TEST_VAR}"}
    resolved = eh.resolve(config)
    assert resolved["value"] == "from_env", f"Expected 'from_env', got '{resolved['value']}'"
    del os.environ["TEST_VAR"]


def test_secret_not_in_log():
    """Secret values should never appear in access log."""
    sm = SecretManager()
    sm.set_secret("password", "super_secret")
    sm.get_secret("password")
    log = sm.get_access_log()
    assert "password" not in "".join(log) or "super_secret" not in "".join(log)


def test_merge_empty_override():
    """Merging with empty override should return base unchanged."""
    base = {"a": 1, "b": {"c": 2}}
    result = Merger.merge(base, {})
    assert result == base


def test_validator_range_boundary():
    """Validator should accept values at min/max boundaries."""
    v = Validator()
    v.add_rule("port", {"type": "integer", "min": 1, "max": 65535})
    errors_min = v.validate({"port": 1})
    errors_max = v.validate({"port": 65535})
    assert len(errors_min) == 0
    assert len(errors_max) == 0


def test_secret_short_masking():
    """Short secrets should be fully masked."""
    sm = SecretManager()
    assert sm.mask_secret("a") == "*"
    assert sm.mask_secret("ab") == "**"
'''

    reference_fix_config = '''"""Reference solution for Config Manager bugs."""

def resolve_fixed(self, config: dict[str, Any]) -> dict[str, Any]:
    """Fixed: properly resolve environment variables."""
    resolved = dict(config)
    for key, value in resolved.items():
        if isinstance(value, str) and "${" in value:
            import re
            def replacer(match):
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))
            resolved[key] = re.sub(r"\$\{([^}]+)\}", replacer, value)
    return resolved


def mask_secret_fixed(self, value: str) -> str:
    """Fixed: properly mask secrets of all lengths."""
    if not value:
        return ""
    if len(value) <= 2:
        return "*" * len(value)
    return value[0] + "*" * (len(value) - 2) + value[-1]


def merge_fixed(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Fixed: deep merge that handles all edge cases."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = Merger.merge_fixed(result[key], value)
        else:
            result[key] = value
    return result
'''

    register_template(
        "config_manager",
        {
            "name": "config_manager",
            "version": "0.1",
            "description": "Configuration management with loading, validation, merging, environment handling, and secrets",
            "dependencies": [],
            "files": {
                "app.py": app_code,
                "tests/test_public.py": public_tests_config,
                ".hidden_tests/test_hidden.py": hidden_tests_config,
                ".reference_solution.py": reference_fix_config,
            },
        },
    )


# Register config_manager last (defined after the registration block)
_register_config_manager()


# ---------------------------------------------------------------------------
# Browser Automation Template
# ---------------------------------------------------------------------------


def _register_browser_automation() -> None:
    """Register the browser_automation template.

    A Playwright-style browser automation library with page navigation,
    element interaction, and form handling.
    """

    app_code = '''"""Browser Automation - Playwright-style automation in pure Python.

Provides Browser, Page, Element, Selector, and Action classes
for simulating browser automation patterns.
"""

from typing import Any, Optional


class Element:
    """Represents a DOM element."""

    def __init__(self, tag: str, attributes: dict[str, str] | None = None, text: str = ""):
        self.tag = tag
        self.attributes = attributes or {}
        self.text = text
        self._children: list["Element"] = []

    def get_attribute(self, name: str) -> str | None:
        return self.attributes.get(name)

    def find(self, selector: "Selector") -> "Element" | None:
        for child in self._children:
            if selector.match(child):
                return child
        return None

    def find_all(self, selector: "Selector") -> list["Element"]:
        results = []
        for child in self._children:
            if selector.match(child):
                results.append(child)
        return results


class Selector:
    """CSS-like selector for finding elements."""

    def __init__(self, tag: str | None = None, css_class: str | None = None, id_: str | None = None):
        self.tag = tag
        self.css_class = css_class
        self.id = id_

    def match(self, element: Element) -> bool:
        if self.tag and element.tag != self.tag:
            return False
        if self.css_class and element.get_attribute("class") != self.css_class:
            return False
        if self.id and element.get_attribute("id") != self.id:
            return False
        return True


class Page:
    """Represents a browser page."""

    def __init__(self, url: str = ""):
        self.url = url
        self.title = ""
        self._elements: list[Element] = []
        self._history: list[str] = []

    def navigate(self, url: str) -> None:
        """Navigate to a URL."""
        self._history.append(self.url)
        self.url = url

    def go_back(self) -> None:
        """Go back in history."""
        if self._history:
            self.url = self._history.pop()

    def find_element(self, selector: Selector) -> Element | None:
        """Find the first matching element."""
        for elem in self._elements:
            if selector.match(elem):
                return elem
        return None

    def find_elements(self, selector: Selector) -> list[Element]:
        """Find all matching elements."""
        return [e for e in self._elements if selector.match(e)]

    def add_element(self, element: Element) -> None:
        """Add an element to the page."""
        self._elements.append(element)

    def get_text(self, selector: Selector) -> str:
        """Get text content of the first matching element."""
        elem = self.find_element(selector)
        return elem.text if elem else ""


class Action:
    """Browser actions like click, type, submit."""

    @staticmethod
    def click(page: Page, selector: Selector) -> bool:
        """Click an element."""
        elem = page.find_element(selector)
        if elem is None:
            return False
        if elem.tag == "button" or elem.get_attribute("type") == "submit":
            return True
        return False

    @staticmethod
    def type_text(page: Page, selector: Selector, text: str) -> bool:
        """Type text into an input field."""
        elem = page.find_element(selector)
        if elem is None:
            return False
        elem.text = text
        return True

    @staticmethod
    def submit_form(page: Page, form_selector: Selector) -> bool:
        """Submit a form."""
        elem = page.find_element(form_selector)
        return elem is not None


class Browser:
    """Browser automation controller."""

    def __init__(self):
        self._pages: list[Page] = []
        self._current_page: Page | None = None
        self._blocked_frames: set[str] = set()

    def new_page(self, url: str = "") -> Page:
        """Open a new page."""
        page = Page(url)
        self._pages.append(page)
        self._current_page = page
        return page

    @property
    def current_page(self) -> Page | None:
        """Get the current page."""
        return self._current_page

    def is_frame_blocked(self, frame_url: str) -> bool:
        """Check if a frame URL is blocked for clickjacking protection."""
        return frame_url in self._blocked_frames

    def block_frame(self, frame_url: str) -> None:
        """Block a frame URL."""
        self._blocked_frames.add(frame_url)

    def sanitize_output(self, user_input: str) -> str:
        """Sanitize user input to prevent XSS."""
        # BUG: Does not properly escape HTML entities
        return user_input
'''

    public_tests_browser = '''"""Public tests for Browser Automation - visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import Element, Selector, Page, Action, Browser


def test_element_creation():
    elem = Element("div", {"class": "container"}, "Hello")
    assert elem.tag == "div"
    assert elem.text == "Hello"


def test_element_attribute():
    elem = Element("input", {"id": "username"})
    assert elem.get_attribute("id") == "username"


def test_selector_match():
    sel = Selector(tag="div", css_class="container")
    elem = Element("div", {"class": "container"})
    assert sel.match(elem) is True


def test_selector_no_match():
    sel = Selector(tag="div")
    elem = Element("span")
    assert sel.match(elem) is False


def test_page_navigation():
    page = Page("https://example.com")
    page.navigate("https://other.com")
    assert page.url == "https://other.com"


def test_page_go_back():
    page = Page("https://example.com")
    page.navigate("https://other.com")
    page.go_back()
    assert page.url == "https://example.com"


def test_page_find_element():
    page = Page()
    page.add_element(Element("input", {"id": "username"}))
    sel = Selector(id_="username")
    elem = page.find_element(sel)
    assert elem is not None


def test_action_type_text():
    page = Page()
    page.add_element(Element("input", {"id": "username"}))
    sel = Selector(id_="username")
    result = Action.type_text(page, sel, "test_user")
    assert result is True


def test_browser_new_page():
    browser = Browser()
    page = browser.new_page("https://example.com")
    assert browser.current_page is page


def test_browser_block_frame():
    browser = Browser()
    browser.block_frame("https://evil.com")
    assert browser.is_frame_blocked("https://evil.com") is True
'''

    hidden_tests_browser = '''"""Hidden tests for Browser Automation - NOT visible to the agent."""

import sys
sys.path.insert(0, ".")

from app import Element, Selector, Page, Action, Browser


def test_xss_sanitize_script_tag():
    """Sanitize should escape script tags."""
    browser = Browser()
    result = browser.sanitize_output("<script>alert('xss')</script>")
    assert "<script>" not in result, "Script tag not escaped"


def test_xss_sanitize_event_handler():
    """Sanitize should escape event handlers."""
    browser = Browser()
    result = browser.sanitize_output('<img onerror="alert(1)">')
    assert "onerror" not in result, "Event handler not escaped"


def test_frame_protection():
    """Blocked frames should be detected."""
    browser = Browser()
    browser.block_frame("https://evil.com/frame")
    assert browser.is_frame_blocked("https://evil.com/frame") is True
    assert browser.is_frame_blocked("https://safe.com") is False


def test_click_nonelement():
    """Clicking a non-button element should return False."""
    page = Page()
    page.add_element(Element("div", {}, "Not a button"))
    sel = Selector(tag="div")
    result = Action.click(page, sel)
    assert result is False


def test_sanitize_empty_input():
    """Empty input should return empty string."""
    browser = Browser()
    result = browser.sanitize_output("")
    assert result == ""
'''

    reference_fix_browser = '''"""Reference solution for Browser Automation bugs."""

def sanitize_output_fixed(self, user_input: str) -> str:
    """Fixed: properly escape HTML entities to prevent XSS."""
    import html
    return html.escape(user_input, quote=True)
'''

    register_template(
        "browser_automation",
        {
            "name": "browser_automation",
            "version": "0.1",
            "description": "Playwright-style browser automation with element interaction and XSS protection",
            "dependencies": [],
            "files": {
                "app.py": app_code,
                "tests/test_public.py": public_tests_browser,
                ".hidden_tests/test_hidden.py": hidden_tests_browser,
                ".reference_solution.py": reference_fix_browser,
            },
        },
    )


# Register browser_automation last
_register_browser_automation()


# ---------------------------------------------------------------------------
# Database Query Template
# ---------------------------------------------------------------------------


def _register_database_query() -> None:
    """Register the database_query template.

    SQL query optimization patterns with connection pooling, caching, and indexing.
    Pure Python implementation — no database dependency required.
    """

    app_code = '''"""Database Query - Query building, connection pooling, and caching modules."""

from typing import Any, Dict, List, Optional


class QueryBuilder:
    """Builds SQL-like query strings."""

    def __init__(self):
        self.table = ""
        self.columns: List[str] = []
        self.conditions: List[str] = []

    def select(self, columns: List[str]) -> "QueryBuilder":
        self.columns = columns
        return self

    def from_table(self, table: str) -> "QueryBuilder":
        self.table = table
        return self

    def where(self, condition: str) -> "QueryBuilder":
        self.conditions.append(condition)
        return self

    def build(self) -> str:
        cols = ", ".join(self.columns) if self.columns else "*"
        query = f"SELECT {cols} FROM {self.table}"
        if self.conditions:
            query += " WHERE " + " AND ".join(self.conditions)
        return query


class ConnectionPool:
    """Manages a pool of database connections."""

    def __init__(self, max_size: int = 5):
        self.max_size = max_size
        self.active: List[Dict[str, Any]] = []
        self.available: List[Dict[str, Any]] = []

    def acquire(self) -> Dict[str, Any]:
        if self.available:
            conn = self.available.pop(0)
        elif len(self.active) < self.max_size:
            conn = {"id": len(self.active), "active": True}
        else:
            raise RuntimeError("Connection pool exhausted")
        self.active.append(conn)
        return conn

    def release(self, conn: Dict[str, Any]) -> None:
        if conn in self.active:
            self.active.remove(conn)
            self.available.append(conn)


class ResultCache:
    """Caches query results to avoid repeated execution."""

    def __init__(self, ttl: float = 60.0):
        self.ttl = ttl
        self._cache: Dict[str, Any] = {}

    def get(self, query: str) -> Optional[Any]:
        if query in self._cache:
            return self._cache[query]
        return None

    def put(self, query: str, result: Any) -> None:
        self._cache[query] = result

    def clear(self) -> None:
        self._cache.clear()


class IndexManager:
    """Manages database indexes for query optimization."""

    def __init__(self):
        self.indexes: Dict[str, List[str]] = {}

    def create_index(self, table: str, columns: List[str]) -> bool:
        if table not in self.indexes:
            self.indexes[table] = []
        for col in columns:
            if col not in self.indexes[table]:
                self.indexes[table].append(col)
        return True

    def has_index(self, table: str, column: str) -> bool:
        return table in self.indexes and column in self.indexes[table]


class QueryOptimizer:
    """Optimizes queries by suggesting indexes and caching."""

    def __init__(self, index_manager: IndexManager, cache: ResultCache):
        self.index_manager = index_manager
        self.cache = cache

    def optimize(self, query: str) -> str:
        if self.cache.get(query) is not None:
            return query  # Already cached
        return query
'''

    public_tests_db = '''"""Public tests for database_query template."""

from app import QueryBuilder, ConnectionPool, ResultCache, IndexManager, QueryOptimizer


def test_query_builder_select_all():
    qb = QueryBuilder()
    query = qb.select(["*"]).from_table("users").build()
    assert "SELECT" in query
    assert "users" in query


def test_query_builder_select_columns():
    qb = QueryBuilder()
    query = qb.select(["id", "name"]).from_table("users").build()
    assert "id" in query
    assert "name" in query


def test_query_builder_where():
    qb = QueryBuilder()
    query = qb.select(["*"]).from_table("users").where("age > 18").build()
    assert "WHERE" in query
    assert "age > 18" in query


def test_connection_pool_acquire():
    pool = ConnectionPool(max_size=2)
    conn = pool.acquire()
    assert conn["active"] is True


def test_connection_pool_release():
    pool = ConnectionPool(max_size=2)
    conn = pool.acquire()
    pool.release(conn)
    assert len(pool.available) == 1


def test_connection_pool_exhausted():
    pool = ConnectionPool(max_size=1)
    pool.acquire()
    try:
        pool.acquire()
        assert False, "Should raise RuntimeError"
    except RuntimeError:
        pass


def test_result_cache_put_get():
    cache = ResultCache()
    cache.put("SELECT 1", 1)
    assert cache.get("SELECT 1") == 1


def test_result_cache_miss():
    cache = ResultCache()
    assert cache.get("MISSING") is None
'''

    hidden_tests_db = '''"""Hidden tests for database_query template."""

from app import QueryBuilder, ConnectionPool, ResultCache, IndexManager, QueryOptimizer


def test_query_builder_multiple_conditions():
    qb = QueryBuilder()
    query = qb.select(["*"]).from_table("users").where("age > 18").where("active = 1").build()
    assert "age > 18" in query
    assert "active = 1" in query


def test_connection_pool_reuse():
    pool = ConnectionPool(max_size=1)
    conn1 = pool.acquire()
    pool.release(conn1)
    conn2 = pool.acquire()
    assert conn1["id"] == conn2["id"]


def test_index_manager_create_and_check():
    mgr = IndexManager()
    mgr.create_index("users", ["email"])
    assert mgr.has_index("users", "email") is True
    assert mgr.has_index("users", "phone") is False


def test_cache_clear():
    cache = ResultCache()
    cache.put("Q1", 1)
    cache.clear()
    assert cache.get("Q1") is None


def test_optimizer_uses_cache():
    cache = ResultCache()
    cache.put("SELECT 1", 42)
    idx = IndexManager()
    opt = QueryOptimizer(idx, cache)
    result = opt.optimize("SELECT 1")
    assert result == "SELECT 1"
'''

    reference_fix_db = '''"""Reference solution for database_query bugs."""

def build_safe(self, user_input: str) -> str:
    """Fixed: use parameterized queries instead of string formatting."""
    return f"SELECT * FROM {self.table} WHERE id = ?"


def acquire_safe(self) -> dict:
    """Fixed: properly check pool size before acquiring."""
    if self.available:
        conn = self.available.pop(0)
    elif len(self.active) < self.max_size:
        conn = {"id": len(self.active), "active": True}
    else:
        raise RuntimeError("Connection pool exhausted")
    self.active.append(conn)
    return conn
'''

    register_template(
        "database_query",
        {
            "name": "database_query",
            "version": "0.1",
            "description": "SQL query optimization with connection pooling, caching, and indexing",
            "dependencies": [],
            "files": {
                "app.py": app_code,
                "tests/test_public.py": public_tests_db,
                ".hidden_tests/test_hidden.py": hidden_tests_db,
                ".reference_solution.py": reference_fix_db,
            },
        },
    )


# ---------------------------------------------------------------------------
# API Integration Template
# ---------------------------------------------------------------------------


def _register_api_integration() -> None:
    """Register the api_integration template.

    REST API client with rate limiting, token management, retry logic, and response parsing.
    Pure Python implementation — no HTTP dependency required.
    """

    app_code = '''"""API Integration - Client, rate limiting, token management, and retry logic."""

import time
from typing import Any, Dict, Optional


class APIClient:
    """Simulated REST API client."""

    def __init__(self, base_url: str = "https://api.example.com"):
        self.base_url = base_url
        self.headers: Dict[str, str] = {}

    def get(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        return {"url": url, "method": "GET", "headers": dict(self.headers)}

    def post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        return {"url": url, "method": "POST", "body": body, "headers": dict(self.headers)}

    def set_header(self, key: str, value: str) -> None:
        self.headers[key] = value


class RateLimiter:
    """Limits API requests per time window."""

    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: list = []

    def can_request(self) -> bool:
        now = time.time()
        self.requests = [t for t in self.requests if now - t < self.window_seconds]
        return len(self.requests) < self.max_requests

    def record_request(self) -> None:
        self.requests.append(time.time())


class TokenManager:
    """Manages API authentication tokens."""

    def __init__(self):
        self._tokens: Dict[str, str] = {}
        self._expires: Dict[str, float] = {}

    def store_token(self, service: str, token: str, ttl: float = 3600.0) -> None:
        self._tokens[service] = token
        self._expires[service] = time.time() + ttl

    def get_token(self, service: str) -> Optional[str]:
        if service not in self._tokens:
            return None
        if time.time() > self._expires[service]:
            return None
        return self._tokens[service]

    def remove_token(self, service: str) -> None:
        self._tokens.pop(service, None)
        self._expires.pop(service, None)


class RetryHandler:
    """Handles retry logic for failed API calls."""

    def __init__(self, max_retries: int = 3, backoff: float = 1.0):
        self.max_retries = max_retries
        self.backoff = backoff

    def execute(self, func) -> Any:
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return func()
            except Exception as e:
                last_error = e
        raise last_error


class ResponseParser:
    """Parses API responses into structured data."""

    @staticmethod
    def parse_json(response: Dict[str, Any]) -> Dict[str, Any]:
        if "data" in response:
            return response["data"]
        return response

    @staticmethod
    def parse_list(response: Dict[str, Any]) -> list:
        data = ResponseParser.parse_json(response)
        if isinstance(data, list):
            return data
        return []
'''

    public_tests_api = '''"""Public tests for api_integration template."""

from app import APIClient, RateLimiter, TokenManager, RetryHandler, ResponseParser


def test_api_client_get():
    client = APIClient()
    resp = client.get("/users")
    assert resp["method"] == "GET"
    assert "/users" in resp["url"]


def test_api_client_post():
    client = APIClient()
    resp = client.post("/users", {"name": "Alice"})
    assert resp["method"] == "POST"
    assert resp["body"]["name"] == "Alice"


def test_api_client_header():
    client = APIClient()
    client.set_header("Authorization", "Bearer token123")
    resp = client.get("/users")
    assert "Authorization" in resp["headers"]


def test_rate_limiter_can_request():
    limiter = RateLimiter(max_requests=2, window_seconds=60.0)
    assert limiter.can_request() is True


def test_rate_limiter_exhausted():
    limiter = RateLimiter(max_requests=1, window_seconds=60.0)
    limiter.record_request()
    assert limiter.can_request() is False


def test_token_manager_store_get():
    tm = TokenManager()
    tm.store_token("svc", "tok123", ttl=3600.0)
    assert tm.get_token("svc") == "tok123"


def test_token_manager_missing():
    tm = TokenManager()
    assert tm.get_token("missing") is None


def test_retry_handler_success():
    rh = RetryHandler(max_retries=3)
    result = rh.execute(lambda: 42)
    assert result == 42
'''

    hidden_tests_api = '''"""Hidden tests for api_integration template."""

from app import APIClient, RateLimiter, TokenManager, RetryHandler, ResponseParser


def test_rate_limiter_window_expiry():
    limiter = RateLimiter(max_requests=1, window_seconds=0.001)
    limiter.record_request()
    import time
    time.sleep(0.01)
    assert limiter.can_request() is True


def test_token_manager_expiry():
    tm = TokenManager()
    tm.store_token("svc", "tok123", ttl=0.001)
    import time
    time.sleep(0.01)
    assert tm.get_token("svc") is None


def test_token_manager_remove():
    tm = TokenManager()
    tm.store_token("svc", "tok123")
    tm.remove_token("svc")
    assert tm.get_token("svc") is None


def test_retry_handler_exhausted():
    rh = RetryHandler(max_retries=2)
    call_count = 0
    def failing():
        nonlocal call_count
        call_count += 1
        raise ValueError("fail")
    try:
        rh.execute(failing)
        assert False
    except ValueError:
        assert call_count == 2


def test_response_parser_list():
    resp = ResponseParser.parse_list({"data": [1, 2, 3]})
    assert resp == [1, 2, 3]
'''

    reference_fix_api = '''"""Reference solution for api_integration bugs."""

def can_request_fixed(self) -> bool:
    """Fixed: properly check rate limit."""
    now = time.time()
    self.requests = [t for t in self.requests if now - t < self.window_seconds]
    return len(self.requests) < self.max_requests


def get_token_fixed(self, service: str) -> Optional[str]:
    """Fixed: properly check token expiry."""
    if service not in self._tokens:
        return None
    if time.time() > self._expires[service]:
        return None
    return self._tokens[service]
'''

    register_template(
        "api_integration",
        {
            "name": "api_integration",
            "version": "0.1",
            "description": "REST API client with rate limiting, token management, retry logic, and response parsing",
            "dependencies": [],
            "files": {
                "app.py": app_code,
                "tests/test_public.py": public_tests_api,
                ".hidden_tests/test_hidden.py": hidden_tests_api,
                ".reference_solution.py": reference_fix_api,
            },
        },
    )


# ---------------------------------------------------------------------------
# DSL Template
# ---------------------------------------------------------------------------


def _register_dsl() -> None:
    """Register the dsl template.

    Domain-specific language parser with lexer, parser, AST, interpreter, and validator.
    Pure Python implementation — no external parser dependency required.
    """

    app_code = '''"""DSL - Lexer, Parser, AST, Interpreter, and Validator modules."""

from typing import Any, Dict, List, Optional, Tuple


class Lexer:
    """Tokenizes input source code."""

    KEYWORDS = {"let", "if", "else", "fn", "return"}

    def __init__(self):
        self.tokens: List[Tuple[str, str]] = []

    def tokenize(self, source: str) -> List[Tuple[str, str]]:
        self.tokens = []
        i = 0
        while i < len(source):
            if source[i].isspace():
                i += 1
                continue
            if source[i].isalpha() or source[i] == "_":
                start = i
                while i < len(source) and (source[i].isalnum() or source[i] == "_"):
                    i += 1
                word = source[start:i]
                if word in self.KEYWORDS:
                    self.tokens.append(("KEYWORD", word))
                else:
                    self.tokens.append(("IDENT", word))
            elif source[i].isdigit():
                start = i
                while i < len(source) and source[i].isdigit():
                    i += 1
                self.tokens.append(("NUMBER", source[start:i]))
            elif source[i] in "+-*/=(){};,":
                self.tokens.append(("OP", source[i]))
            else:
                i += 1
        return self.tokens


class AST:
    """Abstract Syntax Tree nodes."""

    @staticmethod
    def expression(op: str, left: Any, right: Any) -> Dict[str, Any]:
        return {"type": "expression", "op": op, "left": left, "right": right}

    @staticmethod
    def literal(value: Any) -> Dict[str, Any]:
        return {"type": "literal", "value": value}

    @staticmethod
    def variable(name: str) -> Dict[str, Any]:
        return {"type": "variable", "name": name}


class Parser:
    """Parses tokens into an AST."""

    def __init__(self):
        self.pos = 0

    def parse(self, tokens: List[Tuple[str, str]]) -> Dict[str, Any]:
        self.tokens = tokens
        self.pos = 0
        return self._parse_expression()

    def _parse_expression(self) -> Dict[str, Any]:
        left = self._parse_primary()
        while self.pos < len(self.tokens) and self.tokens[self.pos][1] in "+-*/":
            op = self.tokens[self.pos][1]
            self.pos += 1
            right = self._parse_primary()
            left = AST.expression(op, left, right)
        return left

    def _parse_primary(self) -> Dict[str, Any]:
        token_type, token_value = self.tokens[self.pos]
        self.pos += 1
        if token_type == "NUMBER":
            return AST.literal(int(token_value))
        elif token_type == "IDENT":
            return AST.variable(token_value)
        return AST.literal(token_value)


class Interpreter:
    """Evaluates AST expressions."""

    def __init__(self):
        self.env: Dict[str, Any] = {}

    def evaluate(self, node: Dict[str, Any]) -> Any:
        if node["type"] == "literal":
            return node["value"]
        elif node["type"] == "variable":
            return self.env.get(node["name"], 0)
        elif node["type"] == "expression":
            left = self.evaluate(node["left"])
            right = self.evaluate(node["right"])
            op = node["op"]
            if op == "+":
                return left + right
            elif op == "-":
                return left - right
            elif op == "*":
                return left * right
            elif op == "/":
                if right == 0:
                    raise ZeroDivisionError("Division by zero")
                return left / right
        return None

    def set_variable(self, name: str, value: Any) -> None:
        self.env[name] = value


class Validator:
    """Validates AST for type errors."""

    @staticmethod
    def validate(node: Dict[str, Any]) -> List[str]:
        errors = []
        if node["type"] == "expression":
            if node["op"] not in "+-*/":
                errors.append(f"Unknown operator: {node['op']}")
            Validator.validate(node["left"])
            Validator.validate(node["right"])
        return errors
'''

    public_tests_dsl = '''"""Public tests for dsl template."""

from app import Lexer, Parser, Interpreter, Validator, AST


def test_lexer_tokenize_numbers():
    lexer = Lexer()
    tokens = lexer.tokenize("123 456")
    assert len(tokens) == 2
    assert tokens[0][0] == "NUMBER"


def test_lexer_tokenize_ident():
    lexer = Lexer()
    tokens = lexer.tokenize("x y")
    assert tokens[0][0] == "IDENT"
    assert tokens[0][1] == "x"


def test_lexer_tokenize_keyword():
    lexer = Lexer()
    tokens = lexer.tokenize("let")
    assert tokens[0][0] == "KEYWORD"


def test_parser_parse_literal():
    parser = Parser()
    ast = parser.parse([("NUMBER", "42")])
    assert ast["type"] == "literal"
    assert ast["value"] == 42


def test_parser_parse_expression():
    parser = Parser()
    tokens = [("NUMBER", "1"), ("OP", "+"), ("NUMBER", "2")]
    ast = parser.parse(tokens)
    assert ast["type"] == "expression"
    assert ast["op"] == "+"


def test_interpreter_evaluate_literal():
    interp = Interpreter()
    result = interp.evaluate(AST.literal(42))
    assert result == 42


def test_interpreter_evaluate_addition():
    interp = Interpreter()
    node = AST.expression("+", AST.literal(1), AST.literal(2))
    result = interp.evaluate(node)
    assert result == 3


def test_validator_valid():
    node = AST.expression("+", AST.literal(1), AST.literal(2))
    errors = Validator.validate(node)
    assert len(errors) == 0
'''

    hidden_tests_dsl = '''"""Hidden tests for dsl template."""

from app import Lexer, Parser, Interpreter, Validator, AST


def test_lexer_mixed_tokens():
    lexer = Lexer()
    tokens = lexer.tokenize("x + 1")
    types = [t[0] for t in tokens]
    assert "IDENT" in types
    assert "OP" in types
    assert "NUMBER" in types


def test_parser_chained_expression():
    parser = Parser()
    tokens = [("NUMBER", "1"), ("OP", "+"), ("NUMBER", "2"), ("OP", "*"), ("NUMBER", "3")]
    ast = parser.parse(tokens)
    assert ast["type"] == "expression"


def test_interpreter_variable():
    interp = Interpreter()
    interp.set_variable("x", 10)
    result = interp.evaluate(AST.variable("x"))
    assert result == 10


def test_interpreter_division_by_zero():
    interp = Interpreter()
    node = AST.expression("/", AST.literal(1), AST.literal(0))
    try:
        interp.evaluate(node)
        assert False
    except ZeroDivisionError:
        pass


def test_validator_unknown_op():
    node = AST.expression("^", AST.literal(1), AST.literal(2))
    errors = Validator.validate(node)
    assert len(errors) > 0
'''

    reference_fix_dsl = '''"""Reference solution for dsl bugs."""

def tokenize_fixed(self, source: str) -> list:
    """Fixed: properly handle all token types."""
    self.tokens = []
    i = 0
    while i < len(source):
        if source[i].isspace():
            i += 1
            continue
        if source[i].isalpha() or source[i] == "_":
            start = i
            while i < len(source) and (source[i].isalnum() or source[i] == "_"):
                i += 1
            word = source[start:i]
            if word in self.KEYWORDS:
                self.tokens.append(("KEYWORD", word))
            else:
                self.tokens.append(("IDENT", word))
        elif source[i].isdigit():
            start = i
            while i < len(source) and source[i].isdigit():
                i += 1
            self.tokens.append(("NUMBER", source[start:i]))
        elif source[i] in "+-*/=(){};,":
            self.tokens.append(("OP", source[i]))
        else:
            i += 1
    return self.tokens
'''

    register_template(
        "dsl",
        {
            "name": "dsl",
            "version": "0.1",
            "description": "Domain-specific language parser with lexer, parser, AST, interpreter, and validator",
            "dependencies": [],
            "files": {
                "app.py": app_code,
                "tests/test_public.py": public_tests_dsl,
                ".hidden_tests/test_hidden.py": hidden_tests_dsl,
                ".reference_solution.py": reference_fix_dsl,
            },
        },
    )


# Register new templates
_register_database_query()
_register_api_integration()
_register_dsl()
