"""Creation and validation of a generation-zero Subete database."""

from datetime import UTC, datetime
from uuid import uuid4

from .constants import GENERATION_FORMAT_VERSION, INITIAL_CONFIGURATION
from .fsio import write_json
from .paths import path, required_directories
from . import state
from .validation import (
    validate_database_configuration,
    validate_database_generation,
    validate_database_identity,
)


def setup_database():
    """Create a new database or validate the existing generation-zero foundation."""
    if state.g["database-id"]:
        validate_database()
        return "existing"

    _create_required_directories()
    _reject_incomplete_root_metadata()

    _create_identity_record()
    _write_initial_configuration_record()
    _write_generation_zero_record()

    return "created"


def _create_required_directories():
    """Create the complete directory layout for the current database."""
    for directory in required_directories():
        directory.mkdir(parents=True, exist_ok=True)


def _reject_incomplete_root_metadata():
    """Reject a root whose metadata cannot describe a valid database."""
    metadata_names = ("identity", "configuration", "generation")
    if any(path(name).exists() for name in metadata_names):
        raise ValueError("database root has metadata but no identity loaded; refusing to initialize")


def _create_identity_record():
    """Write the identity record for a new database."""
    identity = {
        "database-id": str(uuid4()),
        "created": utc_now(),
    }
    write_json("identity", identity)
    state.load_database_id_right_after_creation()


def _write_initial_configuration_record():
    """Write the fixed generation-zero configuration record."""
    write_json("configuration", INITIAL_CONFIGURATION)
    state.load_configuration()


def _write_generation_zero_record():
    """Write the first generation record for a new database."""
    generation = {
        "generation-format-version": GENERATION_FORMAT_VERSION,
        "database-id": state.g["database-id"],
        "generation": 0,
        "journal-sequence": 0,
        "updated": utc_now(),
    }
    write_json("generation", generation)


def validate_database():
    """Validate the core records required before this process can use the database."""
    validate_database_identity()
    validate_database_configuration()
    validate_database_generation()


def utc_now():
    """Return an ISO 8601 UTC timestamp suitable for stored records."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
