# Walking Example 1 — Create Two Entities and One Link

This example follows one transaction through Subete.

It shows:

1. two ordinary entities and one link entity created atomically;
2. the pending journal record;
3. transaction application;
4. the committed journal record;
5. the resulting entity files;
6. the transaction response;
7. a batched read;
8. a combined search;
9. generation advancement;
10. published status.

The example database begins at generation `41`.

After the transaction commits, it is at generation `42`.

---

# Scenario

We will create:

* a person named **Alice**;
* a project named **Moon Garden**;
* a link stating that Alice participates in Moon Garden.

## Entity IDs

```text
Alice:
11111111-1111-4111-8111-111111111111

Moon Garden:
22222222-2222-4222-8222-222222222222

Participation link:
33333333-3333-4333-8333-333333333333
```

## Database Identity

```text
aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa
```

## Starting Generation

```text
41
```

## Transaction Request ID

```text
44444444-4444-4444-8444-444444444444
```

---

# Initial Database State

Before the request, none of the three entities exists.

The relevant filesystem is:

```text
subete-data/
  identity.json
  configuration.json

  inbox/
  inbox-processing/
    claimed/
    completed/
    failed/

  entities/

  journal/
    pending/
    committed/
    checkpoints/

  status/
    status.json
    heartbeat.json
    metrics.json

  tmp/
```

The committed database generation is:

```text
41
```

---

# 1. Transaction Request

The client writes the following request into the FileTalk inbox.

## Filename

```text
inbox/create-alice-moon-garden.json
```

The filename has no protocol meaning.

## Contents

```json
{
  "request-id": "44444444-4444-4444-8444-444444444444",
  "request-type": "transaction",
  "reply": {
    "type": "file",
    "path": "D:/subete-example/replies/44444444-4444-4444-8444-444444444444.json"
  },
  "request": {
    "operations": [
      {
        "operation": "create-entity",
        "entity": "11111111-1111-4111-8111-111111111111",
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "typehint": "person",
            "name": "alice",
            "title": "Alice",
            "tags": [
              "person",
              "moon-garden"
            ]
          }
        }
      },
      {
        "operation": "create-entity",
        "entity": "22222222-2222-4222-8222-222222222222",
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "typehint": "project",
            "name": "moon-garden",
            "title": "Moon Garden",
            "tags": [
              "project",
              "moon-garden"
            ]
          }
        }
      },
      {
        "operation": "create-entity",
        "entity": "33333333-3333-4333-8333-333333333333",
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "typehint": "link",
            "name": "alice-participates-in-moon-garden",
            "title": "Alice participates in Moon Garden",
            "tags": [
              "link",
              "participation",
              "moon-garden"
            ]
          },
          "tag:m1lattice.net,2026/aspect/link": {
            "from": "11111111-1111-4111-8111-111111111111",
            "to": "22222222-2222-4222-8222-222222222222",
            "relationship": "participates-in"
          }
        }
      }
    ]
  }
}
```

All three creations belong to one transaction.

Either all three entities become committed, or none of them does.

---

# 2. Request Claimed

The service reads one complete JSON object and claims the request.

The file moves from:

```text
inbox/create-alice-moon-garden.json
```

to:

```text
inbox-processing/claimed/create-alice-moon-garden.json
```

No entity files have been created yet.

The committed generation remains:

```text
41
```

---

# 3. Validation and Planning

Subete validates that:

* the request ID is valid;
* the request type is `transaction`;
* the reply destination is permitted;
* all three entity IDs are valid;
* all three entities are absent;
* each entity is created exactly once;
* the link endpoints are valid entity IDs;
* the link refers to entities created in the same transaction;
* the operation set is internally consistent.

Subete then plans three entity transitions.

## Alice Transition

```json
{
  "before": null,
  "after": {
    "revision": 1,
    "aspects": {
      "tag:m1lattice.net,2026/aspect/basic": {
        "typehint": "person",
        "name": "alice",
        "title": "Alice",
        "tags": [
          "person",
          "moon-garden"
        ]
      }
    }
  }
}
```

## Moon Garden Transition

```json
{
  "before": null,
  "after": {
    "revision": 1,
    "aspects": {
      "tag:m1lattice.net,2026/aspect/basic": {
        "typehint": "project",
        "name": "moon-garden",
        "title": "Moon Garden",
        "tags": [
          "project",
          "moon-garden"
        ]
      }
    }
  }
}
```

## Link Transition

