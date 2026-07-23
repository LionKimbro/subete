# Subete — `heartbeat.json`

`heartbeat.json` provides a small, frequently updated indication that the Subete process is alive.

It is descriptive and operational. It is not authoritative database state and does not replace process locking or recovery checks.

## Location

```text
subete-data/
  status/
    heartbeat.json
```

## Format

```json
{
  "heartbeat-format-version": 1,
  "database-id": "7b43887d-f9e2-4ae6-a078-7b36b163bcd0",
  "process-id": 18432,
  "started": "2026-07-23T22:00:00Z",
  "heartbeat": "2026-07-23T23:20:05Z",
  "state": "ready",
  "generation": 10000
}
```

## Fields

### `heartbeat-format-version`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

Identifies the structure of `heartbeat.json`.

### `database-id`

```json
{
  "type": "uuid",
  "required": true
}
```

The identity of the Subete database served by the process.

It must agree with `identity.json`.

### `process-id`

```json
{
  "type": "integer",
  "required": false,
  "minimum": 1
}
```

The operating-system process identifier of the running Subete process.

It is descriptive and may be reused by the operating system after the process exits.

### `started`

```json
{
  "type": "timestamp",
  "required": true
}
```

The UTC time at which the current Subete process started.

### `heartbeat`

```json
{
  "type": "timestamp",
  "required": true
}
```

The UTC time at which this heartbeat record was most recently written.

### `state`

```json
{
  "type": "string",
  "required": true
}
```

The broad current process state.

Recommended values include:

```text
starting
recovering
ready
stopping
error
```

### `generation`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 0
}
```

The latest committed database generation recognized by the process when the heartbeat was written.

## Writing

Subete rewrites `heartbeat.json` periodically while running.

The heartbeat interval is operational configuration.

Subete may also rewrite the file immediately when its broad process state changes.

The complete file should be rewritten rather than updated field by field.

A reader must tolerate observing the file while it is being rewritten and may retry if it cannot yet parse one complete JSON object.

## Interpretation

A recent heartbeat is evidence that a Subete process was recently active.

It is not conclusive proof that:

* the process still exists;
* the process owns the writer lock;
* the process is healthy;
* the database is ready;
* the reported generation is authoritative.

Readers should consider the heartbeat timestamp together with `status.json`, the locking framework, and any direct command result.

A stale heartbeat may indicate that the process stopped, stalled, lost access to the status directory, or failed before it could update the file.

## Rules

* `heartbeat.json` contains one JSON object.
* The file is encoded as UTF-8.
* The filename is exactly `heartbeat.json`.
* Updating the heartbeat does not advance the database generation.
* Missing, stale, or malformed heartbeat data does not alter authoritative database state.
* The heartbeat must not be used as a substitute for `lock.json` or lionscliapp locking behavior.
* The file should remain small and inexpensive to rewrite.
* Detailed counts and diagnostics belong in `status.json` or `metrics.json`, not here.
