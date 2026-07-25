"""The sequential FileTalk request lifecycle."""

import shutil
from pathlib import Path

from . import fsio, state
from .fsio import write_json
from .paths import path


current = {
    "path": None,
    "message": None,
    "location": None,
}

observations = {}


def init_filetalk():
    """Resolve FileTalk's fixed directories for this process."""
    _clear_current_request()
    reset_filetalk_observations()


def discover_next_message():
    """Load the first stable complete inbox message into the current register."""
    _clear_current_request()

    for message_file in sorted(path("inbox").iterdir(), key=lambda item: item.name):
        if not message_file.is_file():
            continue

        fsio.read_json(message_file)

        status = fsio.read["status"]
        data = fsio.read["data"]

        if status == "complete" and isinstance(data, dict):
            current["path"] = message_file
            current["message"] = data
            current["location"] = "inbox"
            observations.pop(message_file, None)
            return True

        _record_unreadable_message(message_file)

    return False


def claim_message():
    """Move the current inbox message to claimed storage."""
    source = current["path"]
    destination = path("claimed") / source.name

    if destination.exists():
        if source.exists() and source.read_bytes() == destination.read_bytes():
            source.unlink()
        else:
            raise ValueError("request claim collision")
    else:
        source.replace(destination)

    current["path"] = destination
    current["location"] = "claimed"


def deliver_reply(response):
    """Write one response to the current message's permitted reply destination."""
    destination = _validate_reply_destination(current["message"]["reply"])
    write_json(destination, response)
    return destination


def complete_request(record):
    """Archive the current claimed request as completed."""
    _archive_current_request("completed", record)


def fail_request(record):
    """Archive the current claimed request as failed."""
    _archive_current_request("failed", record)


def list_stale_unreadable_messages():
    """Return unreadable messages unchanged for the configured quiet period."""
    quiet_seconds = state.configuration["polling"]["incomplete-file-quiet-seconds"]

    return [
        message_file
        for message_file, facts in observations.items()
        if message_file.exists() and state.g["now"] - facts["last-change"] >= quiet_seconds
    ]


def reset_filetalk_observations():
    """Clear incomplete-file observations for a fresh service run."""
    observations.clear()


def _record_unreadable_message(message_file):
    """Record one unreadable message's changing filesystem facts."""
    stat = message_file.stat()
    current_facts = {
        "size": stat.st_size,
        "mtime": stat.st_mtime_ns,
        "first-seen": state.g["now"],
        "last-change": state.g["now"],
    }
    prior_facts = observations.get(message_file)

    if prior_facts is not None:
        current_facts["first-seen"] = prior_facts["first-seen"]

        if (
            prior_facts["size"] == current_facts["size"]
            and prior_facts["mtime"] == current_facts["mtime"]
        ):
            current_facts["last-change"] = prior_facts["last-change"]

    observations[message_file] = current_facts


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


def _archive_current_request(location, record):
    """Move the current request to one terminal location and write its record."""
    destination = path(location) / current["path"].name

    if destination.exists():
        raise ValueError("terminal request collision")

    destination.mkdir()
    request_file = destination / "request.json"
    shutil.move(str(current["path"]), str(request_file))
    current["path"] = request_file
    current["location"] = location
    write_json(destination / "record.json", record)
    _clear_current_request()


def _clear_current_request():
    """Clear FileTalk's current request register."""
    current["path"] = None
    current["message"] = None
    current["location"] = None


def _is_beneath(candidate_path, root):
    """Return whether one resolved path is beneath or equal to another."""
    try:
        candidate_path.relative_to(root)
    except ValueError:
        return False

    return True
