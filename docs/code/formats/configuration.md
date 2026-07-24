# Subete — `configuration.json`

`configuration.json` contains the operational configuration for one Subete database.

It is machine-local operational state. It is not part of a snapshot, and
snapshot restoration must not read, merge, replace, preserve, or otherwise
operate on it. A destination database root must already have valid
configuration before a restored database is operated.

It is stored at the root of the Subete data directory:

```text
subete-data/
  configuration.json
```

## Format

```json
{
  "configuration-version": 1,
  "polling": {
    "inbox-interval-seconds": 1,
    "incomplete-file-quiet-seconds": 20,
    "stale-inbox-file-action": "retain-and-report"
  },
  "filetalk": {
    "allowed-reply-paths": [
      "D:/tmp/subete-replies/"
    ]
  }
}
```

All configuration fields other than `configuration-version` are optional unless required by a separately defined feature.

## Fields

### `configuration-version`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

Identifies the structure of `configuration.json`.

This is a format version, not the database generation or Subete software version.

### `polling`

```json
{
  "type": "object",
  "required": false
}
```

Configuration for polling filesystem surfaces such as the FileTalk inbox.

#### `inbox-interval-seconds`

```json
{
  "type": "number",
  "required": false,
  "minimum-exclusive": 0
}
```

The approximate interval between inbox polling cycles.

#### `incomplete-file-quiet-seconds`

```json
{
  "type": "number",
  "required": false,
  "minimum": 0
}
```

How long an unreadable inbox file may remain unchanged before Subete may treat it as stale or abandoned.

#### `stale-inbox-file-action`

```json
{
  "type": "string",
  "required": false,
  "allowed-values": [
    "retain-and-report",
    "quarantine",
    "delete"
  ],
  "default": "retain-and-report"
}
```

The action after the quiet period for a stale unreadable inbox file. `retain-and-report` leaves the file in place and exposes the condition through operational status or logs. `quarantine` moves it to `inbox-processing/failed/` for inspection. `delete` removes it. The default is non-destructive.

### `filetalk`

```json
{
  "type": "object",
  "required": false
}
```

Configuration governing FileTalk delivery behavior.

#### `allowed-reply-paths`

```json
{
  "type": "array",
  "required": false,
  "items": {
    "type": "file-path"
  }
}
```

Filesystem locations beneath which Subete is permitted to write reply files. For request families that require file replies, this field is required and must contain at least one location.

Each location must be an absolute directory path. Subete normalizes the configured directory and the reply destination's parent path, resolves existing parent-directory links or reparse points, and permits delivery only when the destination remains beneath one configured location. A reply destination inside Subete's own data directory is forbidden unless a later configuration version explicitly permits it.

## Rules

* `configuration.json` contains one JSON object.
* The filename is exactly `configuration.json`.
* There is at most one `configuration.json` at the database root.
* If the file is absent, Subete uses documented defaults. Under Version 1, it therefore has no allowed reply path and cannot accept a request family that requires a file reply.
* Unknown configuration fields must not be silently interpreted.
* Configuration changes do not themselves advance the database generation.
* Configuration must not contain authoritative entity facts.
* Frequently changing operational state belongs in the status surface, not in this file.
* Secrets should not be stored here unless a later specification explicitly defines secure handling for them.
