# Subete — Filesystem Layout

This document defines the initial filesystem layout of a Subete database.

The layout is intentionally simple and visible. It supports authoritative entity storage, FileTalk request processing, write-ahead journaling, recovery, snapshots, checkpoints, status reporting, and temporary work.

The initial layout is:

```text
subete-data/
  config.json
  identity.json
  configuration.json
  generation.json
  lock.json

  entities/
  link-cache/

  journal/
    pending/
    committed/
    checkpoints/

  snapshots/

  inbox/

  inbox-processing/
    claimed/
    completed/
    failed/

  status/
    status.json
    heartbeat.json
    metrics.json

  tmp/
```

The database root may have any filesystem path. Programs must not depend on the directory being named `subete-data`.

## Root Files

### `config.json`

`config.json` is optional framework-owned `lionscliapp` CLI configuration. It is
not Subete operational configuration, authoritative state, or part of the
database protocol. The framework reads it when present and writes it only when
its configuration is explicitly persisted.

### `identity.json`

`identity.json` identifies the Subete database itself.

It contains stable database identity information that distinguishes this Subete world from other databases, restored copies, test databases, and unrelated directory trees.

The database identity must not be casually regenerated when the database process restarts.

The exact format is defined separately.

### `configuration.json`

`configuration.json` contains configuration governing the operation of this database.

Configuration may include filesystem behavior, FileTalk settings, operational limits, snapshot policy, status publication settings, or declarations describing authoritative storage mechanisms.

Configuration does not itself contain authoritative entity facts.

The exact format is defined separately.

### `generation.json`

`generation.json` is the authoritative durable record of the latest committed database generation and its establishing journal sequence.

It is operational metadata used by transaction commitment, startup recovery, restoration, and journal compaction. It is not a descriptive status file.

The exact format and transitional recovery rules are defined in `formats/generation.md`.

### `lock.json`

`lock.json` is used by the surrounding `lionscliapp` command framework to coordinate commands and process ownership.

Subete selects its database root through the framework execution root. Its
framework project directory is `.`, so a lock-requiring command acquires
`<database-root>/lock.json`.

The locking framework determines which commands require exclusive access and which commands may safely operate without taking the primary writer lock.

Subete does not define a second independent locking system inside this document.

## Authoritative Datastore

### `entities/`

`entities/` is the initial authoritative backing store for entity and aspect data.

In Version 1, each entity is represented by a file beneath this directory. Version 1 has no hybrid or SQLite-backed authoritative aspect storage.

The directory is initially flat. Entity files are not sharded into subdirectories until scale or filesystem behavior demonstrates a concrete need.

The exact entity filename convention and file format are defined separately.

Only the authoritative Subete writer may modify files under `entities/`.

The authoritative datastore is a logical concept rather than a permanent commitment to one physical format. A future version may store particular aspects in SQLite or other authoritative stores. Such hybrid storage is out of Version 1 scope. When it is introduced, those stores must participate fully in transactions, journaling, recovery, snapshots, and generation consistency.

`entities/` remains authoritative for all entity state assigned to it. Data must not silently exist in two competing authoritative locations.

## Derived Link Cache

### `link-cache/`

`link-cache/` is the derived lookup structure used to locate link entities attached to an entity without scanning the complete authoritative datastore.

The authoritative relationship is always the link entity and its committed link aspect. The link cache contains only references to those authoritative link entities.

The cache supports locating:

* links whose `from` endpoint is a specified entity;
* links whose `to` endpoint is a specified entity;
* all links attached to a specified entity.

The link cache must be updated when a transaction creates, changes, or deletes a link entity.

The cache records the database generation through which it is current. Subete must not present link-cache results as current when the cache does not reflect the committed database generation.

`link-cache/` is derived and rebuildable. It may be deleted and reconstructed entirely by scanning authoritative entities for link aspects.

Loss or corruption of the link cache may reduce availability or require reconstruction, but it does not constitute loss of authoritative relationship data.

The exact filesystem organization, file formats, update procedure, recovery behavior, and reconstruction process are defined in `link-cache.md`.

## Journal

### `journal/pending/`

`journal/pending/` contains complete journal entries for transactions that have been authorized to begin datastore mutation but have not yet been finalized as committed.

A transaction may enter this directory only after its full journal record has been written successfully.

A pending entry may represent:

* a transaction not yet applied;
* a partially applied transaction;
* a fully applied transaction awaiting final commitment;
* a committed transaction whose journal-file transition was interrupted.

Pending entries are inspected during startup recovery.

An incomplete journal file does not represent an authorized transaction and may be removed according to the recovery rules.

### `journal/committed/`

`journal/committed/` contains journal entries for transactions whose complete intended after-state has become authoritative.

Each committed journal entry has a unique monotonically increasing sequence number.

That sequence number is also the resulting database generation.

Committed journal entries form the durable ordered transaction history after the applicable checkpoint boundary.

### `journal/checkpoints/`

`journal/checkpoints/` contains checkpoint records.

A checkpoint is a small durable recovery statement identifying an accepted recovery boundary. It may identify:

* a snapshot accepted as a restoration base;
* the generation represented by that snapshot;
* the last journal sequence incorporated into the recovery base;
* the journal sequence from which replay should resume;
* integrity or identity information needed to validate the relationship.

A checkpoint is not a snapshot and does not contain the full entity world.

The exact checkpoint format and lifecycle are defined separately.

## Snapshots

### `snapshots/`

`snapshots/` contains preserved recoverable representations of the
authoritative entity store at identified generations.

A Version 1 snapshot archive contains exactly:

```text
snapshot-manifest.json
entities/
```

The manifest carries the database identity, generation, creation time,
contents, and integrity information needed to identify and validate the
snapshot. Root identity and generation files themselves are not snapshot
members.

