# Subete — `configuration.json`

`configuration.json` contains the operational configuration for one Subete database.

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
    "incomplete-file-quiet-seconds": 20
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

Optional filesystem locations beneath which Subete is permitted to write reply files.

The exact path-matching and security rules are defined by the FileTalk implementation.

## Rules

* `configuration.json` contains one JSON object.
* The filename is exactly `configuration.json`.
* There is at most one `configuration.json` at the database root.
* If the file is absent, Subete uses documented defaults.
* Unknown configuration fields must not be silently interpreted.
* Configuration changes do not themselves advance the database generation.
* Configuration must not contain authoritative entity facts.
* Frequently changing operational state belongs in the status surface, not in this file.
* Secrets should not be stored here unless a later specification explicitly defines secure handling for them.
