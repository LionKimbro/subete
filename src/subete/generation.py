"""Access to the authoritative published database generation."""

from . import fsio
from .validation import validate_database_generation


def read_generation():
    """Read and validate the authoritative current generation record."""
    validate_database_generation()
    fsio.read_file("generation", ["required", "json"])
    return fsio.read["value"]["generation"]
