# Subete — Snapshot and Checkpoint Lifecycle

This document defines how Subete creates, validates, retains, and restores snapshots and checkpoints.

Snapshots and checkpoints are separate artifacts with separate purposes:

* a **snapshot** is a complete recoverable capture of authoritative database state at one committed generation;
* a **checkpoint** is a small recovery marker designating a validated snapshot as an accepted recovery base and identifying where journal replay begins.

A snapshot may exist without a checkpoint.

A checkpoint must refer to an existing validated snapshot.

---

# Purpose

The journal provides transaction-by-transaction durability and recovery.

Snapshots provide occasional full recovery bases so that Subete does not need to reconstruct the database by replaying its complete journal history from the beginning.

Checkpoints identify which snapshot Subete may trust as a recovery base and which later journal entries remain necessary for replay.

Creating a snapshot or checkpoint does not:

* modify the M1 world;
* advance the database generation;
* create a database transaction;
* replace the current authoritative datastore.

---

# Generations

Every snapshot represents exactly one committed database generation.

The snapshot generation identifies the complete authoritative world captured by the snapshot.

Every authoritative storage mechanism included in the snapshot must represent that same generation.

A snapshot must not combine:

* stores from different generations;
* partially applied transaction state;
* pending transaction after-states;
* speculative or temporary state.

A checkpoint normally uses the same generation as its referenced snapshot.

---

# When Snapshots Are Created

Snapshots are created by explicit command or operational policy.

Possible triggers include:

* a manual request;
* a periodic schedule;
* a configured number of committed transactions since the previous snapshot;
* journal growth beyond a configured threshold;
* preparation for software upgrades or storage migrations;
* preparation for risky maintenance;
* creation of a durable archival recovery point.

Snapshots are not created after every transaction.

The journal remains responsible for ordinary transaction durability between snapshots.

---

# Snapshot Creation Preconditions

Before snapshot creation begins:

1. Subete must have exclusive authority appropriate to snapshot creation.
2. The target generation must be fully committed.
3. No partially applied transaction may be exposed as the target generation.
4. Every authoritative storage mechanism required to reconstruct that generation must be available.
5. Subete must be able to obtain one coherent view of those stores.

Snapshot creation may occur while Subete is otherwise running only if the implementation can guarantee a consistent capture at one committed generation.

Otherwise, transaction processing must pause for the period needed to capture that consistent state.

---

# Snapshot Creation

A normal snapshot creation proceeds as follows:

1. Select the current committed generation to capture.
2. Establish a consistent view of every authoritative storage mechanism at that generation.
3. Create a temporary snapshot workspace.
4. Copy or export every authoritative store required for recovery.
5. Include `identity.json`.
6. Include or account for operational configuration according to snapshot policy.
7. Create `snapshot-manifest.json`.
8. Record the database identity, generation, creation time, contents, and available integrity information.
9. Package the snapshot as a directory or archive.
10. Complete and close the snapshot artifact.
11. Validate the completed artifact.
12. Move or publish it under its final snapshot filename.

The snapshot must not appear as a completed recovery artifact until all required contents and its manifest are complete.

An incomplete snapshot workspace is not a valid snapshot and must not be referenced by a checkpoint.

---

# Snapshot Validation

Before a snapshot may be accepted as a recovery base, Subete validates at least:

* the snapshot manifest;
* database identity;
* captured generation;
* inclusion of every required authoritative store;
* agreement among all included stores about the captured world;
* required file presence;
* archive readability;
* any required checksums or integrity records.

Validation may become more extensive over time.

A snapshot that cannot be validated remains an untrusted artifact. It may be retained for investigation, but no checkpoint may designate it as a recovery base.

---

# Checkpoint Creation

After a snapshot has been completed and validated, Subete may establish a checkpoint referring to it.

A normal checkpoint creation proceeds as follows:

1. Select the validated snapshot.
2. Confirm its database identity.
3. Confirm its committed generation.
4. Confirm that the snapshot remains available.
5. Determine the final journal sequence already represented by the snapshot.
6. Write a new checkpoint file.
7. Validate that the checkpoint and snapshot agree.
8. Publish the completed checkpoint in `journal/checkpoints/`.

