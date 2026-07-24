"""Creation and validation of a generation-zero Subete database."""

from datetime import UTC, datetime
from uuid import uuid4

from .constants import GENERATION_FORMAT_VERSION, INITIAL_CONFIGURATION
from .fsio import read_json_file, write_json_replace
from .paths import g, required_directories
from .validation import validate_configuration, validate_generation, validate_identity


def setup_database():
    """Create a new database or validate the existing generation-zero foundation."""
    create_required_directories()

    if g["identity"].exists():
        validate_existing_database()
        return existing_database_result()

    reject_partial_metadata()

    identity = create_identity()
    write_initial_configuration()
    write_generation_zero(identity)

    return {
        "status": "created",
        "database-id": identity["database-id"],
    }


def create_required_directories():
    """Create the complete directory layout for the current database."""
    for directory in required_directories():
        directory.mkdir(parents=True, exist_ok=True)


def reject_partial_metadata():
    """Reject a root whose metadata cannot describe a valid database."""
    if g["configuration"].exists() or g["generation"].exists():
        raise ValueError("database root has metadata but no identity.json; refusing to initialize")


def create_identity():
    """Write and return the identity record for a new database."""
    identity = {
        "database-id": str(uuid4()),
        "created": utc_now(),
    }
    write_json_replace(g["identity"], identity)
    return identity


def write_initial_configuration():
    """Write the fixed generation-zero configuration record."""
    write_json_replace(g["configuration"], INITIAL_CONFIGURATION)


def write_generation_zero(identity):
    """Write the first generation record for a new database."""
    generation = {
        "generation-format-version": GENERATION_FORMAT_VERSION,
        "database-id": identity["database-id"],
        "generation": 0,
        "journal-sequence": 0,
        "updated": utc_now(),
    }
    write_json_replace(g["generation"], generation)


def existing_database_result():
    """Return setup's result for the validated existing database."""
    identity = read_json_file(g["identity"])
    return {
        "status": "existing",
        "database-id": identity["database-id"],
    }


def validate_existing_database():
    """Validate the core records required before this process can use the database."""
    for key in ("identity", "configuration", "generation"):
        if not g[key].is_file():
            raise ValueError(f"existing database is missing {g[key].name}")

    identity = read_json_file(g["identity"])
    configuration = read_json_file(g["configuration"])
    generation = read_json_file(g["generation"])

    validate_identity(identity)
    validate_configuration(configuration)
    validate_generation(generation, identity["database-id"])


def utc_now():
    """Return an ISO 8601 UTC timestamp suitable for stored records."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
