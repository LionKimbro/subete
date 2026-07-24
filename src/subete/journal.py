"""Immutable pending journals and idempotent entity application."""
from pathlib import Path
from .entities import delete_entity, read_entity, write_entity
from .fsio import read_json, write_json
from .generation import read_generation
from .paths import path
from .setup import utc_now

def filename(sequence, request_id): return f"{sequence:020d}__{request_id}.json"

def write_pending(database_id, request, transitions):
    sequence = read_generation() + 1
    entry = {"journal-format-version":1,"database-id":database_id,"sequence":sequence,"journaled":utc_now(),"request-id":request["request-id"],"transaction-request":request,"entities":transitions}
    target = path("journal_pending") / filename(sequence, request["request-id"])
    if target.exists(): raise ValueError("journal-sequence-conflict")
    write_json(target, entry)
    return target

def apply_pending(pending):
    entry = read_json(pending)
    for entity_id in sorted(entry["entities"]):
        transition = entry["entities"][entity_id]; current = read_entity(entity_id)
        if current == transition["after"]: continue
        if current != transition["before"]: raise ValueError("journal-state-mismatch")
        if transition["after"] is None: delete_entity(entity_id)
        else: write_entity(entity_id, transition["after"])
    return entry

def commit_pending(pending, database_id):
    entry = read_json(pending); target = path("journal_committed") / pending.name
    if target.exists():
        if target.read_bytes() != pending.read_bytes(): raise ValueError("journal-commit-conflict")
        pending.unlink()
    else: pending.replace(target)
    write_json("generation", {"generation-format-version":1,"database-id":database_id,"generation":entry["sequence"],"journal-sequence":entry["sequence"],"updated":utc_now()})
    return entry
