"""The sequential FileTalk request lifecycle."""

from pathlib import Path

from . import fsio, state
from .fsio import write_json
from .paths import path


observations = {}

selected = {
    "name": None,
    "path": None,
    "message": None,
}


def system_init_filetalk():
    """Reset FileTalk's observations for a fresh service run."""
    _reset_filetalk_observations()
    clear_selected()


def discover_next_message():
    """Select the first stable complete inbox message for possession."""
    clear_selected()

    for message_file in sorted(path("inbox").iterdir(), key=lambda item: item.name):
        if not message_file.is_file():
            continue

        fsio.read_file(message_file, ["json", "stat"])
        status = fsio.read["status"]
        data = fsio.read["value"]

        if status == "complete" and isinstance(data, dict):
            observations.pop(message_file, None)
            selected["name"] = message_file.name
            selected["path"] = message_file
            selected["message"] = data
            return True

        _record_unreadable_message()

    return False


def deliver_reply_back_to_sender():
    """Publish the possessed request's response to its permitted destination."""
    from . import request

    reply = request.current["message"]["reply"]
    response = request.current["response"]
    destination = _validate_reply_destination(reply)
    write_json(destination, response)
    return destination


def list_stale_unreadable_messages():
    """Return unreadable messages unchanged for the configured quiet period."""
    quiet_seconds = state.configuration["polling"]["incomplete-file-quiet-seconds"]

    return [
        message_file
        for message_file, facts in observations.items()
        if message_file.exists() and state.g["now"] - facts["last-change"] >= quiet_seconds
    ]


def _reset_filetalk_observations():
    """Clear incomplete-file observations for a fresh service run."""
    observations.clear()


def _record_unreadable_message():
    """Record one unreadable message's changing filesystem facts."""
    message_file = fsio.read["source"]
    stat = fsio.read["stat"]
    current_facts = {
        "size": stat["size"],
        "mtime": stat["mtime"],
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


def clear_selected():
    """Clear the transient message selected for request possession."""
    selected["name"] = None
    selected["path"] = None
    selected["message"] = None


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


def _is_beneath(candidate_path, root):
    """Return whether one resolved path is beneath or equal to another."""
    try:
        candidate_path.relative_to(root)
    except ValueError:
        return False

    return True
