"""Bug mutation definitions for task generation.

Defines controlled bug mutations that can be injected into
repository templates to create training tasks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BugMutation:
    """Definition of a controlled bug mutation.

    A mutation specifies how to break working code and how to fix it.

    Attributes:
        mutation_id: Unique identifier for this mutation.
        name: Human-readable name.
        description: Description of the bug.
        capabilities: List of capabilities this mutation exercises.
        difficulty: Difficulty level (1-5).
        target_file: File to modify (relative path).
        search_pattern: Text to search for in the target file.
        buggy_replacement: Replacement text that introduces the bug.
        reference_fix: Replacement text that fixes the bug.
    """

    mutation_id: str
    name: str
    description: str
    capabilities: list[str]
    difficulty: int
    target_file: str
    search_pattern: str
    buggy_replacement: str
    reference_fix: str
    metadata: dict[str, Any] = field(default_factory=dict)


def get_all_mutations() -> list[BugMutation]:
    """Return all defined bug mutations.

    Returns:
        List of BugMutation instances.
    """
    return [
        BugMutation(
            mutation_id="pagination_boundary",
            name="Pagination Boundary Error",
            description=(
                "The pagination function returns incorrect results when the "
                "requested page exceeds the available number of records."
            ),
            capabilities=["debugging", "edge_case_reasoning"],
            difficulty=2,
            target_file="app.py",
            search_pattern=(
                "    total_pages = total // page_size\n"
                "    items = all_items[(page - 1) * page_size : page * page_size]"
            ),
            buggy_replacement=(
                "    total_pages = total // page_size\n"
                "    items = all_items[page * page_size : (page + 1) * page_size]"
            ),
            reference_fix=(
                "    total_pages = (total + page_size - 1) // page_size\n"
                "    items = all_items[(page - 1) * page_size : page * page_size]"
            ),
        ),
        BugMutation(
            mutation_id="empty_search",
            name="Empty Search Query Handling",
            description=(
                "The search function returns an error when given an empty "
                "search query instead of returning all records."
            ),
            capabilities=["debugging", "edge_case_reasoning"],
            difficulty=2,
            target_file="app.py",
            search_pattern=(
                "    if query:\n"
                "        results = [r for r in records if query.lower() in r.get('name', '').lower()]\n"
                "    else:\n"
                "        results = records"
            ),
            buggy_replacement=(
                "    if query:\n"
                "        results = [r for r in records if query.lower() in r.get('name', '').lower()]\n"
                "    else:\n"
                "        raise ValueError('Search query cannot be empty')"
            ),
            reference_fix=(
                "    if query:\n"
                "        results = [r for r in records if query.lower() in r.get('name', '').lower()]\n"
                "    else:\n"
                "        results = records"
            ),
        ),
        BugMutation(
            mutation_id="duplicate_records",
            name="Duplicate Record Handling",
            description=(
                "The record creation function does not check for duplicates, "
                "allowing duplicate records to be created."
            ),
            capabilities=["debugging", "edge_case_reasoning", "testing"],
            difficulty=3,
            target_file="app.py",
            search_pattern=("def create_record(records, record):\n" "    records.append(record)\n" "    return record"),
            buggy_replacement=(
                "def create_record(records, record):\n"
                "    # Duplicate check removed\n"
                "    records.append(record)\n"
                "    return record"
            ),
            reference_fix=(
                "def create_record(records, record):\n"
                "    for existing in records:\n"
                "        if existing.get('id') == record.get('id'):\n"
                "            raise ValueError('Duplicate record ID')\n"
                "    records.append(record)\n"
                "    return record"
            ),
        ),
    ]


def get_mutation(mutation_id: str) -> BugMutation | None:
    """Get a mutation by ID.

    Args:
        mutation_id: Mutation identifier.

    Returns:
        BugMutation or None if not found.
    """
    for mutation in get_all_mutations():
        if mutation.mutation_id == mutation_id:
            return mutation
    return None


def get_mutations_by_capability(capability: str) -> list[BugMutation]:
    """Get mutations that exercise a specific capability.

    Args:
        capability: Capability name.

    Returns:
        List of matching mutations.
    """
    return [m for m in get_all_mutations() if capability in m.capabilities]


def get_mutations_by_difficulty(
    min_difficulty: int = 1,
    max_difficulty: int = 5,
) -> list[BugMutation]:
    """Get mutations within a difficulty range.

    Args:
        min_difficulty: Minimum difficulty.
        max_difficulty: Maximum difficulty.

    Returns:
        List of matching mutations.
    """
    return [m for m in get_all_mutations() if min_difficulty <= m.difficulty <= max_difficulty]
