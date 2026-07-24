"""FileTalk intake, claims, replies, and terminal request records."""

import shutil
from pathlib import Path

from . import fsio
from .fsio import write_json
from .paths import path

g = {"observations": {}}


def reset():
    """Clear ephemeral incomplete-file observations for a fresh service run."""
    g["observations"].clear()


def discover_messages(now):
    """Return stable complete JSON-object inbox files in deterministic order."""
    messages = []
    for message_file in sorted(path("inbox").iterdir(), key=lambda item: item.name):
        if not message_file.is_file():
            continue
        outcome = read_message_file(message_file)
        if outcome["state"] == "complete-object":
            g["observations"].pop(message_file, None)
            messages.append({"path": message_file, "message": outcome["value"]})
        else:
            observe_unreadable(message_file, now)
    return messages


def read_message_file(path):
    """Classify a candidate without treating incomplete JSON as bad input."""
    fsio.read_json(path)
    if fsio.read["status"] != "complete":
        return {"state": "unreadable"}
    value = fsio.read["data"]
    if not isinstance(value, dict):
        return {"state": "complete-non-object", "value": value}
    return {"state": "complete-object", "value": value}


def observe_unreadable(path, now):
    """Record one unreadable candidate's changing filesystem facts."""
    stat = path.stat()
    current = {"size": stat.st_size, "mtime": stat.st_mtime_ns, "first-seen": now, "last-change": now}
    prior = g["observations"].get(path)
    if prior is not None:
        current["first-seen"] = prior["first-seen"]
        if prior["size"] == current["size"] and prior["mtime"] == current["mtime"]:
            current["last-change"] = prior["last-change"]
    g["observations"][path] = current
    return current


def stale_unreadable(now, quiet_seconds):
    """Return unreadable candidates unchanged for at least the quiet period."""
    return [path for path, fact in g["observations"].items() if path.exists() and now - fact["last-change"] >= quiet_seconds]


def claim_message(source):
    """Move one complete inbox file to claimed storage without overwriting."""
    destination = path("claimed") / source.name
    if destination.exists():
        if source.exists() and source.read_bytes() == destination.read_bytes():
            source.unlink()
            return destination
        raise ValueError("request claim collision")
    source.replace(destination)
    return destination


def validate_reply_destination(configuration, reply):
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
    root = path("root").resolve()
    if is_beneath(parent, root):
        raise ValueError("invalid-reply-destination")
    allowed = configuration.get("filetalk", {}).get("allowed-reply-paths", [])
    if not any(is_beneath(parent, Path(item).resolve()) for item in allowed if isinstance(item, str) and Path(item).is_absolute()):
        raise ValueError("invalid-reply-destination")
    return parent / destination.name


def deliver_reply(configuration, reply, response):
    """Write one response at a validated FileTalk destination."""
    destination = validate_reply_destination(configuration, reply)
    write_json(destination, response)
    return destination


def complete_request(claimed, record):
    """Place a completed request record under its terminal directory."""
    return move_terminal(path("completed"), claimed, record)


def fail_request(claimed, record):
    """Place a failed request record under its terminal directory."""
    return move_terminal(path("failed"), claimed, record)


def move_terminal(directory, claimed, record):
    """Preserve original request bytes alongside structured terminal data."""
    destination = directory / claimed.name
    if destination.exists():
        raise ValueError("terminal request collision")
    destination.mkdir()
    shutil.move(str(claimed), str(destination / "request.json"))
    write_json(destination / "record.json", record)
    return destination


def is_beneath(path, root):
    """Return whether *path* resolves beneath or equals *root*."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
