"""Live facts about the current Subete database process."""

from .fsio import read_json
from .paths import path


g = {
    "database-id": None,
}


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

