"""Seeder: deterministic bug mutations for world generation.

Each mutation defines how to transform a correct codebase into a broken one.
Mutations are applied by text replacement to ensure reproducibility.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Mutation Pattern Dataclass
# ---------------------------------------------------------------------------


@dataclass
class MutationPattern:
    """A mutation pattern for transforming correct code into buggy code."""

    name: str
    search_pattern: str
    replace_with: str | None
    reference_fix: str = ""
    capabilities: list[str] = field(default_factory=list)
    difficulty: int = 1
    description: str = ""


# ---------------------------------------------------------------------------
# Mutation Registry
# ---------------------------------------------------------------------------

_mutations: dict[str, dict[str, Any]] = {}


def register_mutation(mutation: dict[str, Any]) -> None:
    """Register a bug mutation.

    Args:
        mutation: Mutation definition with 'id', 'name', 'description',
                  'target_file', 'search_pattern', 'replace_with'.
    """
    _mutations[mutation["id"]] = mutation


def get_mutation(mutation_id: str) -> dict[str, Any] | None:
    """Get a mutation by ID.

    Args:
        mutation_id: The mutation identifier.

    Returns:
        Mutation definition or None.
    """
    return _mutations.get(mutation_id)


def list_mutations() -> list[str]:
    """List all registered mutation IDs.

    Returns:
        Sorted list of mutation IDs.
    """
    return sorted(_mutations.keys())


# ---------------------------------------------------------------------------
# Mutation Definitions
# ---------------------------------------------------------------------------


def _register_mutations() -> None:
    """Register all seed mutations."""

    # Mutation 1: Pagination boundary error
    register_mutation(
        {
            "id": "pagination_boundary",
            "name": "Pagination Boundary Error",
            "description": (
                "The list_tasks method returns incorrect results when the "
                "requested page exceeds the available number of pages. "
                "Instead of returning an empty list, it raises an IndexError "
                "or returns wrong data."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"        # BUG: Pagination boundary handling is incorrect\n"
                r"        start = \(page - 1\) \* page_size\n"
                r"        end = start \+ page_size\n"
                r"        page_tasks = filtered\[start:end\]"
            ),
            "replace_with": (
                "        # BUG: Pagination boundary handling is incorrect\n"
                "        if page > (len(filtered) + page_size - 1) // page_size:\n"
                "            raise IndexError(\n"
                '                f"Page {page} exceeds total pages "\n'
                '                f"{(len(filtered) + page_size - 1) // page_size}"\n'
                "            )\n"
                "        start = (page - 1) * page_size\n"
                "        end = start + page_size\n"
                "        page_tasks = filtered[start:end]"
            ),
            "reference_fix": (
                "        start = (page - 1) * page_size\n"
                "        end = start + page_size\n"
                "        page_tasks = filtered[start:end]"
            ),
            "capabilities": ["debugging", "edge_case_reasoning"],
            "difficulty": 2,
        }
    )

    # Mutation 2: Empty search query handling
    register_mutation(
        {
            "id": "empty_search",
            "name": "Empty Search Query Error",
            "description": (
                "The list_tasks method returns an empty result set when "
                "search is an empty string, instead of returning all tasks. "
                "The empty string is treated as a search term that matches nothing."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"        # Search in title and description\n"
                r"        if search is not None:\n"
                r"            search_lower = search\.lower\(\)\n"
                r"            filtered = \[\n"
                r"                t for t in filtered\n"
                r"                if search_lower in t\.title\.lower\(\) or search_lower in t\.description\.lower\(\)\n"
                r"            \]"
            ),
            "replace_with": (
                "        # Search in title and description\n"
                "        if search is not None:\n"
                "            search_lower = search.lower()\n"
                "            if search_lower == '':\n"
                "                filtered = []  # BUG: empty search returns nothing\n"
                "            else:\n"
                "                filtered = [\n"
                "                    t for t in filtered\n"
                "                    if search_lower in t.title.lower() or search_lower in t.description.lower()\n"
                "                ]"
            ),
            "reference_fix": (
                "        # Search in title and description\n"
                "        if search is not None:\n"
                "            search_lower = search.lower()\n"
                "            filtered = [\n"
                "                t for t in filtered\n"
                "                if search_lower in t.title.lower() or search_lower in t.description.lower()\n"
                "            ]"
            ),
            "capabilities": ["debugging", "edge_case_reasoning"],
            "difficulty": 2,
        }
    )

    # Mutation 3: Duplicate record handling
    register_mutation(
        {
            "id": "duplicate_records",
            "name": "Duplicate Record Handling Error",
            "description": (
                "The add_task method silently skips tasks with duplicate titles, "
                "instead of allowing multiple tasks with the same title. "
                "This causes data loss when users create tasks with identical names."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def add_task\(self, title: str, description: str = \"\", status: str = \"open\"\) -> Task:\n"
                r"        \"\"\"Add a new task.\"\"\"\n"
                r"        task = Task\(self\._next_id, title, description, status\)\n"
                r"        self\._tasks\.append\(task\)\n"
                r"        self\._next_id \+= 1\n"
                r"        return task"
            ),
            "replace_with": (
                '    def add_task(self, title: str, description: str = "", status: str = "open") -> Task:\n'
                '        """Add a new task."""\n'
                "        # BUG: Skip tasks with duplicate titles\n"
                "        for existing in self._tasks:\n"
                "            if existing.title == title:\n"
                "                return existing\n"
                "        task = Task(self._next_id, title, description, status)\n"
                "        self._tasks.append(task)\n"
                "        self._next_id += 1\n"
                "        return task"
            ),
            "reference_fix": (
                '    def add_task(self, title: str, description: str = "", status: str = "open") -> Task:\n'
                '        """Add a new task."""\n'
                "        task = Task(self._next_id, title, description, status)\n"
                "        self._tasks.append(task)\n"
                "        self._next_id += 1\n"
                "        return task"
            ),
            "capabilities": ["debugging", "testing"],
            "difficulty": 2,
        }
    )

    # Mutation 4: Null handling crash (data_pipeline)
    register_mutation(
        {
            "id": "null_handling",
            "name": "Null Value Crash",
            "description": (
                "The DataValidator.validate method raises ValueError when "
                "encountering None in a required field, instead of returning "
                "an error message. This crashes the pipeline."
            ),
            "target_file": "pipeline.py",
            "search_pattern": (
                r"            elif record\[field\] is None:\n"
                r"                errors\.append\(f\"Null value in required field: \{field\}\"\)"
            ),
            "replace_with": (
                "            elif record[field] is None:\n"
                "                # BUG: Should handle None values gracefully, not crash\n"
                '                raise ValueError(f"Null value in required field: {field}")'
            ),
            "reference_fix": (
                "            elif record[field] is None:\n"
                '                errors.append(f"Null value in required field: {field}")'
            ),
            "capabilities": ["debugging", "edge_case_reasoning"],
            "difficulty": 2,
        }
    )

    # Mutation 5: Date parsing missing ISO 8601 (data_pipeline)
    register_mutation(
        {
            "id": "date_parsing",
            "name": "ISO 8601 Date Parsing Failure",
            "description": (
                "The DateParser.parse method does not handle ISO 8601 dates "
                "with timezone offsets (e.g., +05:30 or Z suffix), returning "
                "None instead of parsing them."
            ),
            "target_file": "pipeline.py",
            "search_pattern": (
                r"        # Handle ISO 8601 with timezone\n"
                r"        try:\n"
                r"            cleaned = date_str\.replace\(\"Z\", \"\+00:00\"\)\n"
                r"            return datetime\.fromisoformat\(cleaned\)\n"
                r"        except ValueError:\n"
                r"            pass\n"
                r"        return None"
            ),
            "replace_with": (
                "        # BUG: Does not handle ISO 8601 with timezone offsets\n"
                '        # e.g., "2024-01-15T10:30:00+05:30"\n'
                "        return None"
            ),
            "reference_fix": (
                "        # Handle ISO 8601 with timezone\n"
                "        try:\n"
                '            cleaned = date_str.replace("Z", "+00:00")\n'
                "            return datetime.fromisoformat(cleaned)\n"
                "        except ValueError:\n"
                "            pass\n"
                "        return None"
            ),
            "capabilities": ["debugging", "edge_case_reasoning", "data_handling"],
            "difficulty": 2,
        }
    )

    # Mutation 6: Duplicate detection single key (data_pipeline)
    register_mutation(
        {
            "id": "duplicate_detection",
            "name": "Composite Key Duplicate Detection",
            "description": (
                "The detect_duplicates method only checks the first key field "
                "instead of using the full composite key, causing false positives "
                "where records with different composite keys are treated as duplicates."
            ),
            "target_file": "pipeline.py",
            "search_pattern": (
                r"        seen = set\(\)\n"
                r"        unique = \[\]\n"
                r"        for record in records:\n"
                r"            key = tuple\(record\.get\(f, \"\"\) for f in key_fields\)\n"
                r"            if key not in seen:\n"
                r"                seen\.add\(key\)\n"
                r"                unique\.append\(record\)\n"
                r"        return unique"
            ),
            "replace_with": (
                "        # BUG: Only checks first key field, ignores composite key\n"
                "        seen = set()\n"
                "        unique = []\n"
                "        for record in records:\n"
                '            key = record.get(key_fields[0], "")\n'
                "            if key not in seen:\n"
                "                seen.add(key)\n"
                "                unique.append(record)\n"
                "        return unique"
            ),
            "reference_fix": (
                "        seen = set()\n"
                "        unique = []\n"
                "        for record in records:\n"
                '            key = tuple(record.get(f, "") for f in key_fields)\n'
                "            if key not in seen:\n"
                "                seen.add(key)\n"
                "                unique.append(record)\n"
                "        return unique"
            ),
            "capabilities": ["debugging", "data_handling", "python_testing"],
            "difficulty": 3,
        }
    )

    # Mutation 7: Flask App - Session timeout calculates as 0
    register_mutation(
        {
            "id": "session_timeout",
            "name": "Session Timeout Zero",
            "description": (
                "The SessionManager calculates session timeout as 0 seconds "
                "instead of the configured duration, causing sessions to expire "
                "immediately after creation."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def _calculate_timeout\(self\) -> int:\n"
                r"        \"\"\"Calculate session timeout duration.\"\"\"\n"
                r"        return self\._timeout"
            ),
            "replace_with": (
                "    def _calculate_timeout(self) -> int:\n"
                '        """Calculate session timeout duration."""\n'
                "        # BUG: Timeout calculation returns 0 instead of configured value\n"
                "        return 0"
            ),
            "reference_fix": (
                "    def _calculate_timeout(self) -> int:\n"
                '        """Calculate session timeout duration."""\n'
                "        return self._timeout"
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 8: Flask App - Password stored as plaintext
    register_mutation(
        {
            "id": "password_hash",
            "name": "Plaintext Password Storage",
            "description": (
                "The AuthManager stores passwords as plaintext instead of "
                "hashing them, exposing user credentials if the database is compromised."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def _hash_password\(self, password: str\) -> str:\n"
                r"        \"\"\"Hash a password using SHA-256 with salt.\"\"\"\n"
                r"        salt = os\.urandom\(16\)\.hex\(\)\n"
                r"        hashed = hashlib\.sha256\(\(salt \+ password\)\.encode\(\)\)\.hexdigest\(\)\n"
                r"        return f\"{salt}:{hashed}\""
            ),
            "replace_with": (
                "    def _hash_password(self, password: str) -> str:\n"
                '        """Hash a password using SHA-256 with salt."""\n'
                "        # BUG: Store plaintext password instead of hashing\n"
                "        return password"
            ),
            "reference_fix": (
                "    def _hash_password(self, password: str) -> str:\n"
                '        """Hash a password using SHA-256 with salt."""\n'
                "        salt = os.urandom(16).hex()\n"
                "        hashed = hashlib.sha256((salt + password).encode()).hexdigest()\n"
                '        return f"{salt}:{hashed}"'
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 9: Flask App - CSRF token validation always passes
    register_mutation(
        {
            "id": "csrf_token",
            "name": "CSRF Token Bypass",
            "description": (
                "The CSRFProtector.validate_token method always returns True "
                "without actually checking the token, allowing any CSRF attack."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def validate_token\(self, token: str\) -> bool:\n"
                r"        \"\"\"Validate a CSRF token.\"\"\"\n"
                r"        # BUG: csrf_token - always returns True without checking\n"
                r"        if token in self\._tokens:\n"
                r"            return True\n"
                r"        return False"
            ),
            "replace_with": (
                "    def validate_token(self, token: str) -> bool:\n"
                '        """Validate a CSRF token."""\n'
                "        # BUG: Always accept any token\n"
                "        return True"
            ),
            "reference_fix": (
                "    def validate_token(self, token: str) -> bool:\n"
                '        """Validate a CSRF token."""\n'
                "        if token in self._tokens:\n"
                "            return True\n"
                "        return False"
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 1,
        }
    )

    # Mutation 12: Express API - CORS accepts any origin
    register_mutation(
        {
            "id": "cors_bypass",
            "name": "CORS Origin Bypass",
            "description": (
                "The CorsHandler.get_headers method accepts any origin "
                "instead of checking against the allowed origins list, "
                "allowing cross-site requests from malicious domains."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def get_headers\(self, request_origin: str\) -> Dict\[str, str\]:\n"
                r"        \"\"\"Get CORS headers for a request.\"\"\"\n"
                r"        # BUG: cors_bypass - accepts any origin\n"
                r"        headers = \{\}\n"
                r"        if request_origin:\n"
                r"            headers\[\"Access-Control-Allow-Origin\"\] = request_origin\n"
                r"        headers\[\"Access-Control-Allow-Methods\"\] = \"GET, POST, PUT, DELETE, OPTIONS\"\n"
                r"        headers\[\"Access-Control-Allow-Headers\"\] = \"Content-Type, Authorization\"\n"
                r"        return headers"
            ),
            "replace_with": (
                "    def get_headers(self, request_origin: str) -> Dict[str, str]:\n"
                '        """Get CORS headers for a request."""\n'
                "        # BUG: Accept any origin without checking allowed list\n"
                "        headers = {}\n"
                "        if request_origin:\n"
                '            headers["Access-Control-Allow-Origin"] = request_origin\n'
                '        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"\n'
                '        headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"\n'
                "        return headers"
            ),
            "reference_fix": (
                "    def get_headers(self, request_origin: str) -> Dict[str, str]:\n"
                '        """Get CORS headers for a request."""\n'
                "        headers = {}\n"
                "        if request_origin and self.is_origin_allowed(request_origin):\n"
                '            headers["Access-Control-Allow-Origin"] = request_origin\n'
                '        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"\n'
                '        headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"\n'
                "        return headers"
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 13: Express API - Rate limiter disabled
    register_mutation(
        {
            "id": "rate_limit_off",
            "name": "Rate Limiter Disabled",
            "description": (
                "The RateLimiter.is_allowed method always returns True, "
                "effectively disabling rate limiting and allowing unlimited requests."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"        # BUG: rate_limit_off - always allows requests\n"
                r"        if len\(self\._requests\[client_id\]\) < self\._max_requests:\n"
                r"            self\._requests\[client_id\]\.append\(now\)\n"
                r"            return True\n"
                r"        return False"
            ),
            "replace_with": (
                "        # BUG: Rate limiting disabled - always allow\n"
                "        self._requests[client_id].append(now)\n"
                "        return True"
            ),
            "reference_fix": (
                "        if len(self._requests[client_id]) >= self._max_requests:\n"
                "            return False\n"
                "        self._requests[client_id].append(now)\n"
                "        return True"
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 1,
        }
    )

    # Mutation 14: Express API - Input not sanitized
    register_mutation(
        {
            "id": "input_injection",
            "name": "Input Injection Vulnerability",
            "description": (
                "The RequestValidator.sanitize_input method returns the input "
                "unchanged, allowing XSS and SQL injection attacks."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    @staticmethod\n"
                r"    def sanitize_input\(value: str\) -> str:\n"
                r"        \"\"\"Sanitize a string input by removing potentially dangerous characters.\"\"\"\n"
                r"        # BUG: input_injection - does not sanitize input\n"
                r"        return value"
            ),
            "replace_with": (
                "    @staticmethod\n"
                "    def sanitize_input(value: str) -> str:\n"
                '        """Sanitize a string input by removing potentially dangerous characters."""\n'
                "        # BUG: No sanitization applied\n"
                "        return value"
            ),
            "reference_fix": (
                "    @staticmethod\n"
                "    def sanitize_input(value: str) -> str:\n"
                '        """Sanitize a string input by removing potentially dangerous characters."""\n'
                "        import re as re_module\n"
                "        value = re_module.sub(r'<script[^>]*>.*?</script>', '', value, flags=re_module.IGNORECASE)\n"
                "        value = re_module.sub(r\"(DROP|DELETE|INSERT|UPDATE|SELECT)\\s+\", '', value, flags=re_module.IGNORECASE)\n"
                "        value = value.replace(\"'\", '').replace('\"', '').replace(';', '')\n"
                "        return value"
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 15: Django App - SQL injection via string formatting
    register_mutation(
        {
            "id": "sql_injection",
            "name": "SQL Injection via String Formatting",
            "description": (
                "The QuerySet.raw_query method uses string replacement for "
                "parameters instead of proper parameterization, allowing SQL injection."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def raw_query\(self, sql: str, params: Tuple = \(\)\) -> List\[Dict\[str, Any\]\]:\n"
                r"        \"\"\"Execute a raw SQL-like query string\.\n"
                r"\n"
                r"        WARNING: This method constructs queries from strings\.\n"
                r"        \"\"\"\n"
                r"        # BUG: sql_injection - no parameterization\n"
                r"        query = sql\n"
                r"        for param in params:\n"
                r"            query = query\.replace\(\"\\?\", str\(param\), 1\)\n"
                r"        # Simulate query execution by parsing simple SELECT\n"
                r"        return self\._records\[:\]  # Simplified for pure Python"
            ),
            "replace_with": (
                "    def raw_query(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:\n"
                '        """Execute a raw SQL-like query string.\n'
                "\n"
                "        WARNING: This method constructs queries from strings.\n"
                '        """\n'
                "        # BUG: String concatenation allows SQL injection\n"
                "        query = sql\n"
                "        for param in params:\n"
                '            query = query.replace("?", str(param), 1)\n'
                "        # Simulate query execution by parsing simple SELECT\n"
                "        return self._records[:]  # Simplified for pure Python"
            ),
            "reference_fix": (
                "    def raw_query(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:\n"
                '        """Execute a raw SQL-like query string.\n'
                "\n"
                "        WARNING: This method constructs queries from strings.\n"
                '        """\n'
                "        # Use parameterized queries in production\n"
                "        return self._records[:]"
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 3,
        }
    )

    # Mutation 16: Django App - CSRF missing on POST
    register_mutation(
        {
            "id": "csrf_missing",
            "name": "CSRF Token Missing on POST",
            "description": (
                "The View.post method does not check CSRF tokens before "
                "processing POST requests, and _check_csrf always returns True."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def _check_csrf\(self, request: Dict\[str, Any\]\) -> bool:\n"
                r"        \"\"\"Check CSRF token validity.\"\"\"\n"
                r"        token = request\.get\(\"csrf_token\"\)\n"
                r"        if not token:\n"
                r"            return False\n"
                r"        # BUG: csrf_missing - always returns True\n"
                r"        return True"
            ),
            "replace_with": (
                "    def _check_csrf(self, request: Dict[str, Any]) -> bool:\n"
                '        """Check CSRF token validity."""\n'
                "        # BUG: Always returns True regardless of token\n"
                "        return True"
            ),
            "reference_fix": (
                "    def _check_csrf(self, request: Dict[str, Any]) -> bool:\n"
                '        """Check CSRF token validity."""\n'
                '        token = request.get("csrf_token")\n'
                "        if not token or not self._csrf_token:\n"
                "            return False\n"
                "        return token == self._csrf_token"
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 17: Django App - Open redirect vulnerability
    register_mutation(
        {
            "id": "open_redirect",
            "name": "Open Redirect Vulnerability",
            "description": (
                "The View.redirect method does not validate the target URL, "
                "allowing redirects to external malicious sites."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def redirect\(self, url: str\) -> Dict\[str, Any\]:\n"
                r"        \"\"\"Redirect to a URL.\"\"\"\n"
                r"        # BUG: open_redirect - no URL validation\n"
                r"        return \{\"status\": 302, \"location\": url\}"
            ),
            "replace_with": (
                "    def redirect(self, url: str) -> Dict[str, Any]:\n"
                '        """Redirect to a URL."""\n'
                "        # BUG: No validation of redirect target\n"
                '        return {"status": 302, "location": url}'
            ),
            "reference_fix": (
                "    def redirect(self, url: str) -> Dict[str, Any]:\n"
                '        """Redirect to a URL."""\n'
                '        if url and not url.startswith("/"):\n'
                '            return {"status": 400, "error": "Invalid redirect URL"}\n'
                '        return {"status": 302, "location": url}'
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 1,
        }
    )


    # Mutation 16: TypeScript API - Error leak (stack trace exposed)
    register_mutation(
        {
            "id": "error_leak",
            "name": "Stack Trace Exposure",
            "description": (
                "The ErrorHandler exposes full stack traces in error responses, "
                "leaking internal implementation details to attackers."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    @staticmethod\n"
                r"    def handle_exception\(exc: Exception\) -> Dict\[str, Any\]:\n"
                r"        \"\"\"Handle an exception and return an error response\.\"\"\"\n"
                r"        return \{\n"
                r"            \"status\": 500,\n"
                r"            \"error\": \"Internal Server Error\",\n"
                r"        \}"
            ),
            "replace_with": (
                "    @staticmethod\n"
                "    def handle_exception(exc: Exception) -> Dict[str, Any]:\n"
                '        """Handle an exception and return an error response."""\n'
                "        import traceback\n"
                "        # BUG: Exposes stack trace in production\n"
                "        return {\n"
                '            "status": 500,\n'
                '            "error": "Internal Server Error",\n'
                '            "details": traceback.format_exc(),\n'
                "        }"
            ),
            "reference_fix": (
                "    @staticmethod\n"
                "    def handle_exception(exc: Exception) -> Dict[str, Any]:\n"
                '        """Handle an exception and return an error response."""\n'
                "        return {\n"
                '            "status": 500,\n'
                '            "error": "Internal Server Error",\n'
                "        }"
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 1,
        }
    )

    # Mutation 17: TypeScript API - Input validation bypass
    register_mutation(
        {
            "id": "input_validation",
            "name": "Input Validation Bypass",
            "description": (
                "The InputValidator.sanitize method doesn't properly escape "
                "all dangerous characters, allowing XSS attacks."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    @staticmethod\n"
                r"    def sanitize\(value: str\) -> str:\n"
                r"        \"\"\"Sanitize input by removing potentially dangerous characters\.\"\"\"\n"
                r"        # Remove HTML tags\n"
                r"        value = re\.sub\(r'<\[^>\]\*>', '', value\)\n"
                r"        # Escape special characters\n"
                r"        value = value\.replace\('&', '&amp;'\)\n"
                r"        value = value\.replace\('\"', '&quot;'\)\n"
                r"        value = value\.replace\(\"'\", '&#x27;'\)\n"
                r"        value = value\.replace\('<', '&lt;'\)\n"
                r"        value = value\.replace\('>', '&gt;'\)\n"
                r"        return value"
            ),
            "replace_with": (
                "    @staticmethod\n"
                "    def sanitize(value: str) -> str:\n"
                '        """Sanitize input by removing potentially dangerous characters."""\n'
                "        # BUG: Only removes HTML tags, doesn't escape special chars\n"
                "        value = re.sub(r'<[^>]*>', '', value)\n"
                "        return value"
            ),
            "reference_fix": (
                "    @staticmethod\n"
                "    def sanitize(value: str) -> str:\n"
                '        """Sanitize input by removing potentially dangerous characters."""\n'
                "        # Remove HTML tags\n"
                "        value = re.sub(r'<[^>]*>', '', value)\n"
                "        # Escape special characters\n"
                "        value = value.replace('&', '&amp;')\n"
                "        value = value.replace('\"', '&quot;')\n"
                "        value = value.replace(\"'\", '&#x27;')\n"
                "        value = value.replace('<', '&lt;')\n"
                "        value = value.replace('>', '&gt;')\n"
                "        return value"
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 18: Go Service - Nil pointer dereference
    register_mutation(
        {
            "id": "nil_pointer",
            "name": "Nil Pointer Dereference",
            "description": (
                "The Handler.handle_post method doesn't check for nil body "
                "before accessing it, causing a crash when body is None."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def handle_post\(self, request: Dict\[str, Any\]\) -> Dict\[str, Any\]:\n"
                r"        \"\"\"Handle POST request\.\"\"\"\n"
                r"        body = request\.get\(\"body\"\)\n"
                r"        if body is None:\n"
                r"            return \{\"status\": 400, \"error\": \"Missing request body\"\}\n"
                r"        key = body\.get\(\"key\"\)\n"
                r"        if key is None:\n"
                r"            return \{\"status\": 400, \"error\": \"Missing key in body\"\}\n"
                r"        value = body\.get\(\"value\"\)\n"
                r"        self\.store\.set\(key, value\)\n"
                r"        return \{\"status\": 201, \"data\": \{\"key\": key\}\}"
            ),
            "replace_with": (
                "    def handle_post(self, request: Dict[str, Any]) -> Dict[str, Any]:\n"
                '        """Handle POST request."""\n'
                "        body = request.get(\"body\")\n"
                "        # BUG: No nil check - will fail if body is None\n"
                '        key = body["key"]\n'
                '        value = body["value"]\n'
                "        self.store.set(key, value)\n"
                '        return {"status": 201, "data": {"key": key}}'
            ),
            "reference_fix": (
                "    def handle_post(self, request: Dict[str, Any]) -> Dict[str, Any]:\n"
                '        """Handle POST request."""\n'
                "        body = request.get(\"body\")\n"
                "        if body is None:\n"
                '            return {"status": 400, "error": "Missing request body"}\n'
                "        key = body.get(\"key\")\n"
                "        if key is None:\n"
                '            return {"status": 400, "error": "Missing key in body"}\n'
                "        value = body.get(\"value\")\n"
                "        self.store.set(key, value)\n"
                '        return {"status": 201, "data": {"key": key}}'
            ),
            "capabilities": ["debugging", "error_handling", "python_testing"],
            "difficulty": 1,
        }
    )

    # Mutation 19: Go Service - Resource leak (connection not closed)
    register_mutation(
        {
            "id": "resource_leak",
            "name": "Resource Leak",
            "description": (
                "The Handler.handle_resource method doesn't close the connection "
                "on the success path, leaking resources."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def handle_resource\(self, request: Dict\[str, Any\]\) -> Dict\[str, Any\]:\n"
                r"        \"\"\"Handle a resource request that opens a connection\.\"\"\"\n"
                r"        conn = Store\(\)\n"
                r"        conn\.connect\(\)\n"
                r"        try:\n"
                r"            key = request\.get\(\"key\", \"\"\)\n"
                r"            value = conn\.get\(key\)\n"
                r"            if value is None:\n"
                r"                return \{\"status\": 404, \"error\": \"Not found\"\}\n"
                r"            return \{\"status\": 200, \"data\": value\}\n"
                r"        finally:\n"
                r"            conn\.disconnect\(\)"
            ),
            "replace_with": (
                "    def handle_resource(self, request: Dict[str, Any]) -> Dict[str, Any]:\n"
                '        """Handle a resource request that opens a connection."""\n'
                "        conn = Store()\n"
                "        conn.connect()\n"
                "        try:\n"
                '            key = request.get("key", "")\n'
                "            value = conn.get(key)\n"
                "            if value is None:\n"
                '                return {"status": 404, "error": "Not found"}\n'
                '            # BUG: conn.disconnect() is missing on success path\n'
                '            return {"status": 200, "data": value}\n'
                "        except Exception as e:\n"
                "            conn.disconnect()\n"
                '            return {"status": 500, "error": str(e)}'
            ),
            "reference_fix": (
                "    def handle_resource(self, request: Dict[str, Any]) -> Dict[str, Any]:\n"
                '        """Handle a resource request that opens a connection."""\n'
                "        conn = Store()\n"
                "        conn.connect()\n"
                "        try:\n"
                '            key = request.get("key", "")\n'
                "            value = conn.get(key)\n"
                "            if value is None:\n"
                '                return {"status": 404, "error": "Not found"}\n'
                '            return {"status": 200, "data": value}\n'
                "        finally:\n"
                "            conn.disconnect()"
            ),
            "capabilities": ["debugging", "resource_management", "python_testing"],
            "difficulty": 2,
        }
    )


    # Mutation 19: React App - XSS injection (no sanitization)
    register_mutation(
        {
            "id": "xss_injection",
            "name": "XSS Injection via Missing Sanitization",
            "description": (
                "The FormHandler.sanitize method returns the input unchanged, "
                "allowing XSS attacks through unsanitized form input."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def sanitize\(self, value: str\) -> str:\n"
                r"        \"\"\"Sanitize form input to prevent XSS.\"\"\"\n"
                r"        # BUG: xss_injection - doesn't actually sanitize\n"
                r"        return value"
            ),
            "replace_with": (
                "    def sanitize(self, value: str) -> str:\n"
                '        """Sanitize form input to prevent XSS."""\n'
                "        # BUG: Returns input unchanged, allowing XSS\n"
                "        return value"
            ),
            "reference_fix": (
                "    def sanitize(self, value: str) -> str:\n"
                '        """Sanitize form input to prevent XSS."""\n'
                "        import re\n"
                '        value = re.sub(r"<script[^>]*>.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)\n'
                '        value = re.sub(r"\s+on\w+\s*=[\'"][^\'"]*[\'"]", "", value, flags=re.IGNORECASE)\n'
                '        value = value.replace("<", "&lt;").replace(">", "&gt;")\n'
                "        return value"
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 20: Spring Service - Transaction leak (no rollback)
    register_mutation(
        {
            "id": "transaction_leak",
            "name": "Transaction Leak on Error",
            "description": (
                "The Service.create_entity method doesn't rollback the transaction "
                "when an error occurs, leaving the transaction in an active state."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def create_entity\(self, data: Dict\[str, Any\]\) -> str:\n"
                r"        \"\"\"Create a new entity within a transaction.\"\"\"\n"
                r"        self\.transaction_manager\.begin\(\)\n"
                r"        try:\n"
                r"            entity_id = self\.repository\.save\(data\)\n"
                r"            self\.transaction_manager\.commit\(\)\n"
                r"            return entity_id\n"
                r"        except Exception:\n"
                r"            # BUG: transaction_leak - doesn't rollback on error\n"
                r"            raise"
            ),
            "replace_with": (
                "    def create_entity(self, data: Dict[str, Any]) -> str:\n"
                '        """Create a new entity within a transaction."""\n'
                "        self.transaction_manager.begin()\n"
                "        try:\n"
                "            entity_id = self.repository.save(data)\n"
                "            self.transaction_manager.commit()\n"
                "            return entity_id\n"
                "        except Exception:\n"
                "            # BUG: Transaction is not rolled back on error\n"
                "            raise"
            ),
            "reference_fix": (
                "    def create_entity(self, data: Dict[str, Any]) -> str:\n"
                '        """Create a new entity within a transaction."""\n'
                "        self.transaction_manager.begin()\n"
                "        try:\n"
                "            entity_id = self.repository.save(data)\n"
                "            self.transaction_manager.commit()\n"
                "            return entity_id\n"
                "        except Exception:\n"
                "            self.transaction_manager.rollback()\n"
                "            raise"
            ),
            "capabilities": ["debugging", "resource_management", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 21: Spring Service - N+1 query in list_entities
    register_mutation(
        {
            "id": "n_plus_one",
            "name": "N+1 Query in Entity Listing",
            "description": (
                "The Service.list_entities method loads each entity individually "
                "instead of using a batch query, causing N+1 database queries."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def list_entities\(self\) -> List\[Dict\[str, Any\]\]:\n"
                r"        \"\"\"List all entities.\"\"\"\n"
                r"        # BUG: n_plus_one - loads each entity individually instead of batch\n"
                r"        all_entities = self\.repository\.find_all\(\)\n"
                r"        result = \[\]\n"
                r"        for entity in all_entities:\n"
                r"            fetched = self\.repository\.find_by_id\(entity\[""id""\]\)\n"
                r"            if fetched:\n"
                r"                result\.append\(fetched\)\n"
                r"        return result"
            ),
            "replace_with": (
                "    def list_entities(self) -> List[Dict[str, Any]]:\n"
                '        """List all entities."""\n'
                "        # BUG: N+1 query - loads each entity individually\n"
                "        all_entities = self.repository.find_all()\n"
                "        result = []\n"
                "        for entity in all_entities:\n"
                '            fetched = self.repository.find_by_id(entity["id"])\n'
                "            if fetched:\n"
                "                result.append(fetched)\n"
                "        return result"
            ),
            "reference_fix": (
                "    def list_entities(self) -> List[Dict[str, Any]]:\n"
                '        """List all entities."""\n'
                "        return self.repository.find_all()"
            ),
            "capabilities": ["debugging", "performance", "python_testing"],
            "difficulty": 3,
        }
    )

    # Mutation 22: Spring Service - Validation bypass
    register_mutation(
        {
            "id": "validation_bypass",
            "name": "Validation Bypass in Controller",
            "description": (
                "The Controller.handle_create method doesn't check validation errors "
                "before creating the entity, allowing invalid data to be saved."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def handle_create\(self, request: Dict\[str, Any\]\) -> Dict\[str, Any\]:\n"
                r"        \"\"\"Handle create request.\"\"\"\n"
                r"        data = request\.get\(\"body\", \{\}\)\n"
                r"        errors = self\.validator\.validate\(data\)\n"
                r"        if errors:\n"
                r'            return \{"status": 400, "errors": errors\}\n'
                r"        # BUG: validation_bypass - doesn't check validation errors before creating\n"
                r"        entity_id = self\.service\.create_entity\(data\)\n"
                r'        return \{"status": 201, "id": entity_id\}'
            ),
            "replace_with": (
                "    def handle_create(self, request: Dict[str, Any]) -> Dict[str, Any]:\n"
                '        """Handle create request."""\n'
                '        data = request.get("body", {})\n'
                "        errors = self.validator.validate(data)\n"
                "        # BUG: Validation errors are ignored, entity is created anyway\n"
                "        entity_id = self.service.create_entity(data)\n"
                '        return {"status": 201, "id": entity_id}'
            ),
            "reference_fix": (
                "    def handle_create(self, request: Dict[str, Any]) -> Dict[str, Any]:\n"
                '        """Handle create request."""\n'
                '        data = request.get("body", {})\n'
                "        errors = self.validator.validate(data)\n"
                "        if errors:\n"
                '            return {"status": 400, "errors": errors}\n'
                "        entity_id = self.service.create_entity(data)\n"
                '        return {"status": 201, "id": entity_id}'
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation: env_override (config_manager)
    register_mutation(
        {
            "id": "env_override",
            "name": "Environment Variable Override Error",
            "description": (
                "The resolve method does not properly handle environment "
                "variables embedded in the middle of strings. Only exact "
                "matches of ${VAR} are resolved, missing inline references."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"        resolved = dict\(config\)\n"
                r"        for key, value in resolved\.items\(\):\n"
                r"            if isinstance\(value, str\) and value\.startswith\(\"\\\$\{\"\) "
                r"and value\.endswith\(\"\"\)\):\n"
                r"                var_name = value\[2:-1\]\n"
                r"                resolved\[key\] = os\.environ\.get\(var_name, value\)"
            ),
            "replace_with": (
                "        resolved = dict(config)\n"
                "        for key, value in resolved.items():\n"
                '            if isinstance(value, str) and value == "${" + value[2:-1] + "}":\n'
                "                var_name = value[2:-1]\n"
                "                resolved[key] = os.environ.get(var_name, value)"
            ),
            "reference_fix": (
                "        resolved = dict(config)\n"
                "        for key, value in resolved.items():\n"
                '            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):\n'
                "                var_name = value[2:-1]\n"
                "                resolved[key] = os.environ.get(var_name, value)"
            ),
            "capabilities": ["debugging", "configuration", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation: secret_exposure (config_manager)
    register_mutation(
        {
            "id": "secret_exposure",
            "name": "Secret Exposure in Logs",
            "description": (
                "The get_secret method logs the actual secret value instead "
                "of just the key, exposing secrets in access logs."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"        \"\"\"Retrieve a secret value\.\n"
                r"\n"
                r"        Logs access for audit purposes\.\n"
                r"        \"\"\"\n"
                r"        self\._access_log\.append\(key\)\n"
                r"        return self\._secrets\.get\(key\)"
            ),
            "replace_with": (
                '        """Retrieve a secret value.\n'
                "\n"
                "        Logs access for audit purposes.\n"
                '        """\n'
                "        self._access_log.append(f\"Accessed: {key}={self._secrets.get(key, '')}\")\n"
                "        return self._secrets.get(key)"
            ),
            "reference_fix": (
                '        """Retrieve a secret value.\n'
                "\n"
                "        Logs access for audit purposes.\n"
                '        """\n'
                "        self._access_log.append(key)\n"
                "        return self._secrets.get(key)"
            ),
            "capabilities": ["debugging", "security", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation: merge_conflict (config_manager)
    register_mutation(
        {
            "id": "merge_conflict",
            "name": "Merge Order Conflict",
            "description": (
                "The merge method does not properly handle nested dictionaries. "
                "When both base and override contain nested dicts, the override "
                "completely replaces the base instead of merging recursively."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"        result = dict\(base\)\n"
                r"        for key, value in override\.items\(\):\n"
                r"            if \(\n"
                r"                key in result\n"
                r"                and isinstance\(result\[key\], dict\)\n"
                r"                and isinstance\(value, dict\)\n"
                r"            \):\n"
                r"                result\[key\] = Merger\.merge\(result\[key\], value\)\n"
                r"            else:\n"
                r"                result\[key\] = value\n"
                r"        return result"
            ),
            "replace_with": (
                "        result = dict(base)\n"
                "        for key, value in override.items():\n"
                "            result[key] = value\n"
                "        return result"
            ),
            "reference_fix": (
                "        result = dict(base)\n"
                "        for key, value in override.items():\n"
                "            if (\n"
                "                key in result\n"
                "                and isinstance(result[key], dict)\n"
                "                and isinstance(value, dict)\n"
                "            ):\n"
                "                result[key] = Merger.merge(result[key], value)\n"
                "            else:\n"
                "                result[key] = value\n"
                "        return result"
            ),
            "capabilities": ["debugging", "configuration", "python_testing"],
            "difficulty": 2,
        }
    )


    # Browser automation: XSS injection (no sanitization)
    register_mutation(
        {
            "id": "xss_reflected",
            "name": "Reflected XSS",
            "description": (
                "The sanitize_output method returns user input without "
                "escaping HTML entities, allowing reflected XSS attacks."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def sanitize_output\(self, user_input: str\) -> str:\n"
                r'        """Sanitize user input to prevent XSS."""\n'
                r"        # BUG: Does not properly escape HTML entities\n"
                r"        return user_input"
            ),
            "replace_with": (
                "    def sanitize_output(self, user_input: str) -> str:\n"
                '        """Sanitize user input to prevent XSS."""\n'
                "        # BUG: Does not properly escape HTML entities\n"
                "        return user_input"
            ),
            "reference_fix": (
                "    def sanitize_output(self, user_input: str) -> str:\n"
                '        """Sanitize user input to prevent XSS."""\n'
                "        import html\n"
                "        return html.escape(user_input, quote=True)"
            ),
            "capabilities": ["security", "web_security", "python_testing"],
            "difficulty": 2,
        }
    )

    # Browser automation: clickjacking (no frame protection)
    register_mutation(
        {
            "id": "clickjacking",
            "name": "Clickjacking Vulnerability",
            "description": (
                "The browser does not block frames from untrusted origins, "
                "allowing clickjacking attacks."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def is_frame_blocked\(self, frame_url: str\) -> bool:\n"
                r'        """Check if a frame URL is blocked for clickjacking protection."""\n'
                r"        return frame_url in self\._blocked_frames"
            ),
            "replace_with": (
                "    def is_frame_blocked(self, frame_url: str) -> bool:\n"
                '        """Check if a frame URL is blocked for clickjacking protection."""\n'
                "        # BUG: Always returns False, no frame protection\n"
                "        return False"
            ),
            "reference_fix": (
                "    def is_frame_blocked(self, frame_url: str) -> bool:\n"
                '        """Check if a frame URL is blocked for clickjacking protection."""\n'
                "        return frame_url in self._blocked_frames"
            ),
            "capabilities": ["security", "web_security", "python_testing"],
            "difficulty": 1,
        }
    )

    # Browser automation: auth bypass (missing auth check)
    register_mutation(
        {
            "id": "auth_bypass",
            "name": "Authentication Bypass",
            "description": (
                "The submit_form action does not check if the user is "
                "authenticated before allowing form submission."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    @staticmethod\n"
                r"    def submit_form\(page: Page, form_selector: Selector\) -> bool:\n"
                r'        """Submit a form."""\n'
                r"        elem = page\.find_element\(form_selector\)\n"
                r"        return elem is not None"
            ),
            "replace_with": (
                "    @staticmethod\n"
                "    def submit_form(page: Page, form_selector: Selector) -> bool:\n"
                '        """Submit a form."""\n'
                "        # BUG: No authentication check before submission\n"
                "        elem = page.find_element(form_selector)\n"
                "        if elem is None:\n"
                "            return False\n"
                "        # Missing: auth check should verify user is logged in\n"
                "        return True"
            ),
            "reference_fix": (
                "    @staticmethod\n"
                "    def submit_form(page: Page, form_selector: Selector) -> bool:\n"
                '        """Submit a form."""\n'
                "        elem = page.find_element(form_selector)\n"
                "        return elem is not None"
            ),
            "capabilities": ["security", "authentication", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 24: Database Query - SQL injection (string-format queries)
    register_mutation(
        {
            "id": "sql_injection",
            "name": "SQL Injection via String Formatting",
            "description": (
                "The QueryBuilder.build method uses string formatting to insert "
                "user input directly into SQL queries, allowing SQL injection attacks."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def build\(self\) -> str:\n"
                r'        cols = ", "\.join\(self\.columns\) if self\.columns else "\*"\n'
                r'        query = f"SELECT \{cols\} FROM \{self\.table\}"\n'
                r"        if self\.conditions:\n"
                r'            query += " WHERE " + " AND "\.join\(self\.conditions\)\n'
                r"        return query"
            ),
            "replace_with": (
                '    def build(self) -> str:\n'
                '        cols = ", ".join(self.columns) if self.columns else "*"\n'
                '        query = f"SELECT {cols} FROM {self.table}"\n'
                "        if self.conditions:\n"
                '            # BUG: Direct string concatenation allows SQL injection\n'
                '            query += " WHERE " + " AND ".join(self.conditions)\n'
                "        return query"
            ),
            "reference_fix": (
                '    def build(self) -> str:\n'
                '        cols = ", ".join(self.columns) if self.columns else "*"\n'
                '        query = f"SELECT {cols} FROM {self.table}"\n'
                "        if self.conditions:\n"
                '            query += " WHERE " + " AND ".join(self.conditions)\n'
                "        return query"
            ),
            "capabilities": ["security", "sql", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 25: Database Query - N+1 query (missing batch loading)
    register_mutation(
        {
            "id": "n_plus_one_query",
            "name": "N+1 Query Problem",
            "description": (
                "The QueryOptimizer does not batch related queries, causing "
                "N+1 query problems when fetching related data."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def optimize\(self, query: str\) -> str:\n"
                r"        if self\.cache\.get\(query\) is not None:\n"
                r'            return query  # Already cached\n'
                r"        return query"
            ),
            "replace_with": (
                "    def optimize(self, query: str) -> str:\n"
                "        if self.cache.get(query) is not None:\n"
                "            return query  # Already cached\n"
                "        # BUG: Does not batch related queries, causes N+1 problem\n"
                "        return query"
            ),
            "reference_fix": (
                "    def optimize(self, query: str) -> str:\n"
                "        if self.cache.get(query) is not None:\n"
                "            return query  # Already cached\n"
                "        return query"
            ),
            "capabilities": ["performance", "sql", "python_testing"],
            "difficulty": 3,
        }
    )

    # Mutation 26: Database Query - Missing index
    register_mutation(
        {
            "id": "missing_index",
            "name": "Missing Database Index",
            "description": (
                "The IndexManager.has_index method always returns False, "
                "causing the optimizer to never use indexes for query planning."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def has_index\(self, table: str, column: str\) -> bool:\n"
                r"        return table in self\.indexes and column in self\.indexes\[table\]"
            ),
            "replace_with": (
                "    def has_index(self, table: str, column: str) -> bool:\n"
                "        # BUG: Always returns False, indexes are never used\n"
                "        return False"
            ),
            "reference_fix": (
                "    def has_index(self, table: str, column: str) -> bool:\n"
                "        return table in self.indexes and column in self.indexes[table]"
            ),
            "capabilities": ["performance", "sql", "python_testing"],
            "difficulty": 1,
        }
    )

    # Mutation 27: API Integration - Rate limit bypass
    register_mutation(
        {
            "id": "rate_limit_bypass",
            "name": "Rate Limit Bypass",
            "description": (
                "The RateLimiter.can_request method always returns True, "
                "allowing unlimited API requests without rate limiting."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def can_request\(self\) -> bool:\n"
                r"        now = time\.time\(\)\n"
                r"        self\.requests = \[t for t in self\.requests if now - t < self\.window_seconds\]\n"
                r"        return len\(self\.requests\) < self\.max_requests"
            ),
            "replace_with": (
                "    def can_request(self) -> bool:\n"
                "        # BUG: Always returns True, no rate limiting\n"
                "        return True"
            ),
            "reference_fix": (
                "    def can_request(self) -> bool:\n"
                "        now = time.time()\n"
                "        self.requests = [t for t in self.requests if now - t < self.window_seconds]\n"
                "        return len(self.requests) < self.max_requests"
            ),
            "capabilities": ["security", "api", "python_testing"],
            "difficulty": 1,
        }
    )

    # Mutation 28: API Integration - Auth token leak in logs
    register_mutation(
        {
            "id": "auth_token_leak",
            "name": "Auth Token Leak in Logs",
            "description": (
                "The APIClient logs the full request including headers, "
                "exposing authentication tokens in logs."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    def get\(self, path: str\) -> Dict\[str, Any\]:\n"
                r'        url = f"\{self\.base_url\}\{path\}"\n'
                r'        return \{"url": url, "method": "GET", "headers": dict\(self\.headers\)\}'
            ),
            "replace_with": (
                "    def get(self, path: str) -> Dict[str, Any]:\n"
                '        url = f"{self.base_url}{path}"\n'
                '        # BUG: Headers including auth tokens are exposed in response\n'
                '        return {"url": url, "method": "GET", "headers": dict(self.headers)}'
            ),
            "reference_fix": (
                "    def get(self, path: str) -> Dict[str, Any]:\n"
                '        url = f"{self.base_url}{path}"\n'
                '        return {"url": url, "method": "GET", "headers": dict(self.headers)}'
            ),
            "capabilities": ["security", "api", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 29: API Integration - Schema mismatch
    register_mutation(
        {
            "id": "schema_mismatch",
            "name": "Response Schema Mismatch",
            "description": (
                "The ResponseParser.parse_list method does not handle nested "
                "data structures correctly, returning empty list for valid data."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"    @staticmethod\n"
                r"    def parse_list\(response: Dict\[str, Any\]\) -> list:\n"
                r"        data = ResponseParser\.parse_json\(response\)\n"
                r"        if isinstance\(data, list\):\n"
                r"            return data\n"
                r"        return \[\]"
            ),
            "replace_with": (
                "    @staticmethod\n"
                "    def parse_list(response: Dict[str, Any]) -> list:\n"
                "        data = ResponseParser.parse_json(response)\n"
                "        # BUG: Does not handle nested data structures\n"
                "        if isinstance(data, list):\n"
                "            return data\n"
                "        return []"
            ),
            "reference_fix": (
                "    @staticmethod\n"
                "    def parse_list(response: Dict[str, Any]) -> list:\n"
                "        data = ResponseParser.parse_json(response)\n"
                "        if isinstance(data, list):\n"
                "            return data\n"
                "        return []"
            ),
            "capabilities": ["debugging", "api", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 30: DSL - Syntax error (incorrect tokenization)
    register_mutation(
        {
            "id": "syntax_error",
            "name": "Incorrect Tokenization",
            "description": (
                "The Lexer.tokenize method skips operators, causing syntax errors "
                "when parsing expressions with multiple operators."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"        elif source\[i\] in \"\+\-\*\/=\(\)\{\}\;,\":\n"
                r'            self\.tokens\.append\(\("OP", source\[i\]\)\)'
            ),
            "replace_with": (
                '        elif source[i] in "+-*/=(){};,":\n'
                "            # BUG: Skips operators instead of tokenizing them\n"
                "            i += 1"
            ),
            "reference_fix": (
                '        elif source[i] in "+-*/=(){};,":\n'
                '            self.tokens.append(("OP", source[i]))'
            ),
            "capabilities": ["debugging", "parsing", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 31: DSL - Type coercion (wrong type handling)
    register_mutation(
        {
            "id": "type_coercion",
            "name": "Wrong Type Coercion",
            "description": (
                "The Interpreter.evaluate method does not handle type coercion "
                "for division, returning integer division instead of float."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r"            elif op == \"/\":\n"
                r"                if right == 0:\n"
                r'                    raise ZeroDivisionError\("Division by zero"\)\n'
                r"                return left / right"
            ),
            "replace_with": (
                '            elif op == "/":\n'
                "                if right == 0:\n"
                '                    raise ZeroDivisionError("Division by zero")\n'
                "                # BUG: Integer division instead of float division\n"
                "                return int(left // right)"
            ),
            "reference_fix": (
                '            elif op == "/":\n'
                "                if right == 0:\n"
                '                    raise ZeroDivisionError("Division by zero")\n'
                "                return left / right"
            ),
            "capabilities": ["debugging", "parsing", "python_testing"],
            "difficulty": 2,
        }
    )

    # Mutation 32: DSL - Undefined reference (unresolved symbols)
    register_mutation(
        {
            "id": "undefined_reference",
            "name": "Undefined Variable Reference",
            "description": (
                "The Interpreter.evaluate method returns 0 for undefined variables "
                "instead of raising an error, masking bugs in the source code."
            ),
            "target_file": "app.py",
            "search_pattern": (
                r'        elif node\["type"\] == "variable":\n'
                r'            return self\.env\.get\(node\["name"\], 0\)'
            ),
            "replace_with": (
                '        elif node["type"] == "variable":\n'
                '            # BUG: Returns 0 for undefined variables instead of raising error\n'
                '            if node["name"] not in self.env:\n'
                '                return 0\n'
                '            return self.env[node["name"]]'
            ),
            "reference_fix": (
                '        elif node["type"] == "variable":\n'
                '            return self.env.get(node["name"], 0)'
            ),
            "capabilities": ["debugging", "parsing", "python_testing"],
            "difficulty": 2,
        }
    )


# Register all mutations on module load
_register_mutations()


# ---------------------------------------------------------------------------
# Mutation Application
# ---------------------------------------------------------------------------


def apply_mutation(world_dir: Path, mutation_id: str) -> list[str]:
    """Apply a mutation to a world directory.

    Reads the target file, performs the text replacement defined by the
    mutation, and writes the modified file back.

    Args:
        world_dir: Path to the generated world directory.
        mutation_id: ID of the mutation to apply.

    Returns:
        List of file paths that were modified.

    Raises:
        FileNotFoundError: If the mutation is not found.
        ValueError: If the search pattern is not found in the target file.
    """
    mutation = get_mutation(mutation_id)
    if mutation is None:
        raise FileNotFoundError(f"Mutation '{mutation_id}' not found")

    target_path = world_dir / mutation["target_file"]
    if not target_path.exists():
        raise ValueError(f"Target file '{mutation['target_file']}' not found in {world_dir}")

    content = target_path.read_text()

    # Apply the mutation using regex replacement
    search_pattern = mutation["search_pattern"]
    replace_with = mutation["replace_with"]

    new_content = re.sub(search_pattern, replace_with, content, count=1, flags=re.MULTILINE)

    if new_content == content:
        raise ValueError(f"Mutation '{mutation_id}' search pattern not found in {mutation['target_file']}")

    target_path.write_text(new_content)

    return [mutation["target_file"]]


def revert_mutation(world_dir: Path, mutation_id: str) -> list[str]:
    """Revert a mutation by applying the reference fix.

    Args:
        world_dir: Path to the generated world directory.
        mutation_id: ID of the mutation to revert.

    Returns:
        List of file paths that were modified.
    """
    mutation = get_mutation(mutation_id)
    if mutation is None:
        raise FileNotFoundError(f"Mutation '{mutation_id}' not found")

    target_path = world_dir / mutation["target_file"]
    if not target_path.exists():
        raise ValueError(f"Target file '{mutation['target_file']}' not found in {world_dir}")

    content = target_path.read_text()

    # The mutation's replace_with is what's currently in the file
    # The reference_fix is what we want to restore
    mutated_text = mutation["replace_with"]
    reference_fix = mutation.get("reference_fix", mutation["search_pattern"])

    # Simple string replacement to revert
    new_content = content.replace(mutated_text, reference_fix)

    if new_content == content:
        # Try regex-based revert
        new_content = re.sub(
            re.escape(mutated_text),
            reference_fix,
            content,
            count=1,
            flags=re.MULTILINE,
        )

    target_path.write_text(new_content)

    return [mutation["target_file"]]


def get_reference_fix(mutation_id: str) -> str | None:
    """Get the reference fix code for a mutation.

    Args:
        mutation_id: ID of the mutation.

    Returns:
        The reference fix code string, or None.
    """
    mutation = get_mutation(mutation_id)
    if mutation is None:
        return None
    return mutation.get("reference_fix")
