"""Live facts about the current Subete database process."""

from .fsio import read_json
from .paths import path
from .validation import validate_database_configuration


g = {
    "database-id": None,
}

configuration = {}


def load_existing_database_id():
    """Load the current database ID when an identity record is present."""
    g["database-id"] = None

    if not path("identity").is_file():
        return

    identity = read_json("identity")
    g["database-id"] = identity["database-id"]


def load_database_id_right_after_creation():
    """Load the database ID from the identity record just written by setup."""
    g["database-id"] = read_json("identity")["database-id"]


def load_configuration():
    """Load the complete durable configuration for an existing database."""
    configuration.clear()

    if not g["database-id"]:
        return

    validate_database_configuration()
    configuration.update(read_json("configuration"))
