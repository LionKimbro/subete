# Walking Example 2 — Crash During Multi-Entity Transaction

This example follows a transaction that is interrupted after only some authoritative entity files have been changed.

It shows how startup recovery:

1. discovers the completed pending journal entry;
2. compares each affected entity with its journaled before-state and after-state;
3. recognizes work already completed;
4. finishes the remaining mutations;
5. reconciles the link cache;
6. commits the journal record;
7. advances the database to one coherent generation.

The database begins at committed generation `42`.

The interrupted transaction has journal sequence `43`.

---

# Scenario

The database already contains:

* Alice;
* Moon Garden;
* a link stating that Alice participates in Moon Garden.

The transaction will:

* rename Alice to **Alice Morgan**;
* rename Moon Garden to **Lunar Garden**;
* change the link title and relationship from `participates-in` to `leads`;
* keep the same link endpoints.

The process crashes after Alice and Moon Garden have been changed, but before the link entity has been changed and before the journal has been committed.

---

# Database Identity

```text
aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa
```

# Starting Generation

```text
42
```

# Transaction Request ID

```text
77777777-7777-4777-8777-777777777777
```

# Journal Sequence

```text
43
```

# Entities

```text
Alice:
11111111-1111-4111-8111-111111111111

Moon Garden:
22222222-2222-4222-8222-222222222222

Participation link:
33333333-3333-4333-8333-333333333333
```

---

# 1. Authoritative State Before the Transaction

At committed generation `42`, the entity files are as follows.