```json
{
  "before": null,
  "after": {
    "revision": 1,
    "aspects": {
      "tag:m1lattice.net,2026/aspect/basic": {
        "typehint": "link",
        "name": "alice-participates-in-moon-garden",
        "title": "Alice participates in Moon Garden",
        "tags": [
          "link",
          "participation",
          "moon-garden"
        ]
      },
      "tag:m1lattice.net,2026/aspect/link": {
        "from": "11111111-1111-4111-8111-111111111111",
        "to": "22222222-2222-4222-8222-222222222222",
        "relationship": "participates-in"
      }
    }
  }
}
```

The transaction is assigned journal sequence:

```text
42
```

The generation has not yet advanced.

---

# 4. Journal Write Started

Subete begins writing the planned journal entry beneath `tmp/`.

Example temporary path:

```text
tmp/00000000000000000042__44444444-4444-4444-8444-444444444444.json.writing
```

This temporary file does not authorize entity mutation.

If Subete stops here, the temporary file may be discarded and the claimed request may be planned again.

---

# 5. Pending Journal Record

After the journal file is completely written, flushed, and closed, it is placed at:

```text
journal/pending/00000000000000000042__44444444-4444-4444-8444-444444444444.json
```

## Complete Pending Journal File

```json
{
  "journal-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "sequence": 42,
  "journaled": "2026-07-23T23:40:00Z",
  "request-id": "44444444-4444-4444-8444-444444444444",
  "transaction-request": {
    "request-id": "44444444-4444-4444-8444-444444444444",
    "request-type": "transaction",
    "reply": {
      "type": "file",
      "path": "D:/subete-example/replies/44444444-4444-4444-8444-444444444444.json"
    },
    "request": {
      "operations": [
        {
          "operation": "create-entity",
          "entity": "11111111-1111-4111-8111-111111111111",
          "aspects": {
            "tag:m1lattice.net,2026/aspect/basic": {
              "typehint": "person",
              "name": "alice",
              "title": "Alice",
              "tags": [
                "person",
                "moon-garden"
              ]
            }
          }
        },
        {
          "operation": "create-entity",
          "entity": "22222222-2222-4222-8222-222222222222",
          "aspects": {
            "tag:m1lattice.net,2026/aspect/basic": {
              "typehint": "project",
              "name": "moon-garden",
              "title": "Moon Garden",
              "tags": [
                "project",
                "moon-garden"
              ]
            }
          }
        },
        {
          "operation": "create-entity",
          "entity": "33333333-3333-4333-8333-333333333333",
          "aspects": {
            "tag:m1lattice.net,2026/aspect/basic": {
              "typehint": "link",
              "name": "alice-participates-in-moon-garden",
              "title": "Alice participates in Moon Garden",
              "tags": [
                "link",
                "participation",
                "moon-garden"
              ]
            },
            "tag:m1lattice.net,2026/aspect/link": {
              "from": "11111111-1111-4111-8111-111111111111",
              "to": "22222222-2222-4222-8222-222222222222",
              "relationship": "participates-in"
            }
          }
        }
      ]
    }
  },
  "entities": {
    "11111111-1111-4111-8111-111111111111": {
      "before": null,
      "after": {
        "revision": 1,
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "typehint": "person",
            "name": "alice",
            "title": "Alice",
            "tags": [
              "person",
              "moon-garden"
            ]
          }
        }
      }
    },
    "22222222-2222-4222-8222-222222222222": {
      "before": null,
      "after": {
        "revision": 1,
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "typehint": "project",
            "name": "moon-garden",
            "title": "Moon Garden",
            "tags": [
              "project",
              "moon-garden"
            ]
          }
        }
      }
    },
    "33333333-3333-4333-8333-333333333333": {
      "before": null,
      "after": {
        "revision": 1,
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "typehint": "link",
            "name": "alice-participates-in-moon-garden",
            "title": "Alice participates in Moon Garden",
            "tags": [
              "link",
              "participation",
              "moon-garden"
            ]
          },
          "tag:m1lattice.net,2026/aspect/link": {
            "from": "11111111-1111-4111-8111-111111111111",
            "to": "22222222-2222-4222-8222-222222222222",
            "relationship": "participates-in"
          }
        }
      }
    }
  }
}
```

At this point:

* the journal sequence `42` is reserved;
* the transaction is a recovery obligation;
* the generation is still `41`;
* no response may yet claim that the transaction committed.

---

# 6. Transaction Application

Subete applies the journaled after-states.

It creates:

```text
entities/11111111-1111-4111-8111-111111111111.json
entities/22222222-2222-4222-8222-222222222222.json
entities/33333333-3333-4333-8333-333333333333.json
```

