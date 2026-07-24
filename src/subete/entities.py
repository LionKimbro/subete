"""Authoritative Version 1 entity-file storage.

read_aspects(entity_id, aspect_ids)
  |
  `--> read_entity(entity_id)
         |
         `--> _entity_path(entity_id)
                |
                `--> entity_filename(entity_id)


list_ids()
  |
  `--> _read_entity_id_from_filename(filename)


apply_entity_transitions(transitions)
  |
  `--> _apply_entity_transition(entity_id, transition)
         |
         +--> read_entity(entity_id)
         |      `--> _entity_path(entity_id)
         |             `--> entity_filename(entity_id)
         |
         +--> _entity_states_match(current, state)
         |      `--> _entity_states_match(left, right) [recursive]
         |
         +--> _delete_entity_file(entity_id)
         |      `--> _entity_path(entity_id)
         |
         `--> _write_complete_entity_state(entity_id, state)
                `--> _entity_path(entity_id)


validate_entity_state(state)
  |
  +--> _is_entity_revision(value)
  |
  `--> normalize_aspects(aspects)
         |
         +--> _validate_json_value(value)
         |      `--> _validate_json_value(value) [recursive]
         |
         `--> normalize_entity_id(aspect_id) [external]


validate_entity_id(entity_id)
  |
  `--> normalize_entity_id(entity_id) [external]
"""

from copy import deepcopy
import math
from pathlib import Path
from urllib.parse import quote, unquote

from . import fsio
from .fsio import write_json
from .identifiers import normalize_entity_id
from .paths import path


ENTITY_STATE_KEYS = {
    "revision",
    "aspects",
}


def entity_filename(entity_id):
    """Return the reversible Version 1 filename for an M1 entity ID.

    Current callers:
        _entity_path; link-cache rebuild

    Why it exists for them:
        _entity_path needs the authoritative filename to locate an entity;
        link cache needs the same encoding for endpoint cache files.
    """
    return f"{quote(entity_id, safe='-_.~')}.json"


def _read_entity_id_from_filename(filename):
    """Read the entity ID represented by one stored entity filename.

    Current callers:
        list_ids

    Why it exists for them:
        Enumeration needs to turn each stored filename back into the ID it
        represents.
    """
    name = Path(filename).name

    return unquote(name[:-5])


def _entity_path(entity_id):
    """Return the authoritative path for one entity ID.

    Current callers:
        read_entity, _write_complete_entity_state, _delete_entity_file

    Why it exists for them:
        These three physical operations need one shared mapping from an
        internal ID to its file.
    """
    return path("entities") / entity_filename(entity_id)


def read_entity(entity_id):
    """Return one complete entity state, or None when the entity is absent.

    Current callers:
        read_aspects, _apply_entity_transition, transaction planning, reads,
        searches, link-cache rebuild

    Why it exists for them:
        All of these need the complete currently stored state of an entity.
    """
    entity_file = _entity_path(entity_id)

    if not entity_file.exists():
        return None

    fsio.read_json(entity_file, ["required"])
    record = fsio.read["data"]

    return {
        "revision": record["revision"],
        "aspects": deepcopy(record["aspects"]),
    }


def read_aspects(entity_id, aspect_ids):
    """Return selected aspects from one entity, or None when it is absent.

    Current callers:
        Read protocol

    Why it exists for them:
        The read protocol needs a store-owned way to return only selected
        aspects.
    """
    entity = read_entity(entity_id)

    if entity is None:
        return None

    selected = {}

    for aspect_id in aspect_ids:
        if aspect_id in entity["aspects"]:
            selected[aspect_id] = deepcopy(entity["aspects"][aspect_id])

    return {
        "revision": entity["revision"],
        "aspects": selected,
    }


