# Subete — `identity.json`

`identity.json` identifies one Subete database world.

It is stored at the root of the Subete data directory:

```text
subete-data/
  identity.json
```

## Format

```json
{
  "database-id": "7b43887d-f9e2-4ae6-a078-7b36b163bcd0",
  "created": "2026-07-23T22:15:00Z",
  "name": "lion-subete",
  "title": "Lion's Subete"
}
```

## Fields

### `database-id`

```json
{
  "type": "uuid",
  "required": true
}
```

The stable identity of this Subete database.

The stored spelling is the canonical lowercase hyphenated UUID form.

It is created when the database is initialized and must not change during ordinary operation, restart, upgrade, snapshot creation, or recovery.

### `created`

```json
{
  "type": "timestamp",
  "required": true
}
```

The UTC time at which this database identity was created.

It must be an ISO 8601 UTC timestamp with a terminal `Z`.

### `name`

```json
{
  "type": "string",
  "required": false,
  "constraints": {
    "pattern": "^[a-z][a-z0-9_-]*$"
  }
}
```

An optional short, program-friendly name for the database.

It uses lowercase identifier-style text and contains no spaces.

The name is descriptive and does not participate in database identity.

### `title`

```json
{
  "type": "string",
  "required": false
}
```

An optional human-readable title for the database.

The title may contain spaces, capitalization, punctuation, and other display-oriented text.

It is descriptive and does not participate in database identity.

## Rules

* `identity.json` contains one JSON object.
* The filename is exactly `identity.json`.
* There is exactly one `identity.json` at the database root.
* It contains the required `database-id` and `created` fields, and may contain
  only the documented optional `name` and `title` fields.
* `database-id` is the authoritative identity of the database.
* Restoring the same database requires the snapshot manifest's `database-id`
  to match the destination's existing `identity.json`; restoration does not
  copy or replace this file.
* Creating a distinct new database creates a new `database-id`.
* `name` and `title` may be changed without changing database identity.
* The file must not contain the current generation or other frequently changing operational state.
