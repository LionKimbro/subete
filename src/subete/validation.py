"""Validation for root metadata formats used by the foundation."""

from uuid import UUID

from .constants import CONFIGURATION_VERSION, GENERATION_FORMAT_VERSION


def validate_identity(data):
    _require_object(data, "identity.json")
    _require_uuid(data, "database-id")
    if not isinstance(data.get("created"), str):
        raise ValueError("identity.json created must be a timestamp string")


def validate_configuration(data):
    _require_object(data, "configuration.json")
    _require_exact_int(data, "configuration-version", CONFIGURATION_VERSION)


def validate_generation(data, database_id):
    _require_object(data, "generation.json")
    _require_exact_int(data, "generation-format-version", GENERATION_FORMAT_VERSION)
    _require_uuid(data, "database-id")
    if data["database-id"] != database_id:
        raise ValueError("generation.json database-id does not match identity.json")
    generation = data.get("generation")
    sequence = data.get("journal-sequence")
    if not _is_nonnegative_int(generation):
        raise ValueError("generation.json generation must be a non-negative integer")
    if sequence != generation:
        raise ValueError("generation.json journal-sequence must equal generation in Version 1")
    if not isinstance(data.get("updated"), str):
        raise ValueError("generation.json updated must be a timestamp string")


def _require_object(data, filename):
    if not isinstance(data, dict):
        raise ValueError(f"{filename} must contain one JSON object")


def _require_exact_int(data, key, value):
    if data.get(key) != value:
        raise ValueError(f"{key} must equal {value}")


def _require_uuid(data, key):
    value = data.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a UUID string")
    try:
        UUID(value)
    except ValueError as error:
        raise ValueError(f"{key} must be a UUID string") from error


def _is_nonnegative_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0
