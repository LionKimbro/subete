# Subete — CRUD and Read Protocol

This document defines the request and reply semantics for creating, reading, updating, and deleting entities and aspects in Subete.

The protocol has two request families:

* transaction requests, which may modify authoritative state;
* read requests, which observe committed state without modifying it.

Search requests are defined separately.

The structures in this document are written as Markdown SoftSpec. Examples illustrate intended meaning and may omit fields that are not relevant to the example.

---

## CRUD Request Envelope and Shared Delivery

The shared message-file envelope, file receipt, claiming, incomplete-file handling, and SASE file reply delivery rules are defined in [filetalk-protocol.md](filetalk-protocol.md). That shared protocol also permits one-way message families with no reply destination.

CRUD and read messages are request/response communications. A request defined by this document contains:

* a required UUID `request-id`;
* a required `request-type`, either `"transaction"` or `"read"`;
* a required `reply` destination using a form supported by the shared delivery protocol;
* a required `request` object containing the request-family-specific body.

The `reply` requirement belongs to this CRUD/read protocol.

---

# Transaction Requests

A transaction request contains one or more mutation operations.

```json
{
  "request-id": "7be711d6-5801-4e28-a300-81772985bcbb",
  "request-type": "transaction",
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/7be711d6-5801-4e28-a300-81772985bcbb.json"
  },
  "request": {
    "operations": [
      {
        "operation": "create-entity",
        "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "typehint": "person",
            "name": "lion",
            "title": "Lion Kimbro"
          }
        }
      }
    ]
  }
}
```

## Transaction Body

```json
{
  "operations": [
    {
      "...": "operation"
    }
  ]
}
```

### `operations`

```json
{
  "type": "array",
  "required": true,
  "minimum-items": 1
}
```

A serialized collection of mutation operations. Array position is retained for deterministic reporting and error locations, but does not give operations execution-order semantics.

A transaction may affect:

* multiple aspects;
* multiple entities;
* both existing and newly created entities;
* link entities and ordinary entities;
* aspects backed by different authoritative storage mechanisms.

All operations belong to one logical transaction.

The transaction is validated and planned as a whole before authoritative mutation begins.

If any operation is invalid, the transaction fails without beginning datastore mutation.

---

## Transaction Semantics

### Atomic Logical Result

A transaction has one complete intended after-state.

Its operations are not independently committed.

Subete must not accept only a successful subset of the operations.

### Operation Independence and Conflicts

Operations in a transaction do not have execution-order semantics.

The transaction describes one complete set of mutations to be committed atomically. No operation observes an intermediate result produced by another operation in the same transaction.

Operations must not conflict:

* `create-entity` must be the only operation targeting that entity;
* `delete-entity` must be the only operation targeting that entity;
* an existing entity may have multiple aspect operations when they target different aspects;
* the same aspect on the same entity may not be set or deleted more than once in one transaction;
* all operations against the same existing entity must supply the same `expected-revision`.

Creating and then modifying an entity is invalid; `create-entity` must provide its complete initial set of aspects. Modifying and then deleting an entity is also invalid because `delete-entity` already describes the complete intended mutation for that entity.

The serialized order of operations is retained for deterministic reporting and error locations, but it does not affect the transaction's meaning.

For example, setting one aspect and deleting a different aspect on the same existing entity is valid. Both operations independently describe parts of the transaction's intended after-state:

```json
{
  "operations": [
    {
      "operation": "set-aspect",
      "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
      "expected-revision": 12,
      "aspect": "tag:m1lattice.net,2026/aspect/basic",
      "value": {
        "title": "Updated title"
      }
    },
    {
      "operation": "delete-aspect",
      "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
      "expected-revision": 12,
      "aspect": "tag:example.net,2026/aspect/obsolete"
    }
  ]
}
```

### Whole-Aspect Replacement

`set-aspect` replaces the complete current value of one aspect.

The protocol does not define nested field patches.

