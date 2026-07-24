"""Committed-generation read selection and result construction."""

from copy import deepcopy

from .entities import read_entity, validate_entity_id


def execute_reads(paths, reads):
    """Evaluate validated read specifications against the current entity files."""
    validate_reads(reads)
    results = []
    for read in reads:
        entity_id = read["entity"]
        entity = read_entity(paths, entity_id)
        if entity is None:
            results.append({"entity": entity_id, "status": "not-found"})
            continue
        results.append(select_aspects(entity_id, entity, read["aspects"]))
    return results


def validate_reads(reads):
    """Validate the protocol's batch read selectors."""
    if not isinstance(reads, list) or not reads:
        raise ValueError("reads must be a nonempty array")
    for read in reads:
        if not isinstance(read, dict) or set(read) != {"entity", "aspects"}:
            raise ValueError("each read must contain entity and aspects")
        read["entity"] = validate_entity_id(read["entity"])
        aspects = read["aspects"]
        if aspects == "*":
            continue
        if not isinstance(aspects, list):
            raise ValueError("read aspects must be '*' or an array")
        normalized = [validate_entity_id(aspect_id) for aspect_id in aspects]
        if len(set(normalized)) != len(normalized):
            raise ValueError("read aspects must not contain duplicate canonical IDs")
        read["aspects"] = normalized


def select_aspects(entity_id, entity, selector):
    """Construct one found read result from a complete entity state."""
    aspects = entity["aspects"]
    if selector == "*":
        selected = {key: deepcopy(aspects[key]) for key in sorted(aspects)}
    else:
        selected = {key: deepcopy(aspects[key]) for key in selector if key in aspects}
    return {"entity": entity_id, "status": "found", "revision": entity["revision"], "aspects": selected}
