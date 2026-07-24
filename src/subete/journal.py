"""Immutable pending journals and idempotent entity application."""

from pathlib import Path
import re
from uuid import UUID

from .entities import delete_entity, read_entity, write_entity
from . import fsio
from .fsio import write_json
from .generation import read_generation
from .paths import path
from .setup import utc_now


JOURNAL_FILENAME = re.compile(r"^([0-9]{20})__([0-9A-Fa-f-]{36})\.json$")


def journal_filename(sequence, request_id):
    """Return the canonical durable filename for one journal entry."""
    _validate_journal_sequence(sequence)
    _validate_journal_request_id(request_id)
    return f"{sequence:020d}__{request_id}.json"


def parse_journal_filename(filename):
    """Return the sequence and request ID encoded in one journal filename."""
    name = Path(filename).name
    if name != str(filename):
        raise ValueError("journal filename must not include a directory")

    match = JOURNAL_FILENAME.fullmatch(name)
    if match is None:
        raise ValueError("journal filename has an invalid format")

    sequence = int(match.group(1))
    request_id = match.group(2)
    _validate_journal_sequence(sequence)
    _validate_journal_request_id(request_id)

    return {
        "sequence": sequence,
        "request-id": request_id,
    }

def write_pending(database_id, request, transitions):
    sequence = read_generation() + 1
    entry = {"journal-format-version":1,"database-id":database_id,"sequence":sequence,"journaled":utc_now(),"request-id":request["request-id"],"transaction-request":request,"entities":transitions}
    target = path("journal_pending") / journal_filename(sequence, request["request-id"])
    if target.exists(): raise ValueError("journal-sequence-conflict")
    write_json(target, entry)
    return target

def apply_pending(pending):
    entry = read_validated_journal_entry(pending)
    for entity_id in sorted(entry["entities"]):
        transition = entry["entities"][entity_id]; current = read_entity(entity_id)
        if current == transition["after"]: continue
        if current != transition["before"]: raise ValueError("journal-state-mismatch")
        if transition["after"] is None: delete_entity(entity_id)
        else: write_entity(entity_id, transition["after"])
    return entry

def commit_pending(pending, database_id):
    entry = read_validated_journal_entry(pending); target = path("journal_committed") / pending.name
    if target.exists():
        if target.read_bytes() != pending.read_bytes(): raise ValueError("journal-commit-conflict")
        pending.unlink()
    else: pending.replace(target)
    write_json("generation", {"generation-format-version":1,"database-id":database_id,"generation":entry["sequence"],"journal-sequence":entry["sequence"],"updated":utc_now()})
    return entry


def read_validated_journal_entry(journal_file):
    """Read one journal entry after verifying the filename agrees with it."""
    filename_facts = parse_journal_filename(journal_file.name)
    fsio.read_json(journal_file, ["required"])
    entry = fsio.read["data"]

    if not isinstance(entry, dict):
        raise ValueError("journal entry must contain one JSON object")
    if entry.get("sequence") != filename_facts["sequence"]:
        raise ValueError("journal filename sequence does not match its entry")
    if entry.get("request-id") != filename_facts["request-id"]:
        raise ValueError("journal filename request ID does not match its entry")

    return entry


def _validate_journal_sequence(sequence):
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError("journal sequence must be a positive integer")


def _validate_journal_request_id(request_id):
    if not isinstance(request_id, str):
        raise ValueError("journal request ID must be a UUID string")

    try:
        UUID(request_id)
    except ValueError as error:
        raise ValueError("journal request ID must be a UUID string") from error