The checkpoint records:

* the database identity;
* the accepted snapshot;
* the snapshot generation;
* the journal sequence through which that snapshot represents state;
* the sequence after which journal replay begins.

Normally:

```text
checkpoint generation = snapshot generation
replay-after = snapshot generation
```

---

# Advancing the Checkpoint

A checkpoint advances when a newer validated snapshot is accepted as a recovery base.

Advancing the checkpoint creates a new checkpoint file.

An existing checkpoint is not edited in place.

The newer checkpoint does not invalidate or erase older checkpoints automatically. Older checkpoints and snapshots may be retained as fallback recovery points.

A checkpoint may advance only after its referenced snapshot is complete, available, and validated.

Subete must never advance the recovery boundary merely because a snapshot was requested or began construction.

---

# Multiple Snapshots and Checkpoints

Subete may retain multiple snapshots and checkpoints.

This provides:

* fallback recovery points;
* historical archives;
* protection from unnoticed corruption in a newer snapshot;
* recovery choices during maintenance.

The highest-generation checkpoint is preferred only when:

* its checkpoint file is valid;
* its referenced snapshot is present;
* the snapshot is valid;
* all journal entries required after it are available;
* the complete recovery chain is internally consistent.

If the newest checkpoint is unusable, Subete may fall back to an older valid checkpoint and replay a longer journal range.

---

# Journal Records Required for Recovery

Without a checkpoint, recovery may require journal history from the beginning of the retained database history or from another independently established recovery base.

For a checkpoint whose `replay-after` value is generation `N`, recovery requires:

* the checkpoint;
* its referenced snapshot;
* every committed journal entry after `N` through the target generation;
* any pending journal entry that follows the committed range and requires completion.

Committed journal entries through `N` are already represented by the checkpointed snapshot and are not required for forward replay from that snapshot.

They may still be retained for:

* auditing;
* historical inspection;
* alternate reconstruction;
* diagnostics;
* long-term archives.

A checkpoint makes older journal entries unnecessary for that recovery path; it does not delete them.

---

# Journal Retention and Removal

Journal retention is a separate maintenance policy.

Committed journal entries at or before a checkpoint boundary may be archived, compacted, or removed only after Subete has established that:

1. the checkpoint is valid;
2. the referenced snapshot is valid;
3. the snapshot contains every required authoritative store;
4. at least one complete recovery path remains;
5. any configured redundancy or retention requirements are satisfied.

Pending journal entries must never be removed merely because a newer checkpoint exists.

A pending entry represents an unresolved transaction obligation and must be recovered according to `state.md`.

Subete should prefer conservative retention over prematurely removing the only available recovery history.

---

# Restoration

Restoration is an explicit operation.

A normal restoration proceeds as follows:

1. Select the highest suitable valid checkpoint, or an explicitly requested checkpoint.
2. Read and validate the checkpoint.
3. Locate and validate its referenced snapshot.
4. Confirm database identity and restoration policy.
5. place the current datastore into a safe maintenance state.
6. Restore every authoritative storage mechanism from the snapshot.
7. Establish the snapshot generation as the restoration base.
8. Identify committed journal entries whose sequence is greater than `replay-after`.
9. Replay those entries in ascending sequence order.
10. Resolve any pending transaction after the committed sequence.
11. Rebuild or reconcile required derived structures.
12. verify the resulting authoritative world and generation.
13. Publish status and resume ordinary service.

Ordinary reads, searches, and transactions must not observe an incomplete restoration.

---

# Journal Replay

Journal replay applies committed transaction after-states in ascending sequence order.

For each replayed journal entry, Subete:

1. validates the entry and database identity;
2. confirms that its sequence is the next expected sequence;
3. compares affected state with the journaled before-state and after-state;
4. applies any remaining transition to the after-state;
5. confirms that every affected authoritative store matches the after-state;
6. reconciles required derived structures;
7. advances the restored generation to that journal sequence.

