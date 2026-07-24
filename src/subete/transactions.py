"""Pure Version 1 transaction planning."""
from copy import deepcopy
from .entities import read_entity, validate_entity_id, normalize_aspects

def plan_transaction(operations):
    """Return complete logical entity transitions without mutating storage."""
    if not isinstance(operations, list) or not operations: raise ValueError("operations must be a nonempty array")
    targets = {}
    for index, operation in enumerate(operations):
        validate_operation(operation)
        entity = validate_entity_id(operation["entity"])
        operation["entity"] = entity
        targets.setdefault(entity, []).append((index, operation))
    transitions = {}
    for entity, group in targets.items():
        before = read_entity(entity)
        after = plan_entity(before, group)
        transitions[entity] = {"before": before, "after": after}
    return transitions

def validate_operation(operation):
    if not isinstance(operation, dict) or operation.get("operation") not in {"create-entity", "set-aspect", "delete-aspect", "delete-entity"}: raise ValueError("invalid-operation")
    validate_entity_id(operation.get("entity"))
    kind = operation["operation"]
    if kind == "create-entity":
        if set(operation) - {"operation", "entity", "aspects"}: raise ValueError("invalid-operation")
        if "aspects" in operation and not isinstance(operation["aspects"], dict): raise ValueError("invalid-aspects")
    else:
        if not isinstance(operation.get("expected-revision"), int) or isinstance(operation["expected-revision"], bool): raise ValueError("invalid-revision")
        if kind != "delete-entity":
            validate_entity_id(operation.get("aspect"))
            if kind == "set-aspect" and "value" not in operation: raise ValueError("missing-value")

def plan_entity(before, group):
    kinds = {item[1]["operation"] for item in group}
    if "create-entity" in kinds:
        if before is not None or len(group) != 1: raise ValueError("entity-already-exists-or-conflict")
        return {"revision": 1, "aspects": normalize_aspects(deepcopy(group[0][1].get("aspects", {})))}
    if before is None: raise ValueError("entity-not-found")
    if "delete-entity" in kinds:
        if len(group) != 1 or group[0][1]["expected-revision"] != before["revision"]: raise ValueError("entity-conflict")
        return None
    expected = {item[1]["expected-revision"] for item in group}
    if expected != {before["revision"]}: raise ValueError("revision-conflict")
    after = deepcopy(before); changed = False; seen = set()
    for _, operation in group:
        aspect = validate_entity_id(operation["aspect"])
        if aspect in seen: raise ValueError("aspect-conflict")
        seen.add(aspect)
        if operation["operation"] == "set-aspect":
            if after["aspects"].get(aspect, object()) != operation["value"]: after["aspects"][aspect] = deepcopy(operation["value"]); changed = True
        elif aspect in after["aspects"]:
            del after["aspects"][aspect]; changed = True
    if changed: after["revision"] += 1
    return after
