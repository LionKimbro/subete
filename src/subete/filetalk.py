"""FileTalk intake, claims, replies, and terminal request records."""

import shutil
from pathlib import Path

from . import fsio, state
from .fsio import write_json
from .paths import path


observations = {}


def reset_filetalk_observations():
    """Clear incomplete-file observations for a fresh service run."""
    observations.clear()


def discover_messages():
    """Return stable complete JSON-object inbox files in filename order."""
    messages = []

    for message_file in sorted(path("inbox").iterdir(), key=lambda item: item.name):
        if not message_file.is_file():
            continue

        outcome = _read_message_file(message_file)

        if outcome["state"] == "complete-object":
            observations.pop(message_file, None)
            messages.append({"path": message_file, "message": outcome["value"]})
        else:
            _record_unreadable_message(message_file)

    return messages


def list_stale_unreadable_messages():
    """Return unreadable messages unchanged for the configured quiet period."""
    quiet_seconds = state.configuration["polling"]["incomplete-file-quiet-seconds"]

    return [
        message_file
        for message_file, facts in observations.items()
        if message_file.exists() and state.g["now"] - facts["last-change"] >= quiet_seconds
    ]


def claim_inbox_message(source):
    """Move one complete inbox message to claimed storage without overwriting."""
    destination = path("claimed") / source.name

    if destination.exists():
        if source.exists() and source.read_bytes() == destination.read_bytes():
            source.unlink()
            return destination

        raise ValueError("request claim collision")

    source.replace(destination)
    return destination


def deliver_reply(reply, response):
    """Write one response to the configured permitted reply destination."""
    destination = _validate_reply_destination(reply)
    write_json(destination, response)
    return destination


def archive_completed_request(claimed, record):
    """Place one successfully completed request under terminal storage."""
    return _archive_terminal_request(path("completed"), claimed, record)


def archive_failed_request(claimed, record):
    """Place one failed request under terminal storage."""
    return _archive_terminal_request(path("failed"), claimed, record)


def _read_message_file(message_file):
    """Classify a candidate without treating incomplete JSON as bad input."""
    fsio.read_json(message_file)

    if fsio.read["status"] != "complete":
        return {"state": "unreadable"}

    value = fsio.read["data"]

    if not isinstance(value, dict):
        return {"state": "complete-non-object", "value": value}

    return {"state": "complete-object", "value": value}


def _record_unreadable_message(message_file):
    """Record one unreadable message's changing filesystem facts."""
    stat = message_file.stat()
    current = {
        "size": stat.st_size,
        "mtime": stat.st_mtime_ns,
        "first-seen": state.g["now"],
        "last-change": state.g["now"],
    }
    prior = observations.get(message_file)

    if prior is not None:
        current["first-seen"] = prior["first-seen"]

        if prior["size"] == current["size"] and prior["mtime"] == current["mtime"]:
            current["last-change"] = prior["last-change"]

    observations[message_file] = current


def _validate_reply_destination(reply):
    """Return a permitted absolute response path or reject it."""
    if not isinstance(reply, dict) or set(reply) != {"type", "path"} or reply["type"] != "file":
        raise ValueError("invalid-reply-destination")

    raw_path = reply["path"]

    if not isinstance(raw_path, str):
        raise ValueError("invalid-reply-destination")

    destination = Path(raw_path)

    if not destination.is_absolute():
        raise ValueError("invalid-reply-destination")

    parent = destination.parent.resolve()
    database_root = path("root").resolve()

    if _is_beneath(parent, database_root):
        raise ValueError("invalid-reply-destination")

    for allowed_path in state.configuration["filetalk"]["allowed-reply-paths"]:
        if _is_beneath(parent, Path(allowed_path).resolve()):
            return parent / destination.name

    raise ValueError("invalid-reply-destination")


def _archive_terminal_request(directory, claimed, record):
    """Preserve original request bytes alongside structured terminal data."""
    destination = directory / claimed.name

    if destination.exists():
        raise ValueError("terminal request collision")

    destination.mkdir()
    shutil.move(str(claimed), str(destination / "request.json"))
    write_json(destination / "record.json", record)

    return destination


def _is_beneath(candidate_path, root):
    """Return whether one resolved path is beneath or equal to another."""
    try:
        candidate_path.relative_to(root)
    except ValueError:
        return False

    return True