A caller that wants to change one field normally:

1. reads the whole aspect;
2. modifies the value locally;
3. submits the complete replacement aspect.

This rule keeps mutation meaning explicit and independent of aspect-specific internal structure.

### Entity Revisions

Every committed entity has a monotonically increasing integer revision.

The revision identifies the committed state of the entity as a whole, including all of its aspects. Revisions belong to entities, not to individual aspects.

A read of an existing entity returns its current revision. A mutation against an entity that existed before the transaction began must include the revision that the caller previously observed:

```json
{
  "expected-revision": 12
}
```

Subete accepts the transaction only if each affected existing entity's current committed revision equals the supplied `expected-revision`. A mismatch fails the complete transaction before journaling or authoritative mutation begins. This prevents a caller from silently overwriting changes committed after its read.

Creating an entity establishes revision `1`.

When a transaction successfully changes an existing entity, that entity's revision increases by one, regardless of how many operations in the transaction affect it. A successful no-op does not by itself advance the entity revision.

For multiple operations against the same existing entity:

* every operation must supply the same `expected-revision`;
* the precondition is checked against committed state from before the transaction began;
* the entity revision advances at most once when the complete transaction commits.

---

# Mutation Operations

## `create-entity`

Creates a new entity.

```json
{
  "operation": "create-entity",
  "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
  "aspects": {
    "tag:m1lattice.net,2026/aspect/basic": {
      "typehint": "person",
      "title": "Lion Kimbro"
    }
  }
}
```

### Fields

#### `operation`