Replay must be idempotent.

If affected state already matches the journaled after-state, replay recognizes that portion as applied.

If affected state matches the before-state, replay applies the transition.

If state matches neither, restoration enters a recovery-error state rather than guessing.

---

# Pending Transactions During Restoration

A snapshot contains committed state only.

It must not contain a partially applied pending transaction.

After replaying the complete committed journal range, Subete may find a pending journal entry representing the next sequence.

That entry is handled according to the transaction recovery state machine:

* if affected state matches before, apply after;
* if some state already matches after, complete the remaining application;
* if all affected state matches after, finalize commitment;
* if state matches neither, enter recovery error.

The pending transaction is not ignored or rolled back merely because restoration began from a snapshot.

---

# Derived Structures

Derived structures such as search indexes and the link cache may be included in a snapshot, but authoritative recovery must not depend on them unless a separate specification explicitly makes that necessary.

After restoration:

* a derived structure matching the restored generation may be accepted after validation;
* a stale derived structure must be updated or rebuilt;
* an absent derived structure may be rebuilt from authoritative state;
* a derived structure must not claim a generation newer than the authoritative world.

The Version 1 link cache must satisfy its own readiness rules before normal link service resumes.

---

# Snapshot and Checkpoint Failure

## Incomplete Snapshot

An interrupted snapshot construction is not a valid snapshot.

It may be deleted or retained for diagnostics, but no checkpoint may refer to it.

## Snapshot Completed, Checkpoint Not Written

The snapshot remains a valid standalone artifact if it passes validation.

It has not yet been designated as an accepted checkpoint recovery base.

A checkpoint may be created for it later.

## Checkpoint Write Interrupted

An incomplete checkpoint file is not valid and must not advance the recovery boundary.

The previously valid checkpoint remains in effect.

## Checkpoint Exists, Snapshot Missing

The checkpoint is unusable.

Subete may select an older valid checkpoint or require operator intervention.

## Snapshot or Checkpoint Mismatch

If database identity, generation, filename, manifest, or replay boundary disagree, Subete must not silently trust the pair.

It must reject that recovery path and seek another valid one.

---

# Deletion of Snapshots and Checkpoints

Deleting a snapshot or checkpoint does not alter the current authoritative M1 world.

However, deletion may destroy a recovery path.

A snapshot referenced by a retained checkpoint must not be deleted unless:

* that checkpoint is also retired;
* another sufficient recovery path exists;
* retention policy permits the removal.

A checkpoint may be removed without changing database state, but the referenced snapshot then loses that particular designation as a trusted recovery base.

Maintenance commands should make the recovery consequences of deletion explicit.

---

# Lifecycle Summary

```text
committed generation N
        ↓
create complete snapshot of N
        ↓
validate snapshot
        ↓
write checkpoint for snapshot N
        ↓
continue committing N+1, N+2, ...
        ↓
retain later journal entries for replay
        ↓
eventually create and validate snapshot M
        ↓
write new checkpoint for M
```

Recovery from checkpoint `M` becomes:

```text
restore snapshot M
        ↓
replay committed journal entries after M
        ↓
recover any pending next transaction
        ↓
rebuild required derived structures
        ↓
resume service
```

---

# Non-Negotiable Rules

* A snapshot is a full recoverable capture of authoritative state at one committed generation.
* A checkpoint is a small recovery marker and does not contain the world.
* A checkpoint may refer only to a completed and validated snapshot.
* Snapshot creation and checkpoint creation do not advance database generation.
* Snapshots contain committed state only.
* Every authoritative storage mechanism required for recovery must be represented.
* Journal entries after the checkpoint boundary remain necessary for forward replay.
* Older journal entries do not become deletable until a sufficient recovery path is established.
* Existing checkpoints are not edited in place; a newer recovery boundary receives a new checkpoint.
* Restoration replays journals in sequence order.
* A pending transaction remains a recovery obligation after restoration.
* Missing or inconsistent recovery artifacts are rejected rather than silently trusted.
