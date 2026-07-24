"""Creation and validation of a generation-zero Subete database."""

from datetime import UTC, datetime
from uuid import uuid4

from .constants import GENERATION_FORMAT_VERSION, INITIAL_CONFIGURATION
from .fsio import read_json_file, write_json_replace
from .paths import build_paths, required_directories
from .validation import validate_configuration, validate_generation, validate_identity


def setup_database(dbroot):
    """Create a new database or validate the existing generation-zero foundation."""
    paths = build_paths(dbroot)
    for directory in required_directories(paths):
        directory.mkdir(parents=True, exist_ok=True)
    if paths["identity"].exists():
        validate_existing_database(paths)
        return {"status": "existing", "database-id": read_json_file(paths["identity"])["database-id"]}
    if paths["configuration"].exists() or paths["generation"].exists():
        raise ValueError("database root has metadata but no identity.json; refusing to initialize")
    identity = {"database-id": str(uuid4()), "created": utc_now()}
    generation = {
        "generation-format-version": GENERATION_FORMAT_VERSION, "database-id": identity["database-id"],
        "generation": 0, "journal-sequence": 0, "updated": utc_now(),
    }
    write_json_replace(paths["identity"], identity)
    write_json_replace(paths["configuration"], INITIAL_CONFIGURATION)
    write_json_replace(paths["generation"], generation)
    return {"status": "created", "database-id": identity["database-id"]}


def validate_existing_database(paths):
    """Validate the core records required before a service can use *paths*."""
    for key in ("identity", "configuration", "generation"):
        if not paths[key].is_file():
            raise ValueError(f"existing database is missing {paths[key].name}")
    identity = read_json_file(paths["identity"])
    configuration = read_json_file(paths["configuration"])
    generation = read_json_file(paths["generation"])
    validate_identity(identity)
    validate_configuration(configuration)
    validate_generation(generation, identity["database-id"])


def utc_now():
    """Return an ISO 8601 UTC timestamp suitable for stored records."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