```json
{
  "const": "create-entity",
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

The stable identifier of the new entity.

The initial protocol requires callers to provide the entity ID.

Entity minting by Subete may be added separately later.

#### `aspects`

```json
{
  "type": "object",
  "required": false,
  "default": {}
}
```

Maps aspect IDs to complete aspect values.

An entity may be created with no initial aspects.

### Rules

* The entity must not already exist in committed state.
* `create-entity` must be the only operation in the transaction targeting this entity.
* Aspect IDs must be valid entity IDs.
* Each supplied value is the complete value of that aspect.
* The operation fails if the entity already exists.
* A successfully created entity begins at revision `1`.
* Creation does not implicitly create any related entities.
* Creating a link entity does not require its endpoint entities to exist unless a separate validation policy requires that.

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

The value is normally a JSON object, but the accepted value domain follows the governing M1 aspect rules.

### Rules

* The entity must exist in committed state.
* Its committed revision must equal `expected-revision`.
* The aspect may already exist or may be new.
* If the aspect exists, its prior value is replaced wholesale.
* If the aspect does not exist, it is created.
* Omitted fields from the old aspect do not survive unless they are also present in the new value.
* `set-aspect` is not a recursive merge.
* `set-aspect` is not a JSON Patch operation.
* Aspect-specific validation may reject an invalid value.
* If the transaction changes the entity, its revision advances by one when the transaction commits.
* No other operation in the transaction may target the same aspect on this entity.

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

The committed entity revision previously observed by the caller.

#### `aspect`

```json
{
  "type": "entity-id",
  "required": true
}
```

### Rules

* The entity must exist in committed state.
* Its committed revision must equal `expected-revision`.
* If the aspect exists, it is removed.
* If the aspect does not exist, the operation succeeds as a no-op.
* Deleting the final aspect does not automatically delete the entity.
* Deleting the link aspect from a link entity causes that entity to cease being recognized as a link.
* Derived structures affected by the deleted aspect must be reconciled before the resulting generation is presented as current.
* If the aspect existed, the entity revision advances by one when the transaction commits.
* If the aspect was already absent and no other operation changes the entity, its revision does not advance.
* No other operation in the transaction may target the same aspect on this entity.

Missing-aspect deletion is a successful no-op so that retries and recovery remain simple.

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

The committed entity revision previously observed by the caller.

### Rules

* The entity must exist in committed state.
* Its committed revision must equal `expected-revision`.
* `delete-entity` must be the only operation in the transaction targeting this entity.
* The entity and all of its authoritative aspects are removed.
* Deleting an entity does not recursively delete links that refer to it.
* Deleting an entity does not recursively delete arbitrary entities that reference it.
* Existing links may continue to refer to the deleted entity ID.
* Derived structures for the deleted entity must be reconciled before the resulting generation is presented as current.

A missing entity is not a successful no-op because its required revision precondition cannot be satisfied. Retrying an already committed transaction is handled through `request-id` deduplication rather than by weakening the revision requirement.

---

# Batched Transaction Example

```json
{
  "request-id": "2a61419f-14b0-4587-8438-0b057ad224d5",
  "request-type": "transaction",
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/2a61419f-14b0-4587-8438-0b057ad224d5.json"
  },
  "request": {
    "operations": [
      {
        "operation": "create-entity",
        "entity": "0cb710b2-1686-4e02-904b-510a01ce245f",
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "typehint": "person",
            "title": "Alice"
          }
        }
      },
      {
        "operation": "create-entity",
        "entity": "69091b6c-f087-45b4-9560-cbe90c127b8e",
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "typehint": "project",
            "title": "Example Project"
          }
        }
      },
      {
        "operation": "create-entity",
        "entity": "12cc0636-a5cc-49cd-b133-b3a37fa94c9f",
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "typehint": "link"
          },
          "tag:m1lattice.net,2026/aspect/link": {
            "from": "0cb710b2-1686-4e02-904b-510a01ce245f",
            "to": "69091b6c-f087-45b4-9560-cbe90c127b8e",
            "typehint": "member-of"
          }
        }
      }
    ]
  }
}
```

All three entities are created as one transaction.

---

# Read Requests

A read request retrieves committed entity state without changing it.

```json
{
  "request-id": "de780bc3-479b-4389-bf59-d92e5edcd4d3",
  "request-type": "read",
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/de780bc3-479b-4389-bf59-d92e5edcd4d3.json"
  },
  "request": {
    "reads": [
      {
        "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
        "aspects": [
          "tag:m1lattice.net,2026/aspect/basic"
        ]
      }
    ]
  }
}
```

## Read Body

```json
{
  "reads": [
    {
      "...": "read specification"
    }
  ]
}
```

### `reads`

```json
{
  "type": "array",
  "required": true,
  "minimum-items": 1
}
```

A batch of entity reads.

Each read is evaluated against committed state.

A read request must not observe speculative transaction planning, partial journal application, dirty memory, or partially applied recovery state.

---

## Reading Selected Aspects

```json
{
  "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
  "aspects": [
    "tag:m1lattice.net,2026/aspect/basic",
    "tag:example.net,2026/aspect/contact"
  ]
}
```

### Fields

#### `entity`

```json
{
  "type": "entity-id",
  "required": true
}
```

#### `aspects`

```json
{
  "type": "array",
  "required": true
}
```

Each entry is an aspect ID.

Subete returns one result for each requested aspect.

The result explicitly distinguishes a present aspect from an absent aspect.

---

## Reading All Aspects

```json
{
  "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
  "aspects": "*"
}
```

The string `"*"` requests all authoritative current aspects on the entity.

### Rules

* Only committed current aspects are returned.
* Aspect order is not semantically significant.
* Implementations should use a stable deterministic ordering in serialized responses.
* An entity with no aspects is still an existing entity if the datastore represents it as such.
* An absent entity is distinguished from an existing entity with no aspects.

---

## Batched Read Example

```json
{
  "request-id": "9661760d-b876-465f-af5d-a728381568f8",
  "request-type": "read",
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/9661760d-b876-465f-af5d-a728381568f8.json"
  },
  "request": {
    "reads": [
      {
        "entity": "0cb710b2-1686-4e02-904b-510a01ce245f",
        "aspects": "*"
      },
      {
        "entity": "69091b6c-f087-45b4-9560-cbe90c127b8e",
        "aspects": [
          "tag:m1lattice.net,2026/aspect/basic",
          "tag:example.net,2026/aspect/project-status"
        ]
      }
    ]
  }
}
```

The request is one FileTalk request containing two independent entity reads.

---

# Common CRUD Reply Envelope

Every CRUD/read reply uses a common outer shape.

```json
{
  "request-id": "7be711d6-5801-4e28-a300-81772985bcbb",
  "request-type": "transaction",
  "status": "success",
  "generation": 143,
  "response": {
    "...": "request-family-specific result"
  }
}
```

## Fields

### `request-id`

The request ID from the originating request.

### `request-type`

The originating request type.

### `status`

```json
{
  "type": "string",
  "const": "success | failure"
}
```

`"success"` means the request was accepted and completed according to its request-family semantics.

`"failure"` means the request was rejected or could not be completed.

A successful read may still contain not-found results.

Not-found is normally a result condition, not a failure of the whole read request.

### `generation`

```json
{
  "type": "integer",
  "required": true
}
```

For a successful transaction, this is the committed generation produced by the transaction.

For a successful read, this is the committed generation observed by the read.

For a failed transaction, this is the unchanged committed database generation at the time the failure response was produced.

### `response`

Contains the request-family-specific result.

---

# Transaction Success Reply

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
        "revision": 1
      }
    ],
    "operations": [
      {
        "index": 0,
        "operation": "create-entity",
        "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
        "status": "applied"
      }
    ]
  }
}
```