The transaction also has the following link-cache consequences:

- add link `33333333-3333-4333-8333-333333333333` to the outgoing entry for Alice;
- add link `33333333-3333-4333-8333-333333333333` to the incoming entry for Moon Garden;
- advance the complete link cache to generation `42`.

Subete writes or replaces the affected cache entry files:

```text
link-cache/outgoing/11111111-1111-4111-8111-111111111111.json
link-cache/incoming/22222222-2222-4222-8222-222222222222.json
```

After all affected cache entries are complete, Subete writes:

```text
link-cache/generation.json
```

declaring that the complete cache represents generation `42`.

Until the authoritative entities and all required link-cache updates are complete, ordinary reads, searches, and attached-link lookups do not observe generation `42`.

---

# 7. Entity Files After Application

## Alice

### Filename

```text
entities/11111111-1111-4111-8111-111111111111.json
```

### Contents

```json
{
  "entity": "11111111-1111-4111-8111-111111111111",
  "revision": 1,
  "aspects": {
    "tag:m1lattice.net,2026/aspect/basic": {
      "typehint": "person",
      "name": "alice",
      "title": "Alice",
      "tags": [
        "person",
        "moon-garden"
      ]
    }
  }
}
```

## Moon Garden

### Filename

```text
entities/22222222-2222-4222-8222-222222222222.json
```

### Contents

```json
{
  "entity": "22222222-2222-4222-8222-222222222222",
  "revision": 1,
  "aspects": {
    "tag:m1lattice.net,2026/aspect/basic": {
      "typehint": "project",
      "name": "moon-garden",
      "title": "Moon Garden",
      "tags": [
        "project",
        "moon-garden"
      ]
    }
  }
}
```

## Participation Link

### Filename

```text
entities/33333333-3333-4333-8333-333333333333.json
```

### Contents

```json
{
  "entity": "33333333-3333-4333-8333-333333333333",
  "revision": 1,
  "aspects": {
    "tag:m1lattice.net,2026/aspect/basic": {
      "typehint": "link",
      "name": "alice-participates-in-moon-garden",
      "title": "Alice participates in Moon Garden",
      "tags": [
        "link",
        "participation",
        "moon-garden"
      ]
    },
    "tag:m1lattice.net,2026/aspect/link": {
      "from": "11111111-1111-4111-8111-111111111111",
      "to": "22222222-2222-4222-8222-222222222222",
      "relationship": "participates-in"
    }
  }
}
```

All three logical entities now match the journaled after-state.

The journal has not yet been committed.

The published committed generation remains `41`.

---

# 8. Link Cache Preparation

The authoritative link entity causes one outgoing cache membership and one incoming cache membership.

The cache remains derived.

The authoritative link entity remains the sole authority for the relationship and its endpoints.

## Cache Layout

```text
link-cache/
  generation.json

  outgoing/
    11111111-1111-4111-8111-111111111111.json

  incoming/
    22222222-2222-4222-8222-222222222222.json
```

## Alice Outgoing Entry

### Filename

```text
link-cache/outgoing/11111111-1111-4111-8111-111111111111.json
```

### Contents

```json
{
  "link-cache-entry-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 42,
  "entity": "11111111-1111-4111-8111-111111111111",
  "direction": "outgoing",
  "links": [
    "33333333-3333-4333-8333-333333333333"
  ]
}
```

This entry means that link entity:

```text
33333333-3333-4333-8333-333333333333
```

has Alice as its authoritative `from` endpoint.

## Moon Garden Incoming Entry

### Filename

```text
link-cache/incoming/22222222-2222-4222-8222-222222222222.json
```

### Contents

```json
{
  "link-cache-entry-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 42,
  "entity": "22222222-2222-4222-8222-222222222222",
  "direction": "incoming",
  "links": [
    "33333333-3333-4333-8333-333333333333"
  ]
}
```

This entry means that link entity:

```text
33333333-3333-4333-8333-333333333333
```

has Moon Garden as its authoritative `to` endpoint.

## Cache Generation

### Filename

```text
link-cache/generation.json
```

### Contents

```json
{
  "link-cache-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 41,
  "updated": "2026-07-23T23:40:01Z",
  "state": "updating",
  "target-generation": 42
}
```

This file declares that cache-entry changes have been prepared for target generation `42`, while published cache generation remains `41`.

The cache must not be treated as current until:

* both affected entry files are complete;
* the journal is committed at generation `42`;
* `generation.json` reports `state` as `current` at generation `42`;
* the cache generation equals the committed database generation.

