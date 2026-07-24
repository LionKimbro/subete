# Subete — Snapshot Manifest

A snapshot manifest describes one complete snapshot of a Subete database at a committed generation.

The manifest identifies the database, generation, snapshot contents, and integrity information needed to validate restoration.

## Location

Each snapshot is stored beneath:

```text
subete-data/
  snapshots/
```

A snapshot may be represented as a directory or archive.

The manifest is stored inside the snapshot as:

```text
snapshot-manifest.json
```

Example archive:

```text
00000000000000010000__2026-07-23T23-09-42Z.zip
```

containing:

```text
snapshot-manifest.json
entities/
```

These are the only two top-level members of a Version 1 snapshot.

## Snapshot Filename

```text
<generation>__<created>.zip
```

Example:

```text
00000000000000010000__2026-07-23T23-09-42Z.zip
```

### Rules

* `generation` is padded to 20 decimal digits.
* `created` is a filesystem-safe UTC timestamp.
* The archive filename is descriptive; the manifest contents are authoritative.
* Alternate snapshot packaging may be defined later.

## Format

```json
{
  "snapshot-format-version": 1,
  "database-id": "7b43887d-f9e2-4ae6-a078-7b36b163bcd0",
  "generation": 10000,
  "created": "2026-07-23T23:09:42Z",
  "contents": [
    {
      "path": "entities/",
      "kind": "authoritative-store"
    }
  ],
  "entity-count": 48231
}
```

## Fields

### `snapshot-format-version`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

Identifies the structure of the snapshot and its manifest.

### `database-id`

```json
{
  "type": "uuid",
  "required": true
}
```

The stable identity of the database represented by the snapshot.

The snapshot does not contain `identity.json`. During restoration,
`database-id` must agree with the destination database's existing
`identity.json`.

### `generation`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 0
}
```

The committed database generation captured by the snapshot.

Every entity file included in the snapshot must represent this same
generation.

### `created`

```json
{
  "type": "timestamp",
  "required": true
}
```

The UTC time at which snapshot construction completed.

### `contents`

```json
{
  "type": "array",
  "required": true,
  "minimum-items": 1
}
```

Lists the authoritative content contained in the snapshot.

In Version 1 this array contains exactly one entry for `entities/`.

Each entry contains:

```json
{
  "path": "entities/",
  "kind": "authoritative-store"
}
```

#### `path`

```json
{
  "type": "string",
  "required": true
}
```

A path relative to the root of the snapshot.

Absolute paths are forbidden.

#### `kind`

```json
{
  "type": "string",
  "required": true
}
```

Describes the role of the included content.

The Version 1 value is:

```text
authoritative-store
```

Additional kinds require a later snapshot-format version.

### `entity-count`

```json
{
  "type": "integer",
  "required": false,
  "minimum": 0
}
```

The number of logical entities represented in the snapshot.

This is descriptive validation information. It does not define snapshot contents.

## Exact Snapshot Scope

A Version 1 snapshot captures the authoritative entity store only.

It contains exactly:

```text
snapshot-manifest.json
entities/
```

It must not contain:

* `configuration.json`;
* framework `config.json`;
* `identity.json`;
* `generation.json`;
* locks;
* journals;
* checkpoints;
* inbox or request-processing state;
* status, heartbeat, or metrics;
* temporary files;
* link-cache or other derived data.

Database identity and generation are carried as validation metadata in
`snapshot-manifest.json`; their root files are not copied into the archive.
If a future storage design adds another authoritative store, that design
requires a later snapshot-format version rather than silently widening the
Version 1 archive.

## Consistent Generation

A snapshot must represent one coherent committed generation.

Snapshot creation must not combine entity files from different generations
or include partially applied, temporary, or speculative state.

Subete must obtain a consistent view of `entities/` at the selected committed
generation.

## Integrity Information

Content entries may include integrity information:

```json
{
  "path": "entities/",
  "kind": "authoritative-store",
  "sha256": "..."
}
```

Any file inventory or digest information required by snapshot policy must be
stored inside `snapshot-manifest.json`; it must not add another snapshot
member.

Integrity fields are optional unless required by snapshot policy.

A checksum validates bytes. It does not replace validation of database identity, generation, structure, or recovery semantics.

## Creation

A snapshot is created only from committed state.

A normal creation procedure is:

1. read root `generation.json` and identify its committed generation to capture;
2. obtain a consistent view of `entities/` at that generation;
3. copy `entities/` into the temporary snapshot workspace;
4. write `snapshot-manifest.json`;
5. complete and close the snapshot artifact;
6. validate the snapshot sufficiently for recovery use;
7. optionally establish a checkpoint referring to it.

Creating a snapshot does not advance the database generation.

## Restoration

Before restoring a snapshot, Subete validates:

* the manifest structure;
* agreement between manifest `database-id` and the destination
  `identity.json`;
* the snapshot generation;
* that the archive contains exactly `snapshot-manifest.json` and `entities/`;
* any required integrity information;
* consistency with the selected checkpoint, when one is used.

Restoration replaces the destination `entities/` store with the validated
snapshot state and publishes the snapshot generation in root
`generation.json`.

Applicable committed journal entries after the snapshot generation are then
replayed through the normal recovery machinery. Any pending next transaction
is resolved by that same machinery, and derived structures are rebuilt.

After replay and any required pending-transaction recovery establish one coherent world, Subete publishes root `generation.json` for the resulting generation before ordinary service resumes. A stale or absent status file is never a substitute for this step.

## Configuration

`configuration.json` is outside snapshot restoration entirely.

Restoration must not read it as snapshot input, copy it into the snapshot,
restore it, merge it, replace it, preserve it as part of a datastore swap, or
otherwise operate on it.

The destination database root must already have whatever valid machine-local
configuration is required before the restored database is operated.

## Immutability

A completed snapshot must not be edited in place.

A modified snapshot is a different artifact and should receive a new creation timestamp and manifest.

The generation may remain the same if the new artifact represents exactly the same committed world, but it must not reuse integrity claims from the previous artifact without recomputation.

## Rules

* A snapshot contains one `snapshot-manifest.json`.
* The manifest is encoded as UTF-8.
* A snapshot belongs to exactly one database identity.
* A snapshot represents exactly one committed generation.
* A Version 1 snapshot contains exactly `snapshot-manifest.json` and
  `entities/`.
* A snapshot contains no partial transaction state.
* A snapshot contains no configuration, operational state, recovery
  artifacts, temporary files, or derived data.
* Restoration operates on the authoritative entity store and generation,
  never on `configuration.json`.
* Creating or deleting a snapshot does not alter current authoritative entity state.
* Creating a snapshot does not advance the database generation.
* A snapshot does not become a recovery checkpoint merely by existing.
* A checkpoint may separately designate a validated snapshot as a trusted recovery base.