### Rules

* `journal-sequence` equals `generation`.
* The response reports the resulting revision of every created or changed entity that remains present after the transaction.
* A deleted entity has no resulting revision; its deletion is reported by the operation summary.
* The response may summarize each operation.
* The response does not need to repeat complete after-state entity data.
* The committed result remains valid even if reply delivery fails afterward.

---

# Transaction Failure Reply

```json
{
  "request-id": "7be711d6-5801-4e28-a300-81772985bcbb",
  "request-type": "transaction",
  "status": "failure",
  "generation": 142,
  "response": {
    "error": {
      "code": "entity-already-exists",
      "message": "The requested entity already exists.",
      "operation-index": 0,
      "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d"
    }
  }
}
```

### Rules

* A validation failure occurs before authoritative mutation begins.
* No operation in the failed transaction becomes committed.
* The generation does not advance.
* The error should identify the failing operation when applicable.
* A single primary error is sufficient for the initial protocol.
* Subete may later report multiple validation errors.

## Revision Conflict

A stale `expected-revision` is a transaction failure:

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

The reported generation is the unchanged committed database generation. No operation in the transaction is applied.

---

# Read Success Reply

## Selected Aspects

```json
{
  "request-id": "de780bc3-479b-4389-bf59-d92e5edcd4d3",
  "request-type": "read",
  "status": "success",
  "generation": 143,
  "response": {
    "reads": [
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
    ]
  }
}
```

## Entity Not Found

```json
{
  "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
  "status": "not-found"
}
```

## All Aspects

```json
{
  "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
  "status": "found",
  "revision": 12,
  "aspects": {
    "tag:m1lattice.net,2026/aspect/basic": {
      "typehint": "person",
      "title": "Lion Kimbro"
    },
    "tag:example.net,2026/aspect/contact": {
      "email": "lion@example.net"
    }
  }
}
```

### Not-Found Semantics

Not-found conditions are represented within successful read responses.

The request itself succeeded because Subete understood and completed the read.

Possible result conditions include:

* entity found;
* entity not found;
* requested aspect found;
* requested aspect not found.

Every found entity result includes the entity's current committed `revision`. An entity-not-found result has no revision.

A malformed entity ID, malformed aspect ID, invalid request structure, or unsupported request form is a request failure rather than a not-found result.

---

# Read Failure Reply

