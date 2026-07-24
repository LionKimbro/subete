"""Access to the authoritative published database generation."""

from .fsio import read_json
from .validation import validate_database_generation


def read_generation():
    """Read and validate the authoritative current generation record."""
    validate_database_generation()
    return read_json("generation")["generation"]
