"""Authoritative Version 1 entity-file storage."""

from copy import deepcopy
import math
from pathlib import Path
from urllib.parse import quote, unquote

from . import fsio
from .fsio import write_json
from .identifiers import normalize_entity_id
from .paths import path


ENTITY_FILE_KEYS = {
    "entity",
    "revision",
    "aspects",
}

ENTITY_STATE_KEYS = {
    "revision",
    "aspects",
}


def entity_filename(entity_id):
    """Return the reversible Version 1 filename for an M1 entity ID."""
    entity_id = normalize_entity_id(entity_id)
    return f"{quote(entity_id, safe='-_.~')}.json"


def _entity_id_from_filename(filename):
    """Return the entity ID represented by one canonical entity filename."""
    name = Path(filename).name

    if name != str(filename):
        raise ValueError("entity filename must not include a directory")
    if not name.endswith(".json"):
        raise ValueError("entity filename must end in .json")

    entity_id = normalize_entity_id(unquote(name[:-5]))

    if entity_filename(entity_id) != name:
        raise ValueError("entity filename is not canonical")

    return entity_id


def _entity_path(entity_id):
    """Return the authoritative path for one entity ID."""
    return path("entities") / entity_filename(entity_id)


def read_entity(entity_id):
    """Return one complete entity state, or None when the entity is absent."""
    entity_id = normalize_entity_id(entity_id)
    entity_file = _entity_path(entity_id)

    if not entity_file.exists():
        return None

    fsio.read_json(entity_file, ["required"])
    record = fsio.read["data"]
    _validate_entity_file(record, entity_id)

    return {
        "revision": record["revision"],
        "aspects": deepcopy(record["aspects"]),
    }


def read_aspects(entity_id, aspect_ids):
    """Return selected aspects from one entity, or None when it is absent."""
    entity = read_entity(entity_id)

    if entity is None:
        return None

    selected = {}

    for aspect_id in aspect_ids:
        aspect_id = normalize_entity_id(aspect_id)

        if aspect_id in entity["aspects"]:
            selected[aspect_id] = deepcopy(entity["aspects"][aspect_id])

    return {
        "revision": entity["revision"],
        "aspects": selected,
    }


def _write_complete_entity_state(entity_id, state):
    """Replace one entity with its complete intended state."""
    entity_id = normalize_entity_id(entity_id)
    validate_entity_state(state)

    record = {
        "entity": entity_id,
        "revision": state["revision"],
        "aspects": normalize_aspects(state["aspects"]),
    }

    write_json(_entity_path(entity_id), record)


def _delete_entity_file(entity_id):
    """Remove one entity file after a caller has authorized its deletion."""
    entity_file = _entity_path(entity_id)

    if entity_file.exists():
        entity_file.unlink()


def list_ids():
    """Return all entity IDs in stable decoded-identifier order."""
    entity_ids = []

    for entity_file in path("entities").glob("*.json"):
        entity_id = _entity_id_from_filename(entity_file.name)
        fsio.read_json(entity_file, ["required"])
        _validate_entity_file(fsio.read["data"], entity_id)

        if entity_id in entity_ids:
            raise ValueError("entity files contain duplicate entity IDs")

        entity_ids.append(entity_id)

    return sorted(entity_ids)


def apply_entity_transitions(transitions):
    """Apply complete intended entity transitions in identifier order."""
    if not isinstance(transitions, dict):
        raise ValueError("entity transitions must be an object")

    canonical_transitions = {}

    for entity_id, transition in transitions.items():
        canonical_entity_id = normalize_entity_id(entity_id)

        if canonical_entity_id in canonical_transitions:
            raise ValueError("entity transitions contain duplicate canonical IDs")

        canonical_transitions[canonical_entity_id] = transition

    for entity_id in sorted(canonical_transitions):
        _apply_entity_transition(entity_id, canonical_transitions[entity_id])


