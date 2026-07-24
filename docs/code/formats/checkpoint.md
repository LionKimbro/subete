# Subete — Checkpoint Files

Checkpoint files identify accepted recovery boundaries in the Subete journal.

A checkpoint is small recovery metadata. It is not a snapshot and does not contain authoritative entity state.

## Location

Checkpoint files are stored beneath:

```text
subete-data/
  journal/
    checkpoints/
```

## Filename

```text
<generation>.json
```

Example:

```text
00000000000000010000.json
```

### Rules

* `generation` is padded to 20 decimal digits.
* Lexicographic filename order is checkpoint generation order.
* The generation inside the file must agree with the filename.

## Format

```json
{
  "checkpoint-format-version": 1,
  "database-id": "7b43887d-f9e2-4ae6-a078-7b36b163bcd0",
  "generation": 10000,
  "created": "2026-07-23T23:10:00Z",
  "snapshot": "00000000000000010000__2026-07-23T23-09-42Z.zip",
  "replay-after": 10000
}
```

## Fields

### `checkpoint-format-version`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

Identifies the structure of the checkpoint file.

### `database-id`

```json
{
  "type": "uuid",
  "required": true
}
```

The identity of the Subete database to which the checkpoint belongs.

It must match `identity.json` and the referenced snapshot.

### `generation`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 0
}
```

The committed database generation represented by the recovery base.

### `created`

```json
{
  "type": "timestamp",
  "required": true
}
```

The UTC time at which the checkpoint was established.

### `snapshot`

```json
{
  "type": "string",
  "required": true
}
```

The filename of the snapshot accepted as the recovery base.

The referenced snapshot must represent the same database identity and generation.

### `replay-after`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 0
}
```

The final journal sequence already represented by the checkpointed snapshot.

Recovery begins with committed journal entries whose sequence is greater than `replay-after`.

Normally:

```text
replay-after = generation
```

The fields remain separate so their meanings are explicit.

## Meaning

A valid checkpoint states:

> The referenced snapshot is accepted as a complete recoverable representation of this database through the stated generation, and journal replay may begin after the stated sequence.

The checkpoint does not make the snapshot authoritative during ordinary operation.

It becomes relevant when restoring or reconstructing the database.

## Creation

A checkpoint may be created only after:

1. the referenced generation is fully committed;
2. the snapshot has been completed;
3. the snapshot has been validated sufficiently for recovery use;
4. the snapshot manifest agrees with the database identity and generation;
5. the complete checkpoint file has been written.

The checkpoint must be written only after the snapshot it references is complete.

## Recovery

To recover from a checkpoint, Subete:

1. reads and validates the checkpoint;
2. locates the referenced snapshot;
3. verifies the snapshot database identity against the destination's existing
   `identity.json` and verifies the snapshot generation;
4. verifies that the snapshot contains only `entities/` and
   `snapshot-manifest.json`;
5. replaces the authoritative `entities/` store from the snapshot;
6. publishes the checkpoint/snapshot generation in root `generation.json`;
7. replays applicable committed journal entries with sequence numbers greater
   than `replay-after` through normal recovery;
8. resolves any pending journal entry according to the transaction recovery
   rules;
9. rebuilds required derived structures.

Recovery does not restore identity, configuration, journals, checkpoints,
operational state, or derived data from the snapshot. In particular, it never
reads, merges, replaces, preserves, or otherwise operates on
`configuration.json`; the destination must already be configured for its
machine.

A missing, malformed, or inconsistent checkpoint must not be silently trusted.

## Multiple Checkpoints

Subete may retain multiple checkpoint files.

The newest checkpoint is not automatically usable merely because it has the highest generation. It must also reference an available and valid snapshot.

Recovery should select the highest valid checkpoint whose required recovery artifacts are present and consistent.

Older checkpoints may be retained as fallback recovery points.

## Journal Retention

A checkpoint establishes that journal entries through `replay-after` are not required to replay changes after the checkpointed snapshot.

It does not by itself require those older journal entries to be deleted.

Journal deletion, archiving, or compaction is a separate maintenance policy and must not occur until the checkpoint and its referenced snapshot are known to be durable and sufficient.

## Immutability

Once written, a checkpoint file must not be edited in place.

A changed recovery boundary is represented by a new checkpoint file.

An invalid checkpoint may be removed through an explicit maintenance or recovery action, but it must not be silently rewritten to describe a different snapshot or generation.

## Rules

* Each checkpoint file contains one JSON object.
* Files are encoded as UTF-8.
* A checkpoint belongs to exactly one database identity.
* A checkpoint references exactly one snapshot.
* The checkpoint and snapshot must agree on database identity and generation.
* A checkpoint contains no authoritative entity or aspect values.
* Its referenced Version 1 snapshot contains only `entities/` and
  `snapshot-manifest.json`.
* A checkpoint does not advance the database generation.
* Creating a checkpoint is not a transaction over the M1 world.
* Loss of a checkpoint does not alter current authoritative entity state.
* A checkpoint must never claim a recovery boundary newer than the state represented by its snapshot.
* Snapshots preserve state; checkpoints declare trusted recovery boundaries.
* A checkpoint and its validated snapshot may establish the retained recovery chain for generations whose committed journal files have been compacted; root `generation.json` must not claim such a generation without that chain.
