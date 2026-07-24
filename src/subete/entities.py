"""Authoritative Version 1 entity-file storage."""

from copy import deepcopy
from pathlib import Path
from urllib.parse import quote, unquote
from .fsio import read_json_file, write_json_replace
from .identifiers import normalize_entity_id


def entity_filename(entity_id):
    """Return the reversible Version 1 filename for an M1 entity ID."""
    entity_id = normalize_entity_id(entity_id)
    return f"{quote(entity_id, safe='-_.~')}.json"


def entity_id_from_filename(filename):
    """Return the entity ID represented by one entity filename."""
    name = Path(filename).name
    if not name.endswith(".json"):
        raise ValueError("entity filename must end in .json")
    entity_id = unquote(name[:-5])
    entity_id = normalize_entity_id(entity_id)
    if entity_filename(entity_id) != name:
        raise ValueError("entity filename is not canonical")
    return entity_id


def read_entity(paths, entity_id):
    """Return a complete logical entity state, or None when it is absent."""
    entity_id = normalize_entity_id(entity_id)
    path = entity_path(paths, entity_id)
    if not path.exists():
        return None
    data = read_json_file(path)
    validate_entity_file(data, entity_id)
    return {"revision": data["revision"], "aspects": deepcopy(data["aspects"])}


def write_entity(paths, entity_id, state):
    """Replace one entity with its complete intended logical state."""
    entity_id = normalize_entity_id(entity_id)
    validate_entity_state(state)
    data = {"entity": entity_id, "revision": state["revision"], "aspects": normalize_aspects(state["aspects"])}
    write_json_replace(entity_path(paths, entity_id), data)


def delete_entity(paths, entity_id):
    """Remove an entity file after a caller has authorized its deletion."""
    path = entity_path(paths, normalize_entity_id(entity_id))
    if path.exists():
        path.unlink()


def list_entity_ids(paths):
    """Return all entity IDs in stable lexical identifier order."""
    entity_ids = []
    for path in paths["entities"].glob("*.json"):
        entity_id = entity_id_from_filename(path.name)
        data = read_json_file(path)
        validate_entity_file(data, entity_id)
        entity_ids.append(entity_id)
    return sorted(entity_ids)


def entity_path(paths, entity_id):
    """Return the authoritative path for *entity_id*."""
    return paths["entities"] / entity_filename(normalize_entity_id(entity_id))


def validate_entity_file(data, expected_entity_id):
    """Validate one complete on-disk Version 1 entity record."""
    if not isinstance(data, dict):
        raise ValueError("entity file must contain one JSON object")
    entity_id = normalize_entity_id(data.get("entity"))
    if entity_id != expected_entity_id:
        raise ValueError("entity file entity does not match its filename")
    if data["entity"] != entity_id:
        raise ValueError("entity file UUID must use canonical lowercase form")
    validate_entity_state({"revision": data.get("revision"), "aspects": data.get("aspects")})
    if normalize_aspects(data["aspects"]) != data["aspects"]:
        raise ValueError("entity file UUID aspect IDs must use canonical lowercase form")


def validate_entity_state(state):
    """Validate the journal-compatible state of an existing entity."""
    if not isinstance(state, dict):
        raise ValueError("entity state must be an object")
    revision = state.get("revision")
    aspects = state.get("aspects")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValueError("entity revision must be an integer at least 1")
    if not isinstance(aspects, dict):
        raise ValueError("entity aspects must be an object")
    normalize_aspects(aspects)


def validate_entity_id(entity_id):
    """Validate the Version 1 UUID-or-Tag-URI entity-ID domain."""
    return normalize_entity_id(entity_id)


def normalize_aspects(aspects):
    """Canonicalize UUID aspect keys and reject canonical-key collisions."""
    normalized = {}
    for aspect_id, value in aspects.items():
        canonical_id = normalize_entity_id(aspect_id)
        if canonical_id in normalized:
            raise ValueError("entity aspects contain duplicate canonical IDs")
        normalized[canonical_id] = value
    return normalized
