"""Immutable pending journals and idempotent entity application."""

from pathlib import Path
import re
from uuid import UUID

from .entities import (
    apply_entity_transitions,
    normalize_aspects,
    validate_entity_state,
)
from . import fsio
from .fsio import write_json
from .generation import read_generation
from .identifiers import normalize_entity_id
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
    apply_entity_transitions(entry["entities"])
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
    fsio.read_file(journal_file, ["required", "json"])
    entry = fsio.read["value"]

    if not isinstance(entry, dict):
        raise ValueError("journal entry must contain one JSON object")
    if entry.get("sequence") != filename_facts["sequence"]:
        raise ValueError("journal filename sequence does not match its entry")
    if entry.get("request-id") != filename_facts["request-id"]:
        raise ValueError("journal filename request ID does not match its entry")

    _validate_journal_entity_transitions(entry)

    return entry


def _validate_journal_entity_transitions(entry):
    transitions = entry.get("entities")
    if not isinstance(transitions, dict):
        raise ValueError("journal entry entities must be an object")

    canonical_entity_ids = set()

    for entity_id, transition in transitions.items():
        canonical_entity_id = normalize_entity_id(entity_id)
        if entity_id != canonical_entity_id:
            raise ValueError("journal entry entity IDs must use canonical lowercase UUID form")
        if canonical_entity_id in canonical_entity_ids:
            raise ValueError("journal entry contains duplicate canonical entity IDs")

        canonical_entity_ids.add(canonical_entity_id)
        _validate_journal_entity_transition(transition)


def _validate_journal_entity_transition(transition):
    if not isinstance(transition, dict):
        raise ValueError("journal entity transition must be an object")
    if "before" not in transition or "after" not in transition:
        raise ValueError("journal entity transition must contain before and after states")

    _validate_journal_entity_state(transition["before"])
    _validate_journal_entity_state(transition["after"])


def _validate_journal_entity_state(state):
    if state is None:
        return

    validate_entity_state(state)
    if normalize_aspects(state["aspects"]) != state["aspects"]:
        raise ValueError("journal aspect IDs must use canonical lowercase UUID form")


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