def _write_complete_entity_state(entity_id, state):
    """Replace one entity with its complete intended state.

    Current callers:
        _apply_entity_transition

    Why it exists for them:
        Applying a trusted journal transition needs one physical operation to
        replace the complete resulting entity state.
    """
    record = {
        "entity": entity_id,
        "revision": state["revision"],
        "aspects": state["aspects"],
    }

    write_json(_entity_path(entity_id), record)


def _delete_entity_file(entity_id):
    """Remove one entity file after a caller has authorized its deletion.

    Current callers:
        _apply_entity_transition

    Why it exists for them:
        Applying a trusted transition whose after-state is absence needs one
        physical deletion operation.
    """
    entity_file = _entity_path(entity_id)

    if entity_file.exists():
        entity_file.unlink()


def list_ids():
    """Return all entity IDs in stable decoded-identifier order.

    Current callers:
        Searches; link-cache rebuild

    Why it exists for them:
        Both need a stable complete traversal of the entity store.
    """
    entity_ids = []

    for entity_file in path("entities").glob("*.json"):
        entity_id = _read_entity_id_from_filename(entity_file.name)

        entity_ids.append(entity_id)

    return sorted(entity_ids)


def apply_entity_transitions(transitions):
    """Apply complete intended entity transitions in identifier order.

    Current callers:
        Journal application

    Why it exists for them:
        Journal application needs the store to apply its trusted transitions
        in deterministic ID order.
    """
    for entity_id in sorted(transitions):
        _apply_entity_transition(entity_id, transitions[entity_id])


def _apply_entity_transition(entity_id, transition):
    """Apply one complete before/after transition, or accept its after-state.

    Current callers:
        apply_entity_transitions

    Why it exists for them:
        The batch applicator needs one machine that handles the idempotent
        before/current/after rule for a single entity.
    """
    current = read_entity(entity_id)

    if _entity_states_match(current, transition["after"]):
        return

    if not _entity_states_match(current, transition["before"]):
        raise ValueError("entity state does not match its journal before-state")

    if transition["after"] is None:
        _delete_entity_file(entity_id)
        return

    _write_complete_entity_state(entity_id, transition["after"])


def validate_entity_state(state):
    """Validate one present complete entity state.

    Current callers:
        Journal entry validation

    Why it exists for them:
        It currently verifies that a journal's present before/after state has
        a revision and aspects map of the expected shape.
    """
    if not isinstance(state, dict):
        raise ValueError("entity state must be an object")
    if set(state) != ENTITY_STATE_KEYS:
        raise ValueError("entity state has missing or unknown fields")
    if not _is_entity_revision(state["revision"]):
        raise ValueError("entity revision must be an integer at least 1")

    normalize_aspects(state["aspects"])


def validate_entity_id(entity_id):
    """Validate and return one Version 1 UUID-or-Tag-URI entity ID.

    Current callers:
        Request reads, searches, transaction planning

    Why it exists for them:
        These are request-validation paths; they need to turn external
        entity/aspect IDs into canonical internal IDs.
    """
    return normalize_entity_id(entity_id)


def normalize_aspects(aspects):
    """Canonicalize aspect keys and validate every complete JSON value.

    Current callers:
        Transaction planning; journal entry validation

    Why it exists for them:
        Transaction planning uses it to canonicalize externally supplied
        initial aspect maps; journal validation currently uses it to check
        stored aspect IDs.
    """
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
    """Return whether two entity states have the same JSON structure and types.

    Current callers:
        _apply_entity_transition, recursively

    Why it exists for them:
        Transition application needs type-exact comparison to recognize
        “already after,” “still before,” or an incoherent state.
    """
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


def _is_entity_revision(value):
    """Return whether a value is an allowed entity revision.

    Current callers:
        validate_entity_state

    Why it exists for them:
        The state validator needs one precise definition of an allowed
        revision.
    """
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _validate_json_value(value):
    """Validate that a value can be represented as JSON.

    Current callers:
        normalize_aspects, recursively

    Why it exists for them:
        Aspect-map normalization needs to ensure gate-supplied values can
        become JSON.
    """
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
