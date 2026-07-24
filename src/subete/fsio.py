"""Small durable filesystem and JSON operations."""

import json
import os
import tempfile
from pathlib import Path


def read_json_file(path):
    """Read one UTF-8 JSON value from *path*."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle, parse_constant=_reject_non_json_constant)


def write_json_replace(path, data):
    """Durably replace *path* with one complete UTF-8 JSON value."""
    destination = Path(path)
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