def _apply_entity_transition(entity_id, transition):
    """Apply one complete before/after transition, or accept its after-state."""
    entity_id = normalize_entity_id(entity_id)
    _validate_entity_transition(transition)
    current = read_entity(entity_id)

    if _entity_states_match(current, transition["after"]):
        return

    if not _entity_states_match(current, transition["before"]):
        raise ValueError("entity state does not match its journal before-state")

    if transition["after"] is None:
        _delete_entity_file(entity_id)
        return

    _write_complete_entity_state(entity_id, transition["after"])


def _validate_entity_file(record, expected_entity_id):
    """Validate one complete on-disk Version 1 entity record."""
    if not isinstance(record, dict):
        raise ValueError("entity file must contain one JSON object")
    if set(record) != ENTITY_FILE_KEYS:
        raise ValueError("entity file has missing or unknown fields")

    expected_entity_id = normalize_entity_id(expected_entity_id)
    entity_id = normalize_entity_id(record["entity"])

    if entity_id != expected_entity_id:
        raise ValueError("entity file entity does not match its filename")
    if record["entity"] != entity_id:
        raise ValueError("entity file UUID must use canonical lowercase form")

    validate_entity_state(
        {
            "revision": record["revision"],
            "aspects": record["aspects"],
        }
    )

    if normalize_aspects(record["aspects"]) != record["aspects"]:
        raise ValueError("entity file UUID aspect IDs must use canonical lowercase form")


def _validate_entity_transition(transition):
    """Validate one complete journal-facing entity before/after transition."""
    if not isinstance(transition, dict):
        raise ValueError("entity transition must be an object")
    if set(transition) != {"before", "after"}:
        raise ValueError("entity transition must contain only before and after states")

    _validate_present_entity_state(transition["before"])
    _validate_present_entity_state(transition["after"])


def validate_entity_state(state):
    """Validate one present complete entity state."""
    if not isinstance(state, dict):
        raise ValueError("entity state must be an object")
    if set(state) != ENTITY_STATE_KEYS:
        raise ValueError("entity state has missing or unknown fields")
    if not _is_entity_revision(state["revision"]):
        raise ValueError("entity revision must be an integer at least 1")

    normalize_aspects(state["aspects"])


def validate_entity_id(entity_id):
    """Validate and return one Version 1 UUID-or-Tag-URI entity ID."""
    return normalize_entity_id(entity_id)


def normalize_aspects(aspects):
    """Canonicalize aspect keys and validate every complete JSON value."""
    if not isinstance(aspects, dict):
        raise ValueError("entity aspects must be an object")

    normalized = {}

    for aspect_id, value in aspects.items():
        canonical_id = normalize_entity_id(aspect_id)

        if canonical_id in normalized:
            raise ValueError("entity aspects contain duplicate canonical IDs")

        _validate_json_value(value)
        normalized[canonical_id] = value

    return normalized


def _entity_states_match(left, right):
    """Return whether two entity states have the same JSON structure and types."""
    if type(left) is not type(right):
        return False

    if isinstance(left, dict):
        if set(left) != set(right):
            return False

        return all(_entity_states_match(left[key], right[key]) for key in left)

    if isinstance(left, list):
        if len(left) != len(right):
            return False

        return all(_entity_states_match(item, right[index]) for index, item in enumerate(left))

    return left == right


def _validate_present_entity_state(state):
    if state is not None:
        validate_entity_state(state)


def _is_entity_revision(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _validate_json_value(value):
    if value is None or isinstance(value, (bool, str, int)):
        return

    if isinstance(value, float):
        if math.isfinite(value):
            return

        raise ValueError("entity aspect values must contain valid JSON numbers")

    if isinstance(value, list):
        for item in value:
            _validate_json_value(item)
        return

    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("entity JSON object keys must be strings")

            _validate_json_value(item)
        return

    raise ValueError("entity aspect values must be valid JSON values")
