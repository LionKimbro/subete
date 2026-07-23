# Subete — Journal Entry Files

Journal entry files are Subete’s write-ahead records of transactions.

A complete journal entry records the transaction request, the authoritative state before the transaction, and the complete intended state after the transaction.

Once the entry is complete and durable, Subete may begin applying the transaction to the authoritative datastore.

## Locations

Journal entries move between two locations:

```text
subete-data/
  journal/
    pending/
    committed/
```

A complete entry in `pending/` authorizes transaction application.

The same entry moves to `committed/` after its complete intended after-state has become authoritative.

A journal file still being constructed belongs in `tmp/`, not in `journal/pending/`.

## Filename

```text
<sequence>__<request-id>.json
```

Example:

```text
00000000000000000143__7be711d6-5801-4e28-a300-81772985bcbb.json
```

### Rules

* `sequence` is the transaction’s journal sequence number, padded to 20 decimal digits.
* `request-id` is copied from the originating transaction request.
* Lexicographic filename order is journal sequence order.
* The filename remains unchanged when moved from `pending/` to `committed/`.
* The sequence and request ID inside the file must agree with the filename.

## Format

```json
{
  "journal-format-version": 1,
  "database-id": "7b43887d-f9e2-4ae6-a078-7b36b163bcd0",
  "sequence": 143,
  "journaled": "2026-07-23T22:15:00Z",
  "request-id": "7be711d6-5801-4e28-a300-81772985bcbb",
  "transaction-request": {
    "request-id": "7be711d6-5801-4e28-a300-81772985bcbb",
    "request-type": "transaction",
    "reply": {
      "type": "file",
      "path": "D:/tmp/subete-replies/7be711d6-5801-4e28-a300-81772985bcbb.json"
    },
    "request": {
      "operations": [
        {
          "operation": "set-aspect",
          "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
          "expected-revision": 12,
          "aspect": "tag:m1lattice.net,2026/aspect/basic",
          "value": {
            "title": "Updated Title"
          }
        }
      ]
    }
  },
  "entities": {
    "209ee0b8-36d5-4a47-81ca-c59f0eaac29d": {
      "before": {
        "revision": 12,
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "title": "Original Title"
          }
        }
      },
      "after": {
        "revision": 13,
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "title": "Updated Title"
          }
        }
      }
    }
  }
}
```

## Fields

### `journal-format-version`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

Identifies the structure of the journal entry.

This is not the database generation or Subete software version.

### `database-id`

```json
{
  "type": "uuid",
  "required": true
}
```

The identity of the Subete database whose transaction history contains this entry.

It must match the database root’s `identity.json`.

### `sequence`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

The monotonically increasing journal sequence assigned to the transaction.

When the transaction commits, this number also becomes the resulting database generation.

### `journaled`

```json
{
  "type": "timestamp",
  "required": true
}
```

The UTC time at which the complete journal entry was prepared for durable placement in `journal/pending/`.

It is not necessarily the time at which transaction application completed.

### `request-id`

```json
{
  "type": "uuid",
  "required": true
}
```

The identity of the originating transaction request.

It supports duplicate-request detection and recovery after uncertain reply delivery.

### `transaction-request`

```json
{
  "type": "object",
  "required": true
}
```

The complete originating transaction request.

Its structure and semantics are defined by `protocol-crud.md`.

Preserving the original request records what the caller asked Subete to do, including its request identity and reply destination.

### `entities`

```json
{
  "type": "object",
  "required": true
}
```

Maps every affected entity ID to its complete logical before-state and intended after-state.

An entity appears once, even when several operations affect different aspects on that entity.

The entity states include all authoritative aspects, including aspects backed by different physical storage mechanisms.

## Entity Transition

```json
{
  "before": {
    "revision": 12,
    "aspects": {
      "...": "..."
    }
  },
  "after": {
    "revision": 13,
    "aspects": {
      "...": "..."
    }
  }
}
```

### `before`

The complete committed logical entity state before the transaction.

### `after`

The complete intended logical entity state after the transaction.

Each non-null entity state contains:

```json
{
  "revision": 12,
  "aspects": {
    "<aspect-id>": "<complete-aspect-value>"
  }
}
```

The `aspects` object contains the complete logical aspect set across every authoritative backing store.

## Entity Creation

Creation is represented with a null before-state:

```json
{
  "before": null,
  "after": {
    "revision": 1,
    "aspects": {
      "tag:m1lattice.net,2026/aspect/basic": {
        "title": "New Entity"
      }
    }
  }
}
```

## Entity Deletion

Deletion is represented with a null after-state:

```json
{
  "before": {
    "revision": 8,
    "aspects": {
      "tag:m1lattice.net,2026/aspect/basic": {
        "title": "Obsolete Entity"
      }
    }
  },
  "after": null
}
```

## No-Op Operations

A transaction may contain an operation that produces no change, such as deleting an aspect that is already absent.

An entity whose complete before-state and after-state are identical may remain recorded in the journal entry to preserve the meaning and result of the originating request.

Its revision does not advance.

A transaction that produces no authoritative changes still receives a journal sequence and commits as a transaction unless the transaction protocol later defines otherwise.

## Write Procedure

Subete prepares a journal entry as follows:

1. validate the complete transaction request;
2. read the current committed state of every affected entity;
3. verify all expected revisions;
4. compute the complete intended after-state;
5. allocate the next journal sequence;
6. write the complete journal entry beneath `tmp/`;
7. flush and close the file;
8. place the complete file in `journal/pending/`;
9. begin authoritative datastore mutation.

No authoritative datastore mutation may begin before Step 8 is complete.

## Pending Entries

A journal entry in `journal/pending/` may represent a transaction that is:

* not yet applied;
* partially applied;
* fully applied but not yet finalized;
* interrupted while being moved to `journal/committed/`.

During startup recovery, Subete compares each affected entity’s current logical state with its journaled states:

* matching `after` means that entity is already applied;
* matching `before` means that entity still requires application;
* matching neither indicates an inconsistency requiring explicit handling.

Recovery continues until every affected entity matches its intended after-state.

## Committed Entries

After every affected entity and authoritative backing store matches the intended after-state:

1. the journal entry moves to `journal/committed/`;
2. the database generation becomes the entry’s sequence number;
3. derived structures required for current service are reconciled;
4. the transaction result may be delivered to the caller.

The journal file contents do not need to change when committed. Its directory location identifies whether it is pending or committed.

## Immutability

Once a complete journal entry has entered `journal/pending/`, its contents must not be edited.

Recovery and commitment move or inspect the file; they do not rewrite its transaction meaning.

If the journal entry is found to be internally invalid after entering `pending/`, Subete must stop normal service and report a recovery error rather than silently alter or discard the entry.

## Rules

* Each file contains one JSON object.
* Files are encoded as UTF-8.
* Every journal entry belongs to exactly one database identity.
* Every sequence number is used by at most one transaction.
* Journal sequences increase monotonically.
* A complete entry must exist in `pending/` before datastore mutation begins.
* The `entities` map contains every entity affected by the transaction.
* Before-states and after-states describe complete logical entities, not only the aspects mentioned by operations.
* Journal entries cover every authoritative storage mechanism.
* A pending entry is sufficient to complete transaction recovery.
* Moving an entry to `committed/` does not itself alter entity state.
* Journal entries are not the current authoritative entity datastore.
* Committed entries preserve ordered transaction history and support replay after a checkpoint.
