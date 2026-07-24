"""Version 1 full-scan search predicates."""

from .entities import list_ids, read_entity, validate_entity_id

BASIC_ASPECT = "tag:m1lattice.net,2026:aspect/basic"
PREDICATES = {"typehint", "has-aspects", "tags", "name-contains", "title-contains"}


def execute_searches(searches):
    """Evaluate all validated searches by scanning authoritative entity files."""
    validate_searches(searches)
    entity_ids = list_ids()
    results = []
    for index, search in enumerate(searches):
        matches = [entity_id for entity_id in entity_ids if matches_search(read_entity(entity_id), search)]
        results.append({"index": index, "entities": matches})
    return results


def validate_searches(searches):
    """Validate Version 1 search request predicates before scanning."""
    if not isinstance(searches, list) or not searches:
        raise ValueError("searches must be a nonempty array")
    for search in searches:
        if not isinstance(search, dict) or not search:
            raise ValueError("each search must be a nonempty object")
        if set(search) - PREDICATES:
            raise ValueError("search contains an unsupported predicate")
        _validate_search(search)


def matches_search(entity, search):
    """Return whether one complete entity state satisfies all predicates."""
    aspects = entity["aspects"]
    basic = aspects.get(BASIC_ASPECT)
    if "has-aspects" in search and not set(search["has-aspects"]).issubset(aspects):
        return False
    if any(key in search for key in ("typehint", "tags", "name-contains", "title-contains")) and not isinstance(basic, dict):
        return False
    if "typehint" in search and (not isinstance(basic.get("typehint"), str) or basic["typehint"].casefold() != search["typehint"].casefold()):
        return False
    if "tags" in search:
        entity_tags = basic.get("tags")
        if not isinstance(entity_tags, list) or not set(tag.casefold() for tag in search["tags"]).issubset(tag.casefold() for tag in entity_tags if isinstance(tag, str)):
            return False
    for key, field in (("name-contains", "name"), ("title-contains", "title")):
        if key in search and (not isinstance(basic.get(field), str) or search[key].casefold() not in basic[field].casefold()):
            return False
    return True


def _validate_search(search):
    if "typehint" in search and not isinstance(search["typehint"], str):
        raise ValueError("typehint must be a string")
    if "has-aspects" in search:
        values = search["has-aspects"]
        if not isinstance(values, list) or not values:
            raise ValueError("has-aspects must be a nonempty array")
        normalized = [validate_entity_id(value) for value in values]
        if len(set(normalized)) != len(normalized):
            raise ValueError("has-aspects must not contain duplicates")
        search["has-aspects"] = normalized
    if "tags" in search:
        values = search["tags"]
        if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
            raise ValueError("tags must be a nonempty array of nonempty strings")
        if len({value.casefold() for value in values}) != len(values):
            raise ValueError("tags must not contain case-insensitive duplicates")
    for key in ("name-contains", "title-contains"):
        if key in search and (not isinstance(search[key], str) or not search[key]):
            raise ValueError(f"{key} must be a nonempty string")
