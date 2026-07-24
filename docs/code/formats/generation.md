# Subete — `generation.json`

`generation.json` is Subete's authoritative durable record of the current committed database generation.

It is operational metadata, not entity data. Unlike `status/status.json`, it is used by commitment, recovery, restoration, and journal-compaction decisions.

## Location

```text
subete-data/
  generation.json
```

## Format

```json
{
  "generation-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 43,
  "journal-sequence": 43,
  "updated": "2026-07-24T00:12:02Z"
}
```

## Fields

### `generation-format-version`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

### `database-id`

```json
{
  "type": "uuid",
  "required": true
}
```

Must equal the stable identity in `identity.json`.

The stored spelling is the canonical lowercase hyphenated UUID form.

### `generation`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 0
}
```

The latest generation durably published as committed.

### `journal-sequence`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 0
}
```

The journal sequence that establishes `generation`. In Version 1 it must equal `generation`.

### `updated`

```json
{
  "type": "timestamp",
  "required": true
}
```

The UTC time at which this record was published.

It must be an ISO 8601 UTC timestamp with a terminal `Z`.

## Publication and Recovery

For transaction sequence `N + 1`, Subete applies the authoritative after-state, moves the complete journal entry to `journal/committed/`, and then publishes a complete replacement `generation.json` at `N + 1`. The journal move and generation-record replacement are separate filesystem operations and therefore cannot form one filesystem-atomic operation.

Startup recovery interprets the journal and generation record together:

| Journal entry for `N + 1` | Published generation | Meaning and required action |
| --- | ---: | --- |
| `pending/` | `N` | Normal uncommitted transaction; recover its after-state and finalize commitment. |
| `committed/` | `N` | Journal commitment completed but generation publication did not; validate the committed entry and publish `N + 1`. |
| `committed/` | `N + 1` | Fully committed. |
| `pending/` | `N + 1` | Suspicious; verify whether an interrupted journal move left a matching committed copy. If not, enter recovery error rather than treating the pending entry as uncommitted. |
| neither retained | `N + 1` | Invalid unless journal history through `N + 1` was deliberately compacted behind a valid checkpoint and snapshot recovery chain. |

The record must never advance past a missing or invalid recovery chain. If the record, journal placement, checkpoint, snapshot, and authoritative state cannot establish one coherent committed world, Subete enters recovery error rather than guessing.

## Initial Database

A newly initialized empty database publishes generation `0` and journal sequence `0` before it accepts transactions.

## Rules

* The file contains exactly one UTF-8 JSON object.
* It contains exactly the fields defined by this format version.
* Only the authoritative Subete writer may replace it.
* A replacement must be fully written, flushed, and closed before publication under the final filename.
* Readers must tolerate a temporarily unreadable or incomplete visible replacement and retry; they must not substitute `status.json` as authority.
* `generation.json` is not a journal entry and does not itself authorize entity mutation.
* A valid retained checkpoint and snapshot chain may establish the history represented by generations whose committed journal files were compacted.
