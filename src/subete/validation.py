"""Validation for root metadata formats used by the foundation."""

from uuid import UUID
from pathlib import Path

from .constants import CONFIGURATION_VERSION, GENERATION_FORMAT_VERSION
from .fsio import read_json


def validate_database_identity():
    """Validate the fixed identity record of the current database."""
    data = read_json("identity", ["verify-file"])
    _require_object(data, "identity.json")
    _require_uuid(data, "database-id")
    if not isinstance(data.get("created"), str):
        raise ValueError("identity.json created must be a timestamp string")


def validate_database_configuration():
    """Validate the fixed configuration record of the current database."""
    data = read_json("configuration", ["verify-file"])
    _require_object(data, "configuration.json")
    _require_exact_keys(
        data,
        {"configuration-version", "polling", "filetalk"},
        "configuration.json",
    )
    _require_exact_int(data, "configuration-version", CONFIGURATION_VERSION)
    _validate_polling_configuration(data["polling"])
    _validate_filetalk_configuration(data["filetalk"])


def validate_database_generation():
    """Validate the fixed generation record of the current database."""
    identity = read_json("identity", ["verify-file"])
    data = read_json("generation", ["verify-file"])
    _require_object(data, "generation.json")
    _require_exact_int(data, "generation-format-version", GENERATION_FORMAT_VERSION)
    _require_uuid(data, "database-id")
    if data["database-id"] != identity["database-id"]:
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


def _require_exact_keys(data, keys, name):
    if set(data) != keys:
        raise ValueError(f"{name} has missing or unknown fields")


def _validate_polling_configuration(data):
    _require_object(data, "configuration polling")
    _require_exact_keys(
        data,
        {
            "inbox-interval-seconds",
            "incomplete-file-quiet-seconds",
            "stale-inbox-file-action",
        },
        "configuration polling",
    )

    if not _is_number(data["inbox-interval-seconds"]) or data["inbox-interval-seconds"] <= 0:
        raise ValueError("configuration inbox-interval-seconds must be positive")
    if not _is_number(data["incomplete-file-quiet-seconds"]) or data["incomplete-file-quiet-seconds"] < 0:
        raise ValueError("configuration incomplete-file-quiet-seconds must be non-negative")
    if data["stale-inbox-file-action"] not in {"retain-and-report", "quarantine", "delete"}:
        raise ValueError("configuration stale-inbox-file-action is invalid")


def _validate_filetalk_configuration(data):
    _require_object(data, "configuration filetalk")
    _require_exact_keys(data, {"allowed-reply-paths"}, "configuration filetalk")
    paths = data["allowed-reply-paths"]
    if not isinstance(paths, list):
        raise ValueError("configuration allowed-reply-paths must be an array")
    if not all(isinstance(item, str) and Path(item).is_absolute() for item in paths):
        raise ValueError("configuration allowed-reply-paths must contain absolute paths")


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


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)
