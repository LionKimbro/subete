"""Validation and dispatch for non-mutating Version 1 requests."""
from uuid import UUID
from .generation import read_generation
from .reads import execute_reads
from .searches import execute_searches
from .transactions import plan_transaction
from .journal import apply_pending, commit_pending, write_pending
from .link_cache import rebuild
from . import request, state

def execute_request():
    message = request.current["message"]
    database_id = state.g["database-id"]
    validate_envelope(message)
    generation = read_generation()
    if message["request-type"] == "transaction":
        transitions = plan_transaction(message["request"]["operations"])
        pending = write_pending(database_id, message, transitions)
        entry = apply_pending(pending)
        rebuild(database_id, entry["sequence"])
        commit_pending(pending, database_id)
        response = {"journal-sequence": entry["sequence"], "entities": [{"entity": key, "revision": value["after"]["revision"]} for key, value in transitions.items() if value["after"] is not None]}
        generation = entry["sequence"]
    elif message["request-type"] == "read":
        response = {"reads": execute_reads(message["request"]["reads"])}
    else:
        response = {"searches": execute_searches(message["request"]["searches"])}
    request.set_response({"request-id": message["request-id"], "request-type": message["request-type"], "status": "success", "generation": generation, "response": response})

def validate_envelope(message):
    if not isinstance(message, dict) or set(message) != {"request-id", "request-type", "reply", "request"}:
        raise ValueError("invalid-request")
    try: UUID(message["request-id"])
    except (ValueError, TypeError) as error: raise ValueError("invalid-request-id") from error
    if message["request-type"] not in {"transaction", "read", "search"}: raise ValueError("unsupported-request-type")
    key = {"transaction":"operations", "read":"reads", "search":"searches"}[message["request-type"]]
    if not isinstance(message["request"], dict) or set(message["request"]) != {key}: raise ValueError("invalid-request")