At this moment, authoritative mutation and cache mutation are complete, but the journal entry has not yet moved to `committed/`.

The published committed database generation therefore remains `41`.

---

# 9. Committed Journal Record

Subete moves the journal file from:

```text
journal/pending/00000000000000000042__44444444-4444-4444-8444-444444444444.json
```

to:

```text
journal/committed/00000000000000000042__44444444-4444-4444-8444-444444444444.json
```

The file contents do not change.

The committed journal record is byte-for-byte the same JSON document shown in the pending journal section.

Its directory location now records that transaction sequence `42` is committed.

Before commitment, Subete confirms that:

- all three authoritative entity after-states are established;
- the outgoing cache entry contains the link ID;
- the incoming cache entry contains the link ID;
- `link-cache/generation.json` reports generation `41`, state `updating`, and target generation `42`.

The journal may then move to `committed/`.

The database generation advances:

```text
41 → 42
```

## Cache-Current Publication

After journal commitment, Subete publishes the prepared cache as current:

```json
{
  "link-cache-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 42,
  "updated": "2026-07-23T23:40:02Z",
  "state": "current"
}
```

Only now does the global cache record declare generation `42` current.

---

# 10. Transaction Response

Subete writes the transaction response to:

```text
D:/subete-example/replies/44444444-4444-4444-8444-444444444444.json
```

## Response

```json
{
  "request-id": "44444444-4444-4444-8444-444444444444",
  "request-type": "transaction",
  "status": "success",
  "generation": 42,
  "response": {
    "journal-sequence": 42,
    "entities": [
      {
        "entity": "11111111-1111-4111-8111-111111111111",
        "revision": 1
      },
      {
        "entity": "22222222-2222-4222-8222-222222222222",
        "revision": 1
      },
      {
        "entity": "33333333-3333-4333-8333-333333333333",
        "revision": 1
      }
    ]
  }
}
```

The transaction remains committed even if response delivery later proves unsuccessful.

---

# 11. Completed Request

After response delivery, the claimed request moves from:

```text
inbox-processing/claimed/create-alice-moon-garden.json
```

to:

```text
inbox-processing/completed/create-alice-moon-garden.json
```

This movement does not alter the committed generation.

---

# 12. Batched Read

The client requests Alice and the participation link in one read request.

## Read Request Filename

```text
inbox/read-alice-and-link.json
```

## Read Request

```json
{
  "request-id": "55555555-5555-4555-8555-555555555555",
  "request-type": "read",
  "reply": {
    "type": "file",
    "path": "D:/subete-example/replies/55555555-5555-4555-8555-555555555555.json"
  },
  "request": {
    "reads": [
      {
        "entity": "11111111-1111-4111-8111-111111111111",
        "aspects": "*"
      },
      {
        "entity": "33333333-3333-4333-8333-333333333333",
        "aspects": [
          "tag:m1lattice.net,2026/aspect/link"
        ]
      }
    ]
  }
}
```

Both reads observe the same committed generation.

## Read Response

```json
{
  "request-id": "55555555-5555-4555-8555-555555555555",
  "request-type": "read",
  "status": "success",
  "generation": 42,
  "response": {
    "reads": [
      {
        "entity": "11111111-1111-4111-8111-111111111111",
        "status": "found",
        "revision": 1,
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "typehint": "person",
            "name": "alice",
            "title": "Alice",
            "tags": [
              "person",
              "moon-garden"
            ]
          }
        }
      },
      {
        "entity": "33333333-3333-4333-8333-333333333333",
        "status": "found",
        "revision": 1,
        "aspects": [
          {
            "aspect": "tag:m1lattice.net,2026/aspect/link",
            "status": "found",
            "value": {
              "from": "11111111-1111-4111-8111-111111111111",
              "to": "22222222-2222-4222-8222-222222222222",
              "relationship": "participates-in"
            }
          }
        ]
      }
    ]
  }
}
```

The read does not advance the generation.

The generation remains:

```text
42
```

---

# 13. Combined Search

The client searches for an entity that satisfies all of the following:

* has the basic aspect;
* has the link aspect;
* has typehint `link`;
* has both tags `participation` and `moon-garden`;
* has a name containing `alice`.

All predicates within this search are combined with logical AND.

## Search Request Filename

```text
inbox/search-alice-participation-link.json
```

## Search Request

