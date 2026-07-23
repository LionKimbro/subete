# Subete — System Invariants

This document defines the non-negotiable rules of Subete.

These are not implementation suggestions. They are conditions that must remain true across normal operation, failure, recovery, maintenance, and future optimization.

## 1. One Authoritative World

Subete maintains one current authoritative world of M1 entities and aspects.

It does not resolve competing document layers, overlays, or priority orders. At any committed generation, there is one authoritative state for each entity and aspect known to Subete.

## 2. Authoritative Entity State

The committed entity datastore is authoritative.

The datastore is logical and may be implemented using more than one physical storage mechanism. Different aspects may use different authoritative backing stores.

The logical contents of the committed entities and aspects, taken together across those stores, define the current Subete world.

No entity or aspect has more than one authoritative current value at a committed generation.

Status files, derived indexes, caches, snapshots, checkpoints, metrics, and journal records do not independently define current entity state.

## 3. Single Writer Authority

Only the running authoritative Subete writer may mutate the entity datastore, journal, generation state, checkpoints, or other internal state that participates in transaction durability.

External programs must not directly edit authoritative Subete storage.

They submit requests through the supported FileTalk interface.

Read-only tools may inspect permitted surfaces when doing so cannot mutate or misrepresent authoritative state.

## 4. Complete Journal Before Mutation

A complete write-ahead journal entry must exist before any authoritative datastore mutation for that transaction begins.

The journal entry must contain enough information to determine:

* the transaction being applied;
* the affected entities;
* the relevant state before the transaction;
* the intended state after the transaction;
* the assigned journal sequence.

An incomplete journal write grants no permission to alter the datastore.

## 5. Transactions Reach One Complete Outcome

A transaction is atomic at the logical level.

Its complete intended after-state must become authoritative, or no part of that transaction may remain as the accepted committed outcome.

If the process stops after only part of a journaled transaction has been applied, recovery must continue applying that same transaction until its complete intended after-state is reached.

Partial application is a recoverable intermediate state, not a committed database state.

## 6. Transaction Application Is Recoverable

Applying a complete journal entry must be safe to resume after interruption.

During recovery, affected entity state may be compared against the journaled before-state and after-state:

* state matching the after-state is already applied;
* state matching the before-state still requires application;
* state matching neither indicates an inconsistency requiring explicit handling.

Reapplying an already applied part of a transaction must not produce a different result.

## 7. Committed State Only

Reads and searches observe committed state only.

They must not expose:

* partially written journal records;
* transaction planning state;
* temporary files;
* partially applied transactions;
* speculative or dirty in-memory values.

If a transaction is undergoing recovery, Subete must not present its partial physical application as a valid committed world.

## 8. Journal Sequence and Generation

Every transaction accepted as committed receives one monotonically increasing journal sequence number.

The database generation is the journal sequence number of the latest committed transaction.

The two values use the same numbering system.

A transaction does not advance the database generation until its complete intended after-state has become authoritative.

## 9. Generations Identify Committed Worlds

A generation identifies a specific committed state of the Subete world.

Reads, searches, transaction responses, snapshots, checkpoints, status surfaces, indexes, and caches may state the generation they reflect.

No derived structure may claim to represent a generation newer than the authoritative committed state from which it was produced.

## 10. Derived Structures Are Not Authoritative

Search indexes, link indexes, status surfaces, metrics, and other structures derived solely for acceleration or presentation are not authoritative.

An authoritative aspect-storage mechanism does not become derived merely because it also supports efficient searches or indexes its own authoritative contents.

Derived structures must be rebuildable from authoritative entity state without requiring themselves as input.

Deleting a derived index may reduce performance, but must not destroy authoritative information.

Deleting or losing an authoritative aspect store is loss of authoritative information unless that store is restored through the defined recovery process.

If a derived structure is stale, its recorded generation must reveal that staleness.

## 11. Cache Mirrors Durable State

When caching is introduced, cached entity state must reflect committed authoritative state already represented in durable storage.

Dirty, speculative, planned, or partially applied transaction state must never be placed into the shared entity cache.

Transaction computation may use temporary working memory, but that working state is not cache state.

The cache must be safely discardable and reconstructable from authoritative storage.

## 12. Snapshots Preserve; They Do Not Govern

A snapshot preserves a complete recoverable representation of authoritative state at an identified generation, including every authoritative aspect-storage mechanism required to reconstruct that state.

A snapshot does not become the current authoritative world merely by existing.

Restoring a snapshot is an explicit operation that re-establishes a database state and then performs any required journal replay.

## 13. Checkpoints Mark Recovery Boundaries

A checkpoint is a small durable statement describing an accepted recovery boundary.

It identifies the state from which recovery may safely begin and how later journal entries relate to that state.

A checkpoint is distinct from a snapshot and does not contain the full entity world.

## 14. Status Is Descriptive

The public status surface is descriptive and read-only.

It may report process state, current generation, counts, recovery activity, heartbeat, and freshness of derived services.

Status data must not be treated as authoritative entity data or as a substitute for transaction, journal, checkpoint, or generation state.

## 15. Requests Must Be Safely Retriable

The system must account for duplicate delivery and uncertain response delivery.

A caller may retry a request when it cannot determine whether the prior attempt completed.

Subete must use request identity and recorded transaction history to avoid unintentionally applying the same logical transaction more than once.

## 16. Recovery Precedes Normal Service

On startup, Subete must inspect and resolve recoverable incomplete work across all authoritative storage mechanisms before presenting itself as ready for ordinary requests.

The database must not claim a committed generation while any authoritative store remains only partially reconciled with the journal history establishing that generation.

## 17. Optimization Must Preserve Meaning

Caching, indexing, sharding, alternate aspect-storage mechanisms, compaction, and other future optimizations must not change the external meaning of transactions, reads, searches, generations, journaling, snapshots, checkpoints, or recovery.

An optimization may change how Subete performs an operation.

It must not change what authoritative result the operation means.