## Alice Before-State

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
    "tag:m1lattice.net,2026:aspect/basic": {
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

## Moon Garden Before-State

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
    "tag:m1lattice.net,2026:aspect/basic": {
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

## Link Before-State

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
    "tag:m1lattice.net,2026:aspect/basic": {
      "typehint": "link",
      "name": "alice-participates-in-moon-garden",
      "title": "Alice participates in Moon Garden",
      "tags": [
        "link",
        "participation",
        "moon-garden"
      ]
    },
    "tag:m1lattice.net,2026:aspect/link": {
      "from": "11111111-1111-4111-8111-111111111111",
      "to": "22222222-2222-4222-8222-222222222222",
      "relationship": "participates-in"
    }
  }
}
```

---

# 2. Link Cache Before the Transaction

The cache represents generation `42`.

## `link-cache/generation.json`

```json
{
  "link-cache-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 42,
  "updated": "2026-07-23T23:40:01Z",
  "state": "current"
}
```

## Alice Outgoing Entry

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

## Moon Garden Incoming Entry

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

---

# 3. Transaction Request

The client writes:

```text
inbox/rename-moon-garden-and-change-link.json
```

## Request

```json
{
  "request-id": "77777777-7777-4777-8777-777777777777",
  "request-type": "transaction",
  "reply": {
    "type": "file",
    "path": "D:/subete-example/replies/77777777-7777-4777-8777-777777777777.json"
  },
  "request": {
    "operations": [
      {
        "operation": "set-aspect",
        "entity": "11111111-1111-4111-8111-111111111111",
        "expected-revision": 1,
        "aspect": "tag:m1lattice.net,2026:aspect/basic",
        "value": {
          "typehint": "person",
          "name": "alice-morgan",
          "title": "Alice Morgan",
          "tags": [
            "person",
            "lunar-garden"
          ]
        }
      },
      {
        "operation": "set-aspect",
        "entity": "22222222-2222-4222-8222-222222222222",
        "expected-revision": 1,
        "aspect": "tag:m1lattice.net,2026:aspect/basic",
        "value": {
          "typehint": "project",
          "name": "lunar-garden",
          "title": "Lunar Garden",
          "tags": [
            "project",
            "lunar-garden"
          ]
        }
      },
      {
        "operation": "set-aspect",
        "entity": "33333333-3333-4333-8333-333333333333",
        "expected-revision": 1,
        "aspect": "tag:m1lattice.net,2026:aspect/basic",
        "value": {
          "typehint": "link",
          "name": "alice-leads-lunar-garden",
          "title": "Alice leads Lunar Garden",
          "tags": [
            "link",
            "leadership",
            "lunar-garden"
          ]
        }
      },
      {
        "operation": "set-aspect",
        "entity": "33333333-3333-4333-8333-333333333333",
        "expected-revision": 1,
        "aspect": "tag:m1lattice.net,2026:aspect/link",
        "value": {
          "from": "11111111-1111-4111-8111-111111111111",
          "to": "22222222-2222-4222-8222-222222222222",
          "relationship": "leads"
        }
      }
    ]
  }
}
```

The two operations targeting the link entity use the same expected revision and change different aspects.

The link entity advances only once, from revision `1` to revision `2`.

---

# 4. Transaction Planned

Subete validates the request and computes the complete before-state and after-state for each entity.

## Alice Planned Transition

```json
{
  "before": {
    "revision": 1,
    "aspects": {
      "tag:m1lattice.net,2026:aspect/basic": {
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
  "after": {
    "revision": 2,
    "aspects": {
      "tag:m1lattice.net,2026:aspect/basic": {
        "typehint": "person",
        "name": "alice-morgan",
        "title": "Alice Morgan",
        "tags": [
          "person",
          "lunar-garden"
        ]
      }
    }
  }
}
```

## Project Planned Transition

```json
{
  "before": {
    "revision": 1,
    "aspects": {
      "tag:m1lattice.net,2026:aspect/basic": {
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
  "after": {
    "revision": 2,
    "aspects": {
      "tag:m1lattice.net,2026:aspect/basic": {
        "typehint": "project",
        "name": "lunar-garden",
        "title": "Lunar Garden",
        "tags": [
          "project",
          "lunar-garden"
        ]
      }
    }
  }
}
```

## Link Planned Transition

```json
{
  "before": {
    "revision": 1,
    "aspects": {
      "tag:m1lattice.net,2026:aspect/basic": {
        "typehint": "link",
        "name": "alice-participates-in-moon-garden",
        "title": "Alice participates in Moon Garden",
        "tags": [
          "link",
          "participation",
          "moon-garden"
        ]
      },
      "tag:m1lattice.net,2026:aspect/link": {
        "from": "11111111-1111-4111-8111-111111111111",
        "to": "22222222-2222-4222-8222-222222222222",
        "relationship": "participates-in"
      }
    }
  },
  "after": {
    "revision": 2,
    "aspects": {
      "tag:m1lattice.net,2026:aspect/basic": {
        "typehint": "link",
        "name": "alice-leads-lunar-garden",
        "title": "Alice leads Lunar Garden",
        "tags": [
          "link",
          "leadership",
          "lunar-garden"
        ]
      },
      "tag:m1lattice.net,2026:aspect/link": {
        "from": "11111111-1111-4111-8111-111111111111",
        "to": "22222222-2222-4222-8222-222222222222",
        "relationship": "leads"
      }
    }
  }
}
```

Because the link endpoints do not change, its outgoing and incoming cache memberships do not change.

The cache must still have its global `updating` record and prepared target generation `43` before the transaction is committed. It is not current at `43` yet.

---

# 5. Complete Pending Journal Entry

Subete writes and completes:

```text
journal/pending/00000000000000000043__77777777-7777-4777-8777-777777777777.json
```

## Journal Record

```json
{
  "journal-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "sequence": 43,
  "journaled": "2026-07-24T00:10:00Z",
  "request-id": "77777777-7777-4777-8777-777777777777",
  "transaction-request": {
    "request-id": "77777777-7777-4777-8777-777777777777",
    "request-type": "transaction",
    "reply": {
      "type": "file",
      "path": "D:/subete-example/replies/77777777-7777-4777-8777-777777777777.json"
    },
    "request": {
      "operations": [
        {
          "operation": "set-aspect",
          "entity": "11111111-1111-4111-8111-111111111111",
          "expected-revision": 1,
          "aspect": "tag:m1lattice.net,2026:aspect/basic",
          "value": {
            "typehint": "person",
            "name": "alice-morgan",
            "title": "Alice Morgan",
            "tags": [
              "person",
              "lunar-garden"
            ]
          }
        },
        {
          "operation": "set-aspect",
          "entity": "22222222-2222-4222-8222-222222222222",
          "expected-revision": 1,
          "aspect": "tag:m1lattice.net,2026:aspect/basic",
          "value": {
            "typehint": "project",
            "name": "lunar-garden",
            "title": "Lunar Garden",
            "tags": [
              "project",
              "lunar-garden"
            ]
          }
        },
        {
          "operation": "set-aspect",
          "entity": "33333333-3333-4333-8333-333333333333",
          "expected-revision": 1,
          "aspect": "tag:m1lattice.net,2026:aspect/basic",
          "value": {
            "typehint": "link",
            "name": "alice-leads-lunar-garden",
            "title": "Alice leads Lunar Garden",
            "tags": [
              "link",
              "leadership",
              "lunar-garden"
            ]
          }
        },
        {
          "operation": "set-aspect",
          "entity": "33333333-3333-4333-8333-333333333333",
          "expected-revision": 1,
          "aspect": "tag:m1lattice.net,2026:aspect/link",
          "value": {
            "from": "11111111-1111-4111-8111-111111111111",
            "to": "22222222-2222-4222-8222-222222222222",
            "relationship": "leads"
          }
        }
      ]
    }
  },
  "entities": {
    "11111111-1111-4111-8111-111111111111": {
      "before": {
        "revision": 1,
        "aspects": {
          "tag:m1lattice.net,2026:aspect/basic": {
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
      "after": {
        "revision": 2,
        "aspects": {
          "tag:m1lattice.net,2026:aspect/basic": {
            "typehint": "person",
            "name": "alice-morgan",
            "title": "Alice Morgan",
            "tags": [
              "person",
              "lunar-garden"
            ]
          }
        }
      }
    },
    "22222222-2222-4222-8222-222222222222": {
      "before": {
        "revision": 1,
        "aspects": {
          "tag:m1lattice.net,2026:aspect/basic": {
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
      "after": {
        "revision": 2,
        "aspects": {
          "tag:m1lattice.net,2026:aspect/basic": {
            "typehint": "project",
            "name": "lunar-garden",
            "title": "Lunar Garden",
            "tags": [
              "project",
              "lunar-garden"
            ]
          }
        }
      }
    },
    "33333333-3333-4333-8333-333333333333": {
      "before": {
        "revision": 1,
        "aspects": {
          "tag:m1lattice.net,2026:aspect/basic": {
            "typehint": "link",
            "name": "alice-participates-in-moon-garden",
            "title": "Alice participates in Moon Garden",
            "tags": [
              "link",
              "participation",
              "moon-garden"
            ]
          },
          "tag:m1lattice.net,2026:aspect/link": {
            "from": "11111111-1111-4111-8111-111111111111",
            "to": "22222222-2222-4222-8222-222222222222",
            "relationship": "participates-in"
          }
        }
      },
      "after": {
        "revision": 2,
        "aspects": {
          "tag:m1lattice.net,2026:aspect/basic": {
            "typehint": "link",
            "name": "alice-leads-lunar-garden",
            "title": "Alice leads Lunar Garden",
            "tags": [
              "link",
              "leadership",
              "lunar-garden"
            ]
          },
          "tag:m1lattice.net,2026:aspect/link": {
            "from": "11111111-1111-4111-8111-111111111111",
            "to": "22222222-2222-4222-8222-222222222222",
            "relationship": "leads"
          }
        }
      }
    }
  }
}
```

The journal entry is now complete and immutable.

Subete is obligated to finish the transaction.

The committed database generation remains `42`.

---

# 6. Partial Transaction Application

Subete begins applying the journaled after-states.

It successfully replaces the Alice entity file.

It then successfully replaces the project entity file.

Before it replaces the link entity or advances the link cache, the process terminates unexpectedly.

---

# 7. Filesystem at the Moment of the Crash

The disk now contains a mixed physical state.

## Alice Matches After-State

```json
{
  "entity": "11111111-1111-4111-8111-111111111111",
  "revision": 2,
  "aspects": {
    "tag:m1lattice.net,2026:aspect/basic": {
      "typehint": "person",
      "name": "alice-morgan",
      "title": "Alice Morgan",
      "tags": [
        "person",
        "lunar-garden"
      ]
    }
  }
}
```

## Project Matches After-State

```json
{
  "entity": "22222222-2222-4222-8222-222222222222",
  "revision": 2,
  "aspects": {
    "tag:m1lattice.net,2026:aspect/basic": {
      "typehint": "project",
      "name": "lunar-garden",
      "title": "Lunar Garden",
      "tags": [
        "project",
        "lunar-garden"
      ]
    }
  }
}
```

## Link Still Matches Before-State

```json
{
  "entity": "33333333-3333-4333-8333-333333333333",
  "revision": 1,
  "aspects": {
    "tag:m1lattice.net,2026:aspect/basic": {
      "typehint": "link",
      "name": "alice-participates-in-moon-garden",
      "title": "Alice participates in Moon Garden",
      "tags": [
        "link",
        "participation",
        "moon-garden"
      ]
    },
    "tag:m1lattice.net,2026:aspect/link": {
      "from": "11111111-1111-4111-8111-111111111111",
      "to": "22222222-2222-4222-8222-222222222222",
      "relationship": "participates-in"
    }
  }
}
```

## Journal Still Pending

```text
journal/pending/00000000000000000043__77777777-7777-4777-8777-777777777777.json
```

## No Committed Sequence 43

```text
journal/committed/
```

contains no sequence `43` record.

## Link Cache Still Represents Generation 42

```json
{
  "link-cache-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 42,
  "updated": "2026-07-23T23:40:01Z",
  "state": "current"
}
```

The cache memberships themselves remain correct because the link endpoints have not changed.

Its generation has not advanced.

---

# 8. Meaning of the Crash State

The physical entity files are inconsistent with one another:

| Entity       | Physical state |
| ------------ | -------------- |
| Alice        | After-state    |
| Lunar Garden | After-state    |
| Link         | Before-state   |

This mixture is not a valid committed Subete generation.

Subete must not:

* expose it to reads or searches;
* treat Alice and the project as independently committed;
* roll them back merely because the link was not changed;
* abandon the transaction;
* begin processing a later transaction.

The completed pending journal entry defines the required coherent outcome.

---

# 9. Service Restart

The operator starts:

```text
subete service
```

The service:

1. acquires exclusive writer authority;
2. reads database identity;
3. publishes state `starting`;
4. inspects the journal;
5. finds pending sequence `43`;
6. enters recovery before accepting ordinary requests.

Example recovery status:

```json
{
  "status-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "state": "recovering",
  "generation": 42,
  "started": "2026-07-24T00:12:00Z",
  "updated": "2026-07-24T00:12:01Z",
  "recovery": {
    "active": true,
    "journal-sequence": 43,
    "phase": "comparing"
  },
  "link-cache": {
    "state": "stale",
    "generation": 42
  }
}
```

The database generation remains `42` during recovery.

---

# 10. Journal Validation

Recovery reads:

```text
journal/pending/00000000000000000043__77777777-7777-4777-8777-777777777777.json
```

It validates that:

* the file is complete JSON;
* the database ID matches `identity.json`;
* the sequence is `43`;
* sequence `43` is the next expected generation after `42`;
* the request ID agrees with the filename;
* every affected entity has complete before-state and after-state data;
* the journal entry is internally consistent.

The journal record is sufficient to complete recovery.

The original in-memory transaction plan is not needed.

---

# 11. Comparing Current Entities with Journal States

Recovery reads each current logical entity and compares it with the journal.

## Alice Comparison

Current state:

```text
matches journaled after-state
```

Recovery action:

```text
none
```

Alice is already correctly applied.

Recovery does not increment her revision again.

She remains at revision `2`.

## Project Comparison

Current state:

```text
matches journaled after-state
```

Recovery action:

```text
none
```

The project is already correctly applied.

Recovery does not increment its revision again.

It remains at revision `2`.

## Link Comparison

Current state:

```text
matches journaled before-state
```

Recovery action:

```text
apply journaled after-state
```

The link still requires mutation.

---

# 12. Recovery Applies the Missing Link After-State

Recovery replaces:

```text
entities/33333333-3333-4333-8333-333333333333.json
```

with:

```json
{
  "entity": "33333333-3333-4333-8333-333333333333",
  "revision": 2,
  "aspects": {
    "tag:m1lattice.net,2026:aspect/basic": {
      "typehint": "link",
      "name": "alice-leads-lunar-garden",
      "title": "Alice leads Lunar Garden",
      "tags": [
        "link",
        "leadership",
        "lunar-garden"
      ]
    },
    "tag:m1lattice.net,2026:aspect/link": {
      "from": "11111111-1111-4111-8111-111111111111",
      "to": "22222222-2222-4222-8222-222222222222",
      "relationship": "leads"
    }
  }
}
```

The link now matches its journaled after-state.

---

# 13. Recovery Reconciles the Link Cache

The link’s endpoints did not change.

Therefore, the required memberships remain:

```text
Alice outgoing:
33333333-3333-4333-8333-333333333333

Lunar Garden incoming:
33333333-3333-4333-8333-333333333333
```

Recovery verifies both files.

## Alice Outgoing Entry

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

## Lunar Garden Incoming Entry

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

The memberships are already correct.

Recovery may leave their entry-level generation values unchanged because those particular memberships were last changed at generation `42`.

Recovery then writes the global cache record as prepared but not current.

## Updated `link-cache/generation.json`

```json
{
  "link-cache-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 42,
  "updated": "2026-07-24T00:12:02Z",
  "state": "updating",
  "target-generation": 43
}
```

This declares that cache-entry changes have been checked and prepared for target generation `43`, while published cache generation remains `42`.

The committed database generation is still `42` until journal commitment.

---

# 14. Recovery Verifies Complete After-State

Recovery reads all affected logical entities again.

It confirms:

```text
Alice:
matches after-state at revision 2

Lunar Garden:
matches after-state at revision 2

Link:
matches after-state at revision 2
```

It also confirms:

```text
link cache memberships:
correct

link cache target generation:
43

pending journal:
complete and valid
```

The entire intended transaction state is now physically established.

---

# 15. Journal Commitment

Recovery moves:

```text
journal/pending/00000000000000000043__77777777-7777-4777-8777-777777777777.json
```

to:

```text
journal/committed/00000000000000000043__77777777-7777-4777-8777-777777777777.json
```

The journal contents do not change.

Recovery then publishes root `generation.json`:

```json
{
  "generation-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 43,
  "journal-sequence": 43,
  "updated": "2026-07-24T00:12:03Z"
}
```

The recognized database generation is now:

```text
42 → 43
```

The transaction is now committed.

## Cache-Current Publication

Recovery now publishes the cache as current for the committed generation:

```json
{
  "link-cache-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 43,
  "updated": "2026-07-24T00:12:03Z",
  "state": "current"
}
```

---

# 16. Response Recovery

The original transaction request remains beneath:

```text
inbox-processing/claimed/rename-moon-garden-and-change-link.json
```

Recovery recognizes that its request ID belongs to committed journal sequence `43`.

It constructs the original logical success response rather than executing the transaction again.

## Response

```json
{
  "request-id": "77777777-7777-4777-8777-777777777777",
  "request-type": "transaction",
  "status": "success",
  "generation": 43,
  "response": {
    "journal-sequence": 43,
    "entities": [
      {
        "entity": "11111111-1111-4111-8111-111111111111",
        "revision": 2
      },
      {
        "entity": "22222222-2222-4222-8222-222222222222",
        "revision": 2
      },
      {
        "entity": "33333333-3333-4333-8333-333333333333",
        "revision": 2
      }
    ]
  }
}
```

Subete writes the response to:

```text
D:/subete-example/replies/77777777-7777-4777-8777-777777777777.json
```

If the response had already been delivered before the crash, repeated delivery would still represent the same logical result.

---

# 17. Request Completion

The request moves from:

```text
inbox-processing/claimed/rename-moon-garden-and-change-link.json
```

to:

```text
inbox-processing/completed/rename-moon-garden-and-change-link.json
```

This archival movement does not affect commitment or generation.

---

# 18. Final Authoritative State

## Alice

```json
{
  "entity": "11111111-1111-4111-8111-111111111111",
  "revision": 2,
  "aspects": {
    "tag:m1lattice.net,2026:aspect/basic": {
      "typehint": "person",
      "name": "alice-morgan",
      "title": "Alice Morgan",
      "tags": [
        "person",
        "lunar-garden"
      ]
    }
  }
}
```

## Lunar Garden

```json
{
  "entity": "22222222-2222-4222-8222-222222222222",
  "revision": 2,
  "aspects": {
    "tag:m1lattice.net,2026:aspect/basic": {
      "typehint": "project",
      "name": "lunar-garden",
      "title": "Lunar Garden",
      "tags": [
        "project",
        "lunar-garden"
      ]
    }
  }
}
```

## Leadership Link

```json
{
  "entity": "33333333-3333-4333-8333-333333333333",
  "revision": 2,
  "aspects": {
    "tag:m1lattice.net,2026:aspect/basic": {
      "typehint": "link",
      "name": "alice-leads-lunar-garden",
      "title": "Alice leads Lunar Garden",
      "tags": [
        "link",
        "leadership",
        "lunar-garden"
      ]
    },
    "tag:m1lattice.net,2026:aspect/link": {
      "from": "11111111-1111-4111-8111-111111111111",
      "to": "22222222-2222-4222-8222-222222222222",
      "relationship": "leads"
    }
  }
}
```

Every affected entity now belongs to the same coherent committed transaction result.

---

# 19. Final Status

```json
{
  "status-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "state": "ready",
  "generation": 43,
  "started": "2026-07-24T00:12:00Z",
  "updated": "2026-07-24T00:12:03Z",
  "last-commit": {
    "sequence": 43,
    "timestamp": "2026-07-24T00:12:02Z",
    "request-id": "77777777-7777-4777-8777-777777777777"
  },
  "counts": {
    "entities": 3,
    "inbox": 0,
    "claimed": 0,
    "completed": 4,
    "failed": 0,
    "pending-journal": 0,
    "committed-journal": 43
  },
  "recovery": {
    "active": false
  },
  "link-cache": {
    "state": "current",
    "generation": 43
  }
}
```

Subete publishes `ready` only after the pending transaction has been fully applied and committed.

---

# 20. Final Filesystem State

```text
subete-data/
  generation.json
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
      rename-moon-garden-and-change-link.json
    failed/

  journal/
    pending/
    committed/
      00000000000000000042__44444444-4444-4444-8444-444444444444.json
      00000000000000000043__77777777-7777-4777-8777-777777777777.json

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

---

# Recovery Comparison Summary

| Affected state            | State found at startup     | Recovery action               |
| ------------------------- | -------------------------- | ----------------------------- |
| Alice entity              | Matches after-state        | Leave unchanged               |
| Project entity            | Matches after-state        | Leave unchanged               |
| Link entity               | Matches before-state       | Apply after-state             |
| Outgoing cache membership | Correct                    | Leave unchanged               |
| Incoming cache membership | Correct                    | Leave unchanged               |
| Global cache generation   | Behind at 42               | Advance to 43                 |
| Journal sequence 43       | Pending                    | Move to committed             |
| Database generation       | 42                         | Advance to 43                 |
| Claimed request           | Unfinished post-processing | Deliver response and complete |

---

# Generation Timeline

| Event                                 | Recognized committed generation |
| ------------------------------------- | ------------------------------: |
| Before transaction                    |                              42 |
| Pending journal sequence 43 completed |                              42 |
| Alice file changed                    |                              42 |
| Project file changed                  |                              42 |
| Process crashes                       |                              42 |
| Startup recovery begins               |                              42 |
| Alice recognized as already applied   |                              42 |
| Project recognized as already applied |                              42 |
| Link after-state applied              |                              42 |
| Link cache reconciled for target 43   |                              42 |
| Journal sequence 43 committed         |                              43 |
| Response delivered                    |                              43 |
| Service publishes `ready`             |                              43 |

---

# What This Example Demonstrates

* A completed pending journal entry creates a durable obligation to finish the transaction.
* The datastore may temporarily contain a mixture of before-states and after-states after a crash.
* That mixed physical state is not exposed as a committed generation.
* Recovery compares each affected entity independently with its complete journaled before-state and after-state.
* An entity already matching its after-state is not changed again.
* An entity still matching its before-state is advanced to its after-state.
* Entity revisions are not incremented twice during recovery.
* Recovery uses the journal record rather than reconstructing the lost in-memory transaction plan.
* Link-cache consequences are derived from the journaled authoritative states.
* The link cache may require generation reconciliation even when endpoint memberships did not change.
* The journal moves to `committed/` only after every authoritative and required derived state is complete.
* Generation advances only when the recovered transaction is committed.
* Response delivery and request archival occur after commitment.
* Startup does not announce `ready` until the database again represents one coherent generation.
* If any entity matched neither its journaled before-state nor its after-state, Subete would enter recovery error rather than guess.