```json
{
  "request-id": "66666666-6666-4666-8666-666666666666",
  "request-type": "search",
  "reply": {
    "type": "file",
    "path": "D:/subete-example/replies/66666666-6666-4666-8666-666666666666.json"
  },
  "request": {
    "searches": [
      {
        "has-aspects": [
          "tag:m1lattice.net,2026/aspect/basic",
          "tag:m1lattice.net,2026/aspect/link"
        ],
        "typehint": "link",
        "tags": [
          "participation",
          "moon-garden"
        ],
        "name-contains": "alice"
      }
    ]
  }
}
```

## Search Evaluation

Alice does not match because she lacks the link aspect and does not have typehint `link`.

Moon Garden does not match because it lacks the link aspect and does not have typehint `link`.

The participation link matches every predicate.

## Search Response

```json
{
  "request-id": "66666666-6666-4666-8666-666666666666",
  "request-type": "search",
  "status": "success",
  "generation": 42,
  "response": {
    "searches": [
      {
        "index": 0,
        "entities": [
          "33333333-3333-4333-8333-333333333333"
        ]
      }
    ]
  }
}
```

Search results contain entity IDs only.

The search does not advance the generation.

---

# 14. Status Output

After the transaction, read, and search have completed, Subete publishes operational status.

## Filename

```text
status/status.json
```

## Example Status

```json
{
  "status-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "state": "ready",
  "generation": 42,
  "started": "2026-07-23T23:30:00Z",
  "updated": "2026-07-23T23:40:03Z",
  "last-commit": {
    "sequence": 42,
    "timestamp": "2026-07-23T23:40:01Z",
    "request-id": "44444444-4444-4444-8444-444444444444"
  },
  "counts": {
    "entities": 3,
    "inbox": 0,
    "claimed": 0,
    "completed": 3,
    "failed": 0,
    "pending-journal": 0,
    "committed-journal": 42
  },
  "recovery": {
    "active": false
  },
  "link-cache": {
    "state": "current",
    "generation": 42
  }
}
```

The value:

```json
{
  "generation": 42
}
```

reports the latest committed generation.

The read and search requests did not change it.

---

# Final Filesystem State

The relevant files now include:

```text
subete-data/
  entities/
    11111111-1111-4111-8111-111111111111.json
    22222222-2222-4222-8222-222222222222.json
    33333333-3333-4333-8333-333333333333.json

  inbox/

  inbox-processing/
    claimed/
    completed/
      create-alice-moon-garden.json
      read-alice-and-link.json
      search-alice-participation-link.json
    failed/

  journal/
    pending/
    committed/
      00000000000000000042__44444444-4444-4444-8444-444444444444.json

  link-cache/
    generation.json
    outgoing/
      11111111-1111-4111-8111-111111111111.json
    incoming/
      22222222-2222-4222-8222-222222222222.json

  status/
    status.json
    heartbeat.json
    metrics.json
```

The reply directory contains:

```text
D:/subete-example/replies/
  44444444-4444-4444-8444-444444444444.json
  55555555-5555-4555-8555-555555555555.json
  66666666-6666-4666-8666-666666666666.json
```

---

# Generation Summary

| Event                                    | Committed generation |
| ---------------------------------------- | -------------------: |
| Before transaction                       |                   41 |
| Request discovered                       |                   41 |
| Request claimed                          |                   41 |
| Transaction planned                      |                   41 |
| Pending journal written with sequence 42 |                   41 |
| Entity mutation in progress              |                   41 |
| Entity mutation complete                 |                   41 |
| Link-cache entries written               |                   41 |
| Link-cache generation prepared for 42    |                   41 |
| Journal moved to `committed/`            |                   42 |
| Link-cache published current for 42      |                   42 |
| Transaction response delivered           |                   42 |
| Batched read completed                   |                   42 |
| Combined search completed                |                   42 |

---

# What This Example Demonstrates

* Three entities can be created atomically in one transaction.
* A link is an entity with a link aspect.
* The journal records complete before-states and after-states.
* The pending and committed journal files contain the same immutable document.
* Directory placement distinguishes pending from committed.
* Entity files are not created before the journal becomes complete.
* Generation advances only after authoritative mutation and journal commitment.
* Every created entity begins at revision `1`.
* A batched read observes one committed generation.
* Search predicates within one search are combined with AND.
* Reads and searches do not advance generation.
* Status reports the resulting committed generation and operational state.
* Link creation updates both the outgoing index of the `from` endpoint and the incoming index of the `to` endpoint.
* Link-cache entry files contain sorted link entity IDs only.
* `link-cache/generation.json` declares when the complete cache represents the committed world.
* Link-cache entries are prepared before journal commitment, while cache-current publication occurs afterward at the committed generation.
* The authoritative link entity, not the cache, remains the sole authority for the relationship.
