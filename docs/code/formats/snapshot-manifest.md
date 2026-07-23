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
identity.json
configuration.json
entities/
...
```

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
      "path": "identity.json",
      "kind": "database-identity"
    },
    {
      "path": "configuration.json",
      "kind": "configuration"
    },
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

It must agree with the included `identity.json`.

### `generation`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 0
}
```

The committed database generation captured by the snapshot.

Every authoritative store included in the snapshot must represent this same generation.

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

Lists the files, directories, or authoritative stores contained in the snapshot.

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

Typical values include:

```text
database-identity
configuration
authoritative-store
supporting-metadata
```

Additional kinds may be introduced as the storage architecture evolves.

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

## Authoritative Stores

A snapshot must include every authoritative storage mechanism necessary to reconstruct the complete logical Subete world at its generation.

Initially, this includes:

```text
entities/
```

If hybrid storage is introduced, the snapshot must also include complete recoverable representations of any authoritative SQLite databases or other backing stores.

Derived structures such as search indexes and the link cache may be included to accelerate restoration, but they are not required for authoritative recovery because they are rebuildable.

If derived structures are included, the manifest must distinguish them from authoritative stores.

## Consistent Generation

A snapshot must represent one coherent committed generation.

Snapshot creation must not combine:

* entity files from one generation;
* an authoritative SQLite store from another generation;
* partially applied transaction state;
* temporary or speculative values.

Subete must use a snapshot procedure that obtains a consistent view across every authoritative store.

## Integrity Information

Content entries may include integrity information:

```json
{
  "path": "entities/",
  "kind": "authoritative-store",
  "sha256": "..."
}
```

For a directory, integrity may instead be represented by a separate inventory or digest file included in the snapshot.

Integrity fields are optional unless required by snapshot policy.

A checksum validates bytes. It does not replace validation of database identity, generation, structure, or recovery semantics.

## Creation

A snapshot is created only from committed state.

A normal creation procedure is:

1. identify the committed generation to capture;
2. obtain a consistent view of every authoritative store at that generation;
3. copy the required database identity, configuration, and authoritative stores;
4. write `snapshot-manifest.json`;
5. complete and close the snapshot artifact;
6. validate the snapshot sufficiently for recovery use;
7. optionally establish a checkpoint referring to it.

Creating a snapshot does not advance the database generation.

## Restoration

Before restoring a snapshot, Subete validates:

* the manifest structure;
* the database identity;
* the snapshot generation;
* the presence of every required authoritative store;
* any required integrity information;
* consistency with the selected checkpoint, when one is used.

Restoration replaces or reconstructs the authoritative datastore from the snapshot.

Committed journal entries after the snapshot generation may then be replayed.

## Configuration

The snapshot may preserve the database’s `configuration.json`, but restoration policy determines whether that configuration is restored verbatim, merged, or replaced by environment-specific configuration.

The database identity and authoritative entity state are recovery-critical.

Operational configuration may contain machine-specific paths and therefore requires explicit handling.

## Immutability

A completed snapshot must not be edited in place.

A modified snapshot is a different artifact and should receive a new creation timestamp and manifest.

The generation may remain the same if the new artifact represents exactly the same committed world, but it must not reuse integrity claims from the previous artifact without recomputation.

## Rules

* A snapshot contains one `snapshot-manifest.json`.
* The manifest is encoded as UTF-8.
* A snapshot belongs to exactly one database identity.
* A snapshot represents exactly one committed generation.
* Every authoritative store required to reconstruct that generation is included.
* A snapshot contains no partial transaction state.
* Derived structures, when included, must be identified as derived.
* Creating or deleting a snapshot does not alter current authoritative entity state.
* Creating a snapshot does not advance the database generation.
* A snapshot does not become a recovery checkpoint merely by existing.
* A checkpoint may separately designate a validated snapshot as a trusted recovery base.
