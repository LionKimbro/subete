"""Access to the authoritative published database generation."""

from .fsio import read_json_file
from .validation import validate_generation


def read_generation(paths, database_id):
    """Read and validate the authoritative current generation record."""
    data = read_json_file(paths["generation"])
    validate_generation(data, database_id)
    return data["generation"]
