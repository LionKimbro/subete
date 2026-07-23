## Entity Revisions

Every committed entity has a monotonically increasing integer revision.

The revision identifies the committed state of the entity as a whole, including all of its aspects.

A read of an existing entity returns its current revision.

Mutation operations against an existing entity must include the revision that the caller previously observed:

```json
{
  "expected-revision": 12
}
```

Subete accepts the mutation only if the entity’s current committed revision equals `expected-revision`.

If the revisions do not match, the complete transaction fails before journaling or authoritative mutation begins.

This prevents a caller from silently overwriting changes made after it last read the entity.

Revisions belong to entities, not to individual aspects. A change to any aspect advances the revision of the entity.

When a transaction successfully changes an entity, that entity’s revision increases by one, regardless of how many operations within the transaction affected it.

Creating an entity establishes its initial revision.

```json
{
  "revision": 1
}
```

A transaction containing multiple operations against the same existing entity must use the same `expected-revision` for those operations. Later operations observe the transaction’s planned state, but the revision precondition is checked against the committed state that existed before the transaction began.

---

## `set-aspect`

Creates or replaces one complete aspect on an existing entity.

```json
{
  "operation": "set-aspect",
  "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
  "expected-revision": 12,
  "aspect": "tag:m1lattice.net,2026/aspect/basic",
  "value": {
    "typehint": "person",
    "title": "Lion Kimbro",
    "tags": [
      "programmer",
      "writer"
    ]
  }
}
```

### Fields

#### `operation`

```json
{
  "const": "set-aspect",
  "required": true
}
```

#### `entity`

```json
{
  "type": "entity-id",
  "required": true
}
```

#### `expected-revision`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

The committed entity revision previously observed by the caller.

#### `aspect`

```json
{
  "type": "entity-id",
  "required": true
}
```

#### `value`

```json
{
  "required": true
}
```

The complete replacement value for the aspect.

### Rules

* The entity must exist in the transaction’s initial committed state or have been created earlier in the same transaction.
* For a previously existing entity, its committed revision must equal `expected-revision`.
* An entity created earlier in the same transaction does not require `expected-revision` on later operations against it.
* The aspect may already exist or may be new.
* If the aspect exists, its prior value is replaced wholesale.
* If the aspect does not exist, it is created.
* `set-aspect` is not a recursive merge or nested patch.
* Aspect-specific validation may reject an invalid value.
* A successful transaction advances the entity revision by one.

---

## `delete-aspect`

Removes one aspect from an existing entity.

```json
{
  "operation": "delete-aspect",
  "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
  "expected-revision": 12,
  "aspect": "tag:example.net,2026/aspect/obsolete"
}
```

### Fields

#### `operation`

```json
{
  "const": "delete-aspect",
  "required": true
}
```

#### `entity`

```json
{
  "type": "entity-id",
  "required": true
}
```

#### `expected-revision`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

#### `aspect`

```json
{
  "type": "entity-id",
  "required": true
}
```

### Rules

* The entity must exist.
* Its committed revision must equal `expected-revision`.
* If the aspect exists, it is removed.
* If the aspect does not exist, the operation succeeds as a no-op.
* Deleting the final aspect does not automatically delete the entity.
* If the operation changes the entity, the successful transaction advances its revision by one.
* If the aspect was already absent and no other operation changes the entity, its revision does not advance.

---

## `delete-entity`

Removes an entity and all of its authoritative aspects.

```json
{
  "operation": "delete-entity",
  "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
  "expected-revision": 12
}
```

### Fields

#### `operation`

```json
{
  "const": "delete-entity",
  "required": true
}
```

#### `entity`

```json
{
  "type": "entity-id",
  "required": true
}
```

#### `expected-revision`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

### Rules

* The entity must exist.
* Its committed revision must equal `expected-revision`.
* The entity and all of its authoritative aspects are removed.
* Deleting an entity does not recursively delete links or arbitrary references to its identifier.
* A missing entity is not treated as a successful no-op, because its required revision precondition cannot be satisfied.
* Retrying an already committed transaction is handled through `request-id` deduplication rather than by weakening the revision requirement.

---

## Revision Validation Across a Transaction

Before journaling begins, Subete gathers the revision preconditions for every existing entity affected by the transaction.

For each such entity:

* every supplied `expected-revision` must agree;
* the supplied revision must equal the current committed entity revision;
* a mismatch causes the complete transaction to fail;
* no operation is applied and the database generation does not advance.

Example failure:

```json
{
  "request-id": "7be711d6-5801-4e28-a300-81772985bcbb",
  "request-type": "transaction",
  "status": "failure",
  "generation": 142,
  "response": {
    "error": {
      "code": "revision-conflict",
      "message": "The entity changed after the caller last read it.",
      "operation-index": 0,
      "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
      "expected-revision": 12,
      "current-revision": 13
    }
  }
}
```

---

## Read Results Include Revisions

Every successful read of an existing entity returns its current committed revision.

### Selected Aspects

```json
{
  "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
  "status": "found",
  "revision": 12,
  "aspects": [
    {
      "aspect": "tag:m1lattice.net,2026/aspect/basic",
      "status": "found",
      "value": {
        "typehint": "person",
        "title": "Lion Kimbro"
      }
    },
    {
      "aspect": "tag:example.net,2026/aspect/contact",
      "status": "not-found"
    }
  ]
}
```

### All Aspects

```json
{
  "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
  "status": "found",
  "revision": 12,
  "aspects": {
    "tag:m1lattice.net,2026/aspect/basic": {
      "typehint": "person",
      "title": "Lion Kimbro"
    }
  }
}
```

An entity-not-found result has no revision:

```json
{
  "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
  "status": "not-found"
}
```

---

## Transaction Success Response

A successful transaction response reports the resulting revision of every changed or created entity.

```json
{
  "request-id": "7be711d6-5801-4e28-a300-81772985bcbb",
  "request-type": "transaction",
  "status": "success",
  "generation": 143,
  "response": {
    "journal-sequence": 143,
    "entities": [
      {
        "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
        "revision": 13
      }
    ],
    "operations": [
      {
        "index": 0,
        "operation": "set-aspect",
        "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
        "status": "applied"
      }
    ]
  }
}
```

---

## Additional Validation Rules

Before journaling or authoritative mutation begins, Subete validates:

* that every mutation of a previously existing entity supplies `expected-revision`;
* that all expected revisions supplied for the same entity agree;
* that each expected revision matches the current committed entity revision;
* that operations against entities created earlier in the same transaction do not incorrectly claim a prior committed revision.

---

## Additional Error Codes

```text
missing-expected-revision
invalid-expected-revision
inconsistent-expected-revision
revision-conflict
```
