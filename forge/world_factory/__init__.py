"""World factory module — generates executable software environments.

Provides:
- WorldGenerator for creating reproducible Python repositories
- Templates for environment generation (task_manager_api, data_pipeline)
- Seeder for deterministic bug injection
- Manifest generation and tracking
"""

__version__ = "0.1.0"

from forge.world_factory.generator import WorldGenerator
from forge.world_factory.manifest import has_manifest, read_manifest, write_manifest
from forge.world_factory.seeder import (
    apply_mutation,
    get_mutation,
    get_reference_fix,
    list_mutations,
    register_mutation,
    revert_mutation,
)
from forge.world_factory.templates import get_template, list_templates, register_template

__all__ = [
    "WorldGenerator",
    "get_template",
    "list_templates",
    "register_template",
    "get_mutation",
    "list_mutations",
    "apply_mutation",
    "revert_mutation",
    "get_reference_fix",
    "register_mutation",
    "read_manifest",
    "write_manifest",
    "has_manifest",
]