A snapshot must not contain `configuration.json`, framework `config.json`,
locks, journals, checkpoints, inbox or request-processing state, status,
heartbeat, metrics, temporary files, or derived link-cache data.

Restoration replaces `entities/` only. It never reads, merges, replaces,
preserves, or otherwise operates on `configuration.json`; the destination
root must already have valid machine-local configuration before operation.

Snapshots are archival recovery artifacts. Their presence does not make them the current authoritative datastore.

The exact snapshot structure and lifecycle are defined separately.

## FileTalk Inbox

### `inbox/`

`inbox/` is the public request-entry surface.

External programs submit FileTalk requests by placing request files into this directory.

FileTalk delivery is defined by `filetalk-protocol.md`. A caller may write directly to the final inbox filename, so a visible request file may still be incomplete. Writing a temporary file and atomically renaming it into place is a recommended optimization, not a requirement; it is possible only when the temporary and final paths are on the same filesystem. Subete must tolerate incomplete visible files by applying the FileTalk incomplete-file handling rules before claiming or processing a request.

External programs may create requests under `inbox/`, but they must not modify Subete’s authoritative datastore, journal, checkpoints, snapshots, processing state, or status records.

Subete claims requests from this directory before processing them.

## Request Processing

### `inbox-processing/claimed/`

`inbox-processing/claimed/` contains requests that Subete has claimed for processing.

Claiming removes the request from the public inbox and establishes that the running Subete process owns its execution.

A claimed request may still be awaiting validation, execution, recovery, or response delivery.

### `inbox-processing/completed/`

`inbox-processing/completed/` contains requests that completed successfully.

Completed request records support inspection, auditing, and duplicate-request
detection. For transactions, committed journal history supports recovery from
uncertain response delivery. Completed and failed maintenance records retain
their complete logical responses so checkpoint, removal, and stop outcomes can
be reproduced without intentionally performing the operation again. Version 1
does not require completed read or search records to retain their response
bodies.

Retention or compaction policy may later remove old completed requests when their required identity and transaction-outcome information remain safely represented elsewhere.

### `inbox-processing/failed/`

`inbox-processing/failed/` contains requests that could not be completed.

Examples include malformed requests, failed validation, unsupported operations, violated transaction conditions, or undeliverable responses when the defined policy treats that as failure.

Failure records should preserve enough information to understand the request and the reason for failure.

A failed request must not be confused with a journaled transaction that was interrupted during datastore mutation. Once authoritative mutation has begun, recovery governs the transaction until completion.

## Status Surface

### `status/status.json`

`status/status.json` provides a public read-only summary of the database’s current operational state.

It may include:

* database identity;
* process state;
* current committed generation;
* last committed transaction;
* entity counts;
* inbox and processing counts;
* active recovery information;
* latest snapshot and checkpoint information;
* freshness of derived services.

The status file is descriptive and is not authoritative entity or transaction state.

### `status/heartbeat.json`

`status/heartbeat.json` indicates that the running Subete process is alive and periodically updating its public status surface.

It may include the process identity, startup time, last heartbeat time, current activity, and current generation.

The heartbeat is advisory. It must not replace the locking framework or authoritative recovery checks.

### `status/metrics.json`

`status/metrics.json` exposes operational measurements.

It may contain request counts, transaction counts, search counts, failure counts, recovery counts, timing measurements, datastore sizes, or other diagnostic information.

Metrics are derived and may be discarded or reconstructed without loss of authoritative data.

## Temporary Workspace

### `tmp/`

`tmp/` contains temporary files created during safe filesystem operations.

Examples include:

* entity replacement files written before rename;
* journal files still being constructed;
* response files before delivery;
* snapshot construction work;
* status files before atomic replacement;
* recovery scratch files.

Nothing under `tmp/` is authoritative merely because it exists.

A complete journal entry must be established before temporary datastore replacements may be promoted into authoritative storage.

Startup recovery may inspect or remove abandoned temporary files according to clearly defined filename and ownership rules.

## Ownership Summary

The initial paths have the following roles:

| Path                          | Role                                                       |
| ----------------------------- | ---------------------------------------------------------- |
| `config.json`                 | Optional framework-owned CLI configuration                 |
| `identity.json`               | Stable identity of the database                            |
| `configuration.json`          | Operational configuration                                  |
| `generation.json`             | Authoritative published committed generation               |
| `lock.json`                   | `lionscliapp` locking coordination                         |
| `entities/`                   | Initial authoritative entity datastore                     |
| `link-cache/`                 | Derived, rebuildable lookup of link entities by endpoint   |
| `journal/pending/`            | Complete transactions awaiting application or finalization |
| `journal/committed/`          | Ordered committed transaction history                      |
| `journal/checkpoints/`        | Durable recovery-boundary records                          |
| `snapshots/`                  | Entity-store snapshots with embedded manifests             |
| `inbox/`                      | Public FileTalk request-entry surface                      |
| `inbox-processing/claimed/`   | Requests owned by Subete                                   |
| `inbox-processing/completed/` | Successfully completed requests                            |
| `inbox-processing/failed/`    | Rejected or failed requests                                |
| `status/`                     | Public derived operational information                     |
| `tmp/`                        | Non-authoritative temporary workspace                      |

## Layout Evolution

The initial filesystem layout is deliberately uncomplicated.

Future changes may introduce:

* sharding beneath `entities/`;
* authoritative SQLite stores for selected aspects;
* derived search indexes;
* cache files or cache metadata;
* journal compaction;
* alternate snapshot packaging;
* additional status or maintenance surfaces.

Such changes may alter physical organization, but they must preserve the system invariants, public request semantics, committed generations, journal ordering, recovery behavior, and the existence of one authoritative current value for each entity aspect.
