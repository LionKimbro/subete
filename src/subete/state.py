"""Live facts about the current Subete database process."""

import time

from . import fsio
from .paths import path
from .validation import validate_database_configuration


g = {
    "database-id": None,
    "now": None,
}

configuration = {}


def load_existing_database_id():
    """Load the current database ID when an identity record is present."""
    g["database-id"] = None

    if not path("identity").is_file():
        return

    fsio.read_json("identity", ["required"])
    identity = fsio.read["data"]
    g["database-id"] = identity["database-id"]


def load_database_id_right_after_creation():
    """Load the database ID from the identity record just written by setup."""
    fsio.read_json("identity", ["required"])
    g["database-id"] = fsio.read["data"]["database-id"]


def update_now():
    """Record the current wall-clock time for this process pass."""
    g["now"] = time.time()


def load_configuration():
    """Load the complete durable configuration for an existing database."""
    configuration.clear()

    if not g["database-id"]:
        return

    validate_database_configuration()
    fsio.read_json("configuration", ["required"])
    configuration.update(fsio.read["data"])