```json
{
  "request-id": "de780bc3-479b-4389-bf59-d92e5edcd4d3",
  "request-type": "read",
  "status": "failure",
  "generation": 143,
  "response": {
    "error": {
      "code": "invalid-read-request",
      "message": "The aspects field must be an array of aspect IDs or the string '*'.",
      "read-index": 0
    }
  }
}
```

If one batched read specification is structurally invalid, the complete request fails.

Valid reads in the same malformed request are not returned as partial success.

---

# Duplicate Request Behavior

CRUD and read requests use `request-id` to make repeated FileTalk delivery safe.

## Same Request ID, Same Request

When Subete receives a request whose `request-id` has already completed:

* it must not execute the logical request again;
* it should reproduce or redeliver the recorded outcome;
* a committed transaction must retain its original journal sequence and generation;
* a read may return its originally recorded result if Subete preserves that result;
* Subete must not silently reinterpret the duplicate as a new request against a newer generation.

For transactions, committed journal history is sufficient to establish that the transaction has already been applied.

## Same Request ID, Different Request

If the same `request-id` is presented with materially different request content, Subete must reject it with `request-id-conflict`.

The reply destination is part of the submitted request content. In the initial CRUD/read protocol, changing only the reply destination under the same `request-id` is still a conflict. A future protocol may define a separate reply-redelivery request.

## Duplicate While Processing

If a duplicate arrives while the original request is claimed or still being processed, Subete must not run both independently.

The duplicate may:

* remain pending;
* receive an in-progress reply;
* be associated with the original execution;
* be rejected as already in progress.

The exact operational policy may be defined separately, but at most one logical execution may occur.

---

# Validation Rules

The inbox file and reply destination are validated according to [filetalk-protocol.md](filetalk-protocol.md). This protocol additionally validates its request envelope, request identity, and duplicate consistency.

Before beginning transaction journaling or authoritative mutation, Subete also validates:

* the request type;
* the request-family-specific structure;
* every entity ID;
* every aspect ID;
* every operation name;
* operation field presence;
* that operations do not form any prohibited entity or aspect conflict;
* that every mutation of an existing entity supplies `expected-revision`;
* that all expected revisions supplied for the same entity agree;
* that each expected revision equals the entity's current committed revision;
* applicable aspect-specific rules.

Read requests are validated before execution.

Validation itself must not modify authoritative entity state.

---

# Initial Error Codes

The protocol may use error codes including:

```text
invalid-request
invalid-request-id
unsupported-request-type
invalid-reply-destination
request-id-conflict
request-already-in-progress

invalid-transaction
empty-transaction
unsupported-operation
invalid-operation
conflicting-entity-operations
duplicate-aspect-operation
entity-already-exists
entity-not-found
invalid-entity-id
invalid-aspect-id
invalid-aspect-value
missing-expected-revision
invalid-expected-revision
inconsistent-expected-revision
revision-conflict

invalid-read-request
invalid-read
invalid-aspects-selector

internal-error
recovery-required
service-not-ready
```

The code is intended for programmatic handling.

The message is intended for human understanding.

Additional structured fields may identify the entity, aspect, operation index, read index, or other relevant location.

The shared FileTalk protocol additionally defines `reply-delivery-failed`. A reply-delivery failure does not change the recorded logical outcome of a CRUD/read request.

---

# Protocol Boundaries

This protocol deliberately does not define:

* field-level aspect reads;
* nested aspect mutation;
* JSON Patch;
* implicit recursive deletion;
* link traversal requests;
* search requests;
* M1 document layering;
* transaction rollback requested after commit;
* multiple concurrent writers;
* Subete-minted entity IDs;
* arbitrary executable operations supplied by callers.

These capabilities may be defined separately if needed.

The central model remains:

* transactions submit complete intended mutations;
* reads retrieve complete committed aspects;
* each request carries its own reply destination;
* request IDs make retries safe;
* one transaction produces one committed generation.
