"""Small durable filesystem and JSON operations."""

import json
import os
import tempfile
from pathlib import Path

from .paths import path


read = {
    "status": None,
    "source": None,
    "stat": None,
    "raw": None,
    "value": None,
    "error": None,
}


def read_file(source, flags=None):
    """Read a file into the current read register and return its status."""
    if flags is None:
        flags = []

    read.update(
        {
            "status": None,
            "source": source,
            "stat": None,
            "raw": None,
            "value": None,
            "error": None,
        }
    )

    if isinstance(source, str):
        source = path(source)
        read["source"] = source

    if not isinstance(source, Path):
        read["status"] = "invalid"
        read["error"] = "invalid-source"
        raise TypeError("read_file source must be a territory name or Path")

    try:
        if "stat" in flags:
            facts = source.stat()
            read["stat"] = {"size": facts.st_size, "mtime": facts.st_mtime_ns}

        read["raw"] = source.read_bytes()

        if "json" in flags:
            read["value"] = json.loads(
                read["raw"].decode("utf-8"),
                parse_constant=_reject_non_json_constant,
            )
    except FileNotFoundError:
        read["status"] = "missing"
        read["error"] = "missing"
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        read["status"] = "invalid"
        read["error"] = "invalid-json"
    except OSError:
        read["status"] = "unreadable"
        read["error"] = "unreadable"
    else:
        read["status"] = "complete"

    if "required" in flags and read["status"] != "complete":
        raise ValueError(f"required file read failed: {read['status']}: {source.resolve()}")

    return read["status"]


def write_json(destination, data):
    """Write JSON without leaving temporary files in external directories."""
    if isinstance(destination, str):
        destination = path(destination)

    if not isinstance(destination, Path):
        raise TypeError("write_json destination must be a territory name or Path")

    destination.parent.mkdir(parents=True, exist_ok=True)

    if _is_within_database_root(destination):
        _replace_database_json(destination, data)
    else:
        _write_external_json(destination, data)


def _replace_database_json(destination, data):
    """Atomically replace one JSON file in the database territory."""
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            _write_json(handle, data)
        os.replace(temporary, destination)
        _fsync_directory(destination.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_external_json(destination, data):
    """Write directly to an external JSON destination that Subete does not own."""
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        _write_json(handle, data)


def _write_json(handle, data):
    """Write and flush one complete UTF-8 JSON document to an open file."""
    json.dump(data, handle, indent=2, ensure_ascii=False, allow_nan=False)
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())


def _is_within_database_root(destination):
    """Return whether the resolved destination remains in this database root."""
    try:
        destination.resolve().relative_to(path("root").resolve())
    except (OSError, ValueError):
        return False
    return True


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
