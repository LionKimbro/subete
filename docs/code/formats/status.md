# Subete — `status.json`

`status.json` provides a public, read-only summary of the current operational state of Subete.

It is descriptive and derived. It is not authoritative entity state, journal state, or recovery state.

## Location

```text
subete-data/
  status/
    status.json
```

## Format

```json
{
  "status-format-version": 1,
  "database-id": "7b43887d-f9e2-4ae6-a078-7b36b163bcd0",
  "state": "ready",
  "generation": 10000,
  "started": "2026-07-23T22:00:00Z",
  "updated": "2026-07-23T23:20:00Z",
  "last-commit": {
    "sequence": 10000,
    "timestamp": "2026-07-23T23:19:42Z",
    "request-id": "7be711d6-5801-4e28-a300-81772985bcbb"
  },
  "counts": {
    "entities": 48231,
    "inbox": 2,
    "claimed": 1,
    "failed": 4
  },
  "recovery": {
    "active": false
  },
  "link-cache": {
    "state": "current",
    "generation": 10000
  },
  "latest-snapshot": {
    "generation": 9000,
    "file": "00000000000000009000__2026-07-22T20-00-00Z.zip"
  },
  "latest-checkpoint": {
    "generation": 9000,
    "file": "00000000000000009000.json"
  }
}
```

## Fields

### `status-format-version`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

Identifies the structure of `status.json`.

### `database-id`

```json
{
  "type": "uuid",
  "required": true
}
```

The identity of the Subete database described by this status file.

It must agree with `identity.json`.

### `state`

```json
{
  "type": "string",
  "required": true
}
```

The current broad operational state.

Recommended values include:

```text
starting
recovering
ready
stopping
stopped
error
```

Additional states may be introduced when needed.

### `generation`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 0
}
```

The latest committed database generation currently recognized by Subete.

This value must not advance until the corresponding transaction has fully committed.

### `started`

```json
{
  "type": "timestamp",
  "required": false
}
```

The UTC time at which the current Subete process started.

### `updated`

```json
{
  "type": "timestamp",
  "required": true
}
```

The UTC time at which `status.json` was most recently written.

### `last-commit`

```json
{
  "type": "object",
  "required": false
}
```

Describes the latest committed transaction.

Typical fields include:

```json
{
  "sequence": 10000,
  "timestamp": "2026-07-23T23:19:42Z",
  "request-id": "7be711d6-5801-4e28-a300-81772985bcbb"
}
```

This section is absent when the database has no committed transactions.

### `counts`

```json
{
  "type": "object",
  "required": false
}
```

Provides descriptive counts such as:

```text
entities
inbox
claimed
completed
failed
pending-journal
committed-journal
```

Counts may be approximate if exact calculation would be expensive.

### `recovery`

```json
{
  "type": "object",
  "required": false
}
```

Describes current recovery activity.

Example:

```json
{
  "active": true,
  "journal-sequence": 10001,
  "phase": "applying"
}
```

When no recovery is active:

```json
{
  "active": false
}
```

### `link-cache`

```json
{
  "type": "object",
  "required": false
}
```

Describes the state of the derived link cache.

Example:

```json
{
  "state": "current",
  "generation": 10000
}
```

Recommended states include:

```text
absent
stale
rebuilding
current
error
```

The recorded generation identifies the committed database generation represented by the cache.

### `latest-snapshot`

```json
{
  "type": "object",
  "required": false
}
```

Identifies the latest known completed snapshot.

Example:

```json
{
  "generation": 9000,
  "file": "00000000000000009000__2026-07-22T20-00-00Z.zip"
}
```

### `latest-checkpoint`

```json
{
  "type": "object",
  "required": false
}
```

Identifies the latest known checkpoint.

Example:

```json
{
  "generation": 9000,
  "file": "00000000000000009000.json"
}
```

## Writing

Subete may rewrite `status.json` whenever meaningful operational state changes.

It should write the complete replacement content rather than update the file incrementally.

A reader must tolerate observing the file while it is being rewritten and may retry if it cannot yet parse one complete JSON object.

## Rules

* `status.json` contains one JSON object.
* The file is encoded as UTF-8.
* The filename is exactly `status.json`.
* The file is safe for external read-only inspection.
* The file must not be used as the authoritative source for entity data, journal commitment, checkpoints, or recovery decisions.
* Missing or stale status information does not alter authoritative database state.
* Creating or updating the file does not advance the database generation.
* Fields may be omitted when their information is unavailable or too expensive to calculate.
* Unknown fields may be added in later format versions.
* Readers should treat the file as an operational summary, not as a transactional interface.
