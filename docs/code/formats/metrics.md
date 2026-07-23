# Subete — `metrics.json`

`metrics.json` provides operational measurements about the running Subete process and database activity.

It is descriptive and derived. It is not authoritative entity state, transaction state, or recovery state.

## Location

```text
subete-data/
  status/
    metrics.json
```

## Format

```json
{
  "metrics-format-version": 1,
  "database-id": "7b43887d-f9e2-4ae6-a078-7b36b163bcd0",
  "started": "2026-07-23T22:00:00Z",
  "updated": "2026-07-23T23:20:05Z",
  "generation": 10000,
  "requests": {
    "received": 12840,
    "completed": 12791,
    "failed": 49
  },
  "transactions": {
    "committed": 10000,
    "rejected": 31,
    "recovered": 2
  },
  "reads": {
    "completed": 1910
  },
  "searches": {
    "completed": 881
  },
  "timing": {
    "last-request-seconds": 0.014,
    "average-request-seconds": 0.021
  },
  "storage": {
    "entities": 48231,
    "entity-bytes": 124918223,
    "journal-bytes": 84219931
  }
}
```

All measurement groups are optional unless required by a later specification.

## Fields

### `metrics-format-version`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

Identifies the structure of `metrics.json`.

### `database-id`

```json
{
  "type": "uuid",
  "required": true
}
```

The identity of the Subete database described by the metrics.

It must agree with `identity.json`.

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

The UTC time at which the metrics file was most recently written.

### `generation`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 0
}
```

The latest committed database generation recognized when the metrics were written.

## Metric Groups

### `requests`

May contain cumulative counts for the current process lifetime, including:

```text
received
claimed
completed
failed
reply-delivery-failed
```

### `transactions`

May contain counts including:

```text
committed
rejected
recovered
no-op
revision-conflict
```

### `reads`

May contain counts including:

```text
completed
failed
entities-returned
aspects-returned
not-found
```

### `searches`

May contain counts including:

```text
completed
failed
entities-scanned
entities-matched
```

### `timing`

May contain operational timing measurements in seconds, including:

```text
last-request-seconds
average-request-seconds
last-transaction-seconds
average-transaction-seconds
last-read-seconds
average-read-seconds
last-search-seconds
average-search-seconds
```

Timing values are descriptive and need not provide strict statistical guarantees.

### `storage`

May contain approximate storage measurements, including:

```text
entities
entity-bytes
pending-journal-files
committed-journal-files
journal-bytes
snapshot-files
snapshot-bytes
```

### `recovery`

May contain counts or timing information for recovery work, including:

```text
runs
transactions-completed
failures
last-duration-seconds
```

### `link-cache`

May contain measurements such as:

```text
generation
entries
rebuilds
last-rebuild-seconds
```

## Counter Scope

Unless otherwise stated, cumulative counters describe the lifetime of the current Subete process.

A process restart may reset them.

Metrics that persist across restarts must be explicitly identified as persistent and must not rely on `metrics.json` alone as authoritative storage.

## Writing

Subete may rewrite `metrics.json` periodically or after meaningful activity.

The file should be written as one complete replacement object.

A reader must tolerate observing it while it is being rewritten and may retry if it cannot yet parse one complete JSON object.

Collecting metrics must not block or materially endanger transaction processing.

Expensive measurements may be omitted, delayed, sampled, or reported approximately.

## Rules

* `metrics.json` contains one JSON object.
* The file is encoded as UTF-8.
* The filename is exactly `metrics.json`.
* Metrics are descriptive and derived.
* Missing, stale, approximate, or malformed metrics do not alter authoritative database state.
* Updating metrics does not advance the database generation.
* Counters must not be used to determine whether a transaction committed.
* `generation` reports the committed generation observed when the file was written.
* Unknown metric groups and fields may be introduced later.
* Detailed event history belongs in journals or logs, not in `metrics.json`.
* The file should remain reasonably small and inexpensive to rewrite.
