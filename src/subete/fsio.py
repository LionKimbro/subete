"""Small durable filesystem and JSON operations."""

import json
import os
import tempfile
from pathlib import Path

from .paths import path


def read_json(source, flags=None):
    """Read JSON from a named territory or an explicit Path object."""
    if flags is None:
        flags = []

    if isinstance(source, str):
        source = path(source)

    if not isinstance(source, Path):
        raise TypeError("read_json source must be a territory name or Path")

    if "verify-file" in flags and not source.is_file():
        raise ValueError(f"existing database is missing {source.name}")

    with source.open("r", encoding="utf-8") as handle:
        return json.load(handle, parse_constant=_reject_non_json_constant)


def write_json(destination, data):
    """Durably write JSON to a named territory or an explicit Path object."""
    if isinstance(destination, str):
        destination = path(destination)

    if not isinstance(destination, Path):
        raise TypeError("write_json destination must be a territory name or Path")

    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        _fsync_directory(destination.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def _fsync_directory(path):
    """Request directory metadata durability where the platform supports it."""
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _reject_non_json_constant(value):
    raise ValueError(f"invalid JSON numeric constant: {value}")
