"""The selected FileTalk request's process-local lifecycle."""

import shutil

from .fsio import write_json
from .paths import path
from . import filetalk


current = {
    "name": None,
    "path": None,
    "message": None,
    "location": None,
    "response": None,
    "error": None,
}


def system_init_request():
    """Reset the selected request for a fresh service run."""
    _clear_request()

def possess_current_message():
    """Possess the message currently selected by FileTalk."""
    selected = filetalk.selected
    if selected["path"] is None:
        raise ValueError("no request selected")

    _clear_request()
    current["name"] = selected["name"]
    current["path"] = selected["path"]
    current["message"] = selected["message"]
    current["location"] = "inbox"
    filetalk.clear_selected()


def claim_current_message():
    """Move the possessed inbox message to claimed storage."""
    _move_to("claimed")


def set_response(response):
    """Store the response belonging to the possessed request."""
    current["response"] = response


def record_successful_completion():
    """Archive the possessed claimed request as completed."""
    if current["response"] is None:
        raise ValueError("request has no response")

    _move_to("completed")
    _write_terminal()
    _clear_request()


def record_failure_to_complete(error):
    """Archive the possessed claimed request as failed."""
    current["error"] = str(error)
    _move_to("failed")
    _write_terminal()
    _clear_request()


def _move_to(location):
    """Move the current request to one lifecycle location."""
    source = current["path"]
    destination = path(location) / current["name"]

    if location == "claimed":
        source.replace(destination)
        current["path"] = destination
        current["location"] = location
        return

    if destination.exists():
        raise ValueError("terminal request collision")

    destination.mkdir()
    request_file = destination / "request.json"
    shutil.move(str(source), str(request_file))
    current["path"] = request_file
    current["location"] = location


def _write_terminal():
    """Write the terminal record for the current request."""
    if current["location"] == "completed":
        record = {
            "status": "success",
            "response": current["response"],
        }
    elif current["location"] == "failed":
        record = {
            "status": "failure",
            "error": current["error"],
        }
    else:
        raise ValueError("request is not terminal")

    write_json(current["path"].parent / "record.json", record)


def _clear_request():
    """Clear the selected request register."""
    current["name"] = None
    current["path"] = None
    current["message"] = None
    current["location"] = None
    current["response"] = None
    current["error"] = None
