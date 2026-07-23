# Subete — Transaction and Recovery State Machine

This document defines the lifecycle of FileTalk requests and transactions in Subete.

It describes:

* normal request processing;
* transaction state transitions;
* durable boundaries;
* failure handling;
* startup recovery.

The filesystem locations and JSON formats referenced here are defined in the corresponding documents under `docs/code/` and `docs/code/formats/`.

---

# Core Principle

A transaction passes through two fundamentally different regions:

## Before the Journal Is Complete

The transaction may be parsed, validated, and planned, but it has no permission to alter authoritative state.

Failure in this region may cause the request to be retried or failed.

## After the Journal Is Complete

The transaction has a durable intended after-state.

From this point onward, Subete must complete that transaction. It must not abandon it merely because the process stopped, response delivery failed, or application was interrupted.

The complete pending journal entry is the durable boundary between:

```text
request processing
```

and:

```text
transaction recovery obligation
```

---

# Request Lifecycle Overview

```text
inbox request discovered
        ↓
request claimed
        ↓
request validated
        ↓
transaction planned
        ↓
journal write started
        ↓
journal complete
        ↓
authoritative mutation in progress
        ↓
authoritative mutation complete
        ↓
journal committed
        ↓
generation publication attempted
        ↓
cache-current publication attempted
        ↓
response delivery attempted
        ↓
request completed
```

A request may fail before the journal becomes complete.

After the journal becomes complete, an interrupted transaction is recovered to completion rather than failed or rolled back.

---

# 1. Inbox Request Discovered

A file is visible directly beneath:

```text
inbox/
```

At this point, Subete does not yet assume that the file contains a complete message.

## Possible Conditions

The file may be:

* actively being written;
* complete valid JSON;
* complete invalid JSON;
* stale and incomplete;
* inaccessible;
* a duplicate delivery.

## Behavior

Subete attempts to read one complete JSON object.

If the file is incomplete or temporarily unreadable, Subete leaves it in `inbox/` and retries during a later polling cycle according to `filetalk-protocol.md`.

If the file is a complete JSON object, it is eligible to be claimed.

## Durable Meaning

Discovery alone establishes no ownership and no transaction state.

## Startup Behavior

Files found in `inbox/` after startup are treated as ordinary candidate requests.

---

# 2. Request Claimed

Subete claims the complete message file by moving it from:

```text
inbox/
```

to:

```text
inbox-processing/claimed/
```

The claimed file retains its original contents.

## Meaning

Claiming establishes that the running Subete process owns processing of that message.

The request has not yet been accepted as valid.

No transaction journal sequence has been assigned.

No authoritative state may have changed.

## Failure Before Claim Completes

If the move does not complete, the file remains in `inbox/` and may be discovered again.

If the claim operation leaves ambiguous filesystem state, Subete must determine whether the file exists in `inbox/`, `claimed/`, or both before processing it.

It must not execute two copies of the same logical request independently.

## Startup Behavior

Every file found in `inbox-processing/claimed/` is an interrupted request-processing candidate.

Subete reads the request identity and determines whether:

* the request has no journal entry and should resume validation;
* a pending journal entry already exists and transaction recovery governs;
* a committed journal entry already exists and the transaction request must not execute again;
* a prior completed or failed outcome already exists.

---

# 3. Request Validated

Subete validates:

* the FileTalk message structure;
* request identity;
* request type;
* reply destination;
* request-family body;
* duplicate-request consistency;
* transaction operation structure;
* entity and aspect identifiers;
* revision preconditions;
* operation conflicts;
* applicable aspect-specific rules.

For reads and searches, validation is followed directly by execution against committed state.

For transactions, validation precedes planning.

## Successful Validation

The request is structurally and semantically eligible to continue.

## Validation Failure

Before a complete journal entry exists:

1. no authoritative mutation occurs;
2. the request is recorded as failed;
3. an error response is prepared;
4. response delivery is attempted;
5. the request moves from `claimed/` to `failed/`.

A failed validation does not advance the database generation.

## Startup Behavior

A claimed request with no corresponding journal entry may be validated again.

Validation is safe to repeat because it does not modify authoritative entity state.

---

# 4. Transaction Planned

Subete computes the transaction’s complete intended logical effect.

Planning includes:

* reading every affected entity from all applicable authoritative stores;
* confirming each current revision;
* constructing the complete before-state of each affected entity;
* computing the complete intended after-state;
* assigning resulting entity revisions;
* determining required changes to authoritative storage mechanisms;
* determining required changes to the link cache and other current derived services;
* constructing the future transaction response.

Planning occurs in temporary working memory.

Planned state is not authoritative state and is not cache state.

## Successful Planning

The transaction has a complete, internally consistent before-and-after description.

## Planning Failure

If planning discovers a conflict, invalid authoritative value, failed precondition, unsupported storage condition, or other error before journal completion:

1. no authoritative mutation occurs;
2. no journal sequence is committed;
3. the request is failed;
4. an error response is attempted;
5. the request moves to `failed/`.

## Startup Behavior

Planning state exists only in memory and is lost on process termination.

A claimed request with no complete pending journal entry is simply validated and planned again.

---

# 5. Journal Write Started

Subete allocates the next available journal sequence and begins writing the journal entry beneath:

```text
tmp/
```

The temporary journal file contains:

* database identity;
* journal sequence;
* originating transaction request;
* complete affected entity before-states;
* complete intended after-states;
* required transaction metadata.

## Meaning

The journal file is under construction.

It is not yet a complete journal entry.

It does not authorize authoritative mutation.

## Failure During Journal Writing

If writing, flushing, or closing the file fails:

* no authoritative datastore mutation may have begun;
* the incomplete temporary journal file may be deleted;
* the request may be retried from validation and planning;
* the allocated sequence may be reused if it was never established as a complete pending journal entry.

No generation is advanced.

## Startup Behavior

An incomplete journal file found in `tmp/` is not a pending transaction.

Subete may delete or quarantine it after determining that no active process owns it.

The associated claimed request may then be processed again.

---

# 6. Journal Complete

The complete journal file has been:

1. fully written;
2. flushed as required by durability policy;
3. closed;
4. placed in:

```text
journal/pending/
```

At this point, the journal entry is immutable.

## Meaning

The transaction is now durably defined.

The pending journal entry authorizes authoritative mutation.

Subete is obligated to bring every affected authoritative store to the journaled after-state.

The request may no longer be treated as an ordinary validation or execution failure.

## Sequence Meaning

The journal sequence is reserved for this transaction.

The database generation has not yet advanced to that sequence.

## Failure Immediately After Journal Completion

If Subete stops before changing any authoritative data, startup recovery finds the pending journal entry and applies its complete after-state.

## Startup Behavior

Every complete journal entry in `journal/pending/` must be recovered before Subete presents ordinary service as ready.

---

# 7. Authoritative Mutation in Progress

Subete applies the journaled after-state across every affected authoritative storage mechanism.

This may include:

* creating, replacing, or deleting entity files;
* updating authoritative SQLite-backed aspects in a future hybrid-storage extension;
* changing other authoritative aspect stores;
* updating entity revision metadata;
* reconciling the Version 1 link cache.

The order of physical writes does not define the transaction’s logical meaning.

## Intermediate Physical State

During this phase:

* some affected stores may already match the after-state;
* others may still match the before-state;
* the physical datastore may temporarily contain a mixture.

This mixture is not a committed Subete world.

Reads and searches must not expose it as valid committed state.

Because Subete uses one authoritative writer, ordinary request processing does not proceed while such an incomplete transaction is being applied or recovered.

## Failure During Mutation

The pending journal entry remains sufficient to recover.

On restart, Subete compares every affected logical entity or authoritative component with the journal:

* matching `after` means that part is already applied;
* matching `before` means that part still requires application;
* matching neither indicates an unexpected inconsistency.

Recovery applies every remaining before-state component to its intended after-state.

## Idempotence

Writing an already established after-state again must not produce a different logical result.

---

# 8. Authoritative Mutation Complete

Every affected authoritative storage mechanism now matches the journaled intended after-state.

Every created or changed entity has its intended resulting revision.

Every deleted entity is absent from all authoritative stores.

Required derived cache-entry changes have been prepared. For the Version 1 link cache, `link-cache/generation.json` remains at the last committed generation with `state = updating` and a target generation equal to the pending journal sequence.

## Meaning

The logical transaction result has been fully established in durable storage.

The journal entry may now be committed.

## Failure Before Journal Commitment

If Subete stops after all authoritative changes are complete but while the journal entry remains in `pending/`, startup recovery compares the datastore with the journal, finds every affected state already matching `after`, and proceeds to finalize the commit.

The transaction is not applied a second time in a way that changes its result.

---

# 9. Journal Committed

The journal entry moves from:

```text
journal/pending/
```

to:

```text
journal/committed/
```

After the move, Subete publishes `generation.json` with the journal sequence as both `generation` and `journal-sequence`. The database generation becomes that sequence only when this authoritative generation record is published.

## Meaning

The journal has committed the transaction's after-state. `generation.json` publication completes the durable publication of the resulting current generation.

Its complete intended after-state is the current authoritative world.

The transaction must never be executed again under the same request identity.

A committed transaction remains committed even if:

* response construction fails;
* response delivery fails;
* request archival fails;
* the process stops immediately afterward.

## Generation Publication

The journal move and replacement of `generation.json` cannot be one filesystem-atomic operation. A process may therefore stop after the entry is in `journal/committed/` while `generation.json` still names the preceding generation.

On startup, Subete validates that committed entry and the authoritative after-state, then publishes the missing generation record. It must not execute or plan the transaction again. The exact accepted and suspicious combinations are defined in `formats/generation.md`.

## Cache-Current Publication

After journal commitment establishes the new database generation, Subete publishes required derived services as current for that generation. For the Version 1 link cache, this replaces the `updating` record with `state = current` and the newly committed generation.

There may be a short post-commit interval in which the database is at generation `N + 1` while the cache remains:

```text
state = updating
generation = N
target-generation = N + 1
```

This state is not an error and must not be presented as current cache information. If the process stops in this interval, startup recovery completes cache-current publication before announcing ordinary service as ready.

## Commit Ordering

Committed journal entries and generations advance in journal sequence order.

Subete must not expose generation `N + 1` as committed while generation `N` remains an unresolved pending transaction.

## Failure During Journal Move

If process interruption leaves ambiguity about whether the entry resides in `pending/`, `committed/`, or both, recovery determines:

* whether the authoritative datastore matches the after-state;
* whether the sequence is already recognized as committed;
* whether duplicate journal files are byte-identical.

A single logical journal entry must result.

The transaction must not be applied as a second transaction.

## Startup Behavior

Committed entries require no entity mutation during ordinary recovery unless replaying from a snapshot or checkpoint.

A claimed request whose request ID already appears in committed journal history is recognized as already completed logically.

---

# 10. Response Delivery Attempted

Subete constructs the recorded logical reply and writes it to the request’s SASE destination.

For a transaction, the response includes the committed generation and resulting entity revisions where applicable.

## Delivery Success

The complete response is written to the destination.

The request may proceed to completed archival.

## Delivery Failure

The transaction remains committed.

Subete records the reply-delivery failure according to the FileTalk protocol and retains enough information to reproduce or redeliver the original logical response.

The transaction must not be re-executed.

## Startup Behavior

A committed journal entry paired with a request still in `claimed/` indicates that logical processing completed but post-commit handling may have been interrupted.

Subete reconstructs or retrieves the original response and may retry delivery according to policy.

---

# 11. Response Delivered

The response has been successfully written to the SASE destination.

## Meaning

The caller has been given a reply artifact.

This does not prove that the caller has read or acknowledged it.

Subete does not require recipient acknowledgment for the request to be considered processed.

## Failure After Delivery

If Subete stops after writing the response but before archiving the request, startup recovery may attempt delivery again.

The recipient must therefore tolerate replacement or repeated delivery of the same logical response.

A transaction request must not be executed again. An unfinished read or search may be rerun under the sequential-recovery rule, and a later completed read or search delivery may execute again as a new non-mutating observation.

---

# 12. Request Completed

After successful logical processing and any required reply handling, the claimed request moves to:

```text
inbox-processing/completed/
```

The completed record supports:

* auditing;
* duplicate-request recognition;
* operational inspection.

For transactions, the committed journal supplies the durable logical outcome needed for response reconstruction. Version 1 does not require completed read or search records to retain a replayable result.

## Meaning

The FileTalk request lifecycle is complete.

For transactions, commitment occurred earlier at journal commitment.

Moving the request to `completed/` does not alter entity state or advance the generation.

## Startup Behavior

A completed transaction request must not execute again. A completed read or search request may execute again when its request-family protocol permits a repeated non-mutating observation.

A repeated inbox delivery with the same request ID is handled under its request-family protocol. Only transaction commitment requires a durable outcome that can be reconstructed after archival; an identical completed read or search may execute again as a new non-mutating observation of the current committed generation.

---

# 13. Request Failed

A request may move to:

```text
inbox-processing/failed/
```

only when it fails before a complete pending journal entry establishes a recovery obligation, or when the message is invalid at the FileTalk or request-protocol level.

Examples include:

* malformed completed JSON;
* unsupported request type;
* invalid reply destination;
* invalid operation;
* entity revision conflict;
* conflicting transaction operations;
* invalid search predicate;
* invalid read selector.

## Meaning

No authoritative transaction from that request was committed.

The failure record should preserve:

* the original request;
* the error code;
* a human-readable explanation;
* relevant operation or search indexes;
* the generation observed when failure was determined;
* reply-delivery outcome when applicable.

## Prohibited Failure Transition

A transaction with a complete entry in `journal/pending/` must not be moved to ordinary request failure merely because transaction application was interrupted.

It is a recovery obligation and must be completed or placed into an explicit database recovery-error state.

---

# Read and Search Requests

Read and search requests use a shorter lifecycle:

```text
discovered
    ↓
claimed
    ↓
validated
    ↓
executed against one committed generation
    ↓
response delivery attempted
    ↓
completed or failed
```

They do not:

* allocate a journal sequence;
* create a pending journal entry;
* advance database generation;
* mutate authoritative state.

Subete processes only one request at a time. While a read or search is executing or its reply is being delivered, no other request may mutate the database. Therefore, if the process stops before the request is completed, recovery discards any incomplete temporary response file, retains the claimed request, and reruns the read or search against the unchanged committed generation. It then publishes the completed response according to `filetalk-protocol.md`, using atomic replacement when it is available and the protocol's tolerant direct-write delivery otherwise, and archives the request normally.

This recovery rule does not require a durable read or search outcome record. It applies only to an unfinished claimed request; an identical request already archived as completed may execute again as a new non-mutating observation under its request-family protocol.

---

# Startup Recovery Order

Before Subete announces `ready`, it performs recovery in this order.

## 1. Establish Exclusive Writer Authority

Acquire the required `lionscliapp` writer lock.

No recovery mutation may begin without writer authority.

## 2. Validate Database Identity and Core Layout

Read `identity.json`, configuration, `generation.json`, and required storage locations. Confirm that the generation record identifies this database.

Do not proceed against an ambiguous or mismatched database identity.

## 3. Inspect Journal State

Enumerate:

* temporary journal files;
* pending journal entries;
* committed journal entries;
* the authoritative published generation record;
* sequence consistency;
* duplicate or conflicting files.

Incomplete temporary journal files do not authorize mutation.

Complete pending entries do.

## 4. Recover Pending Transactions in Sequence Order

For each pending journal entry, beginning with the lowest sequence:

1. validate the journal entry;
2. confirm database identity;
3. inspect every affected authoritative store;
4. compare current state with before and after states;
5. apply every remaining transition to after-state;
6. prepare required derived cache entries and record their pending target generation;
7. move the journal entry to `committed/`;
8. publish `generation.json` at the entry sequence;
9. publish required derived services as current for the committed generation.

Normal request service remains unavailable until all recoverable pending transactions are resolved.

## 5. Reconcile Generation State

`generation.json` is the authoritative recognized database generation. It must equal the highest contiguous committed journal sequence represented by the current authoritative state, except where older committed entries were deliberately compacted behind a valid checkpoint and snapshot chain.

A committed journal entry newer than `generation.json` requires validated generation publication. A pending entry newer than `generation.json` requires ordinary pending-transaction recovery. A gap, conflict, impossible journal/generation combination, or insufficient compacted recovery chain causes recovery error rather than guessed advancement.

## 6. Inspect Claimed Requests

For each file in `inbox-processing/claimed/`:

* if its transaction is committed, reconstruct or redeliver the result and complete the request;
* if its transaction is pending, associate it with journal recovery;
* if it has no journal entry, resume validation and processing;
* if it already has a completed or failed record, resolve the duplicate without execution.

## 7. Inspect Required Derived Services

Confirm that the link cache and any other service required for normal committed-world behavior reflect the current generation.

Rebuild or reconcile them before announcing `ready`, unless the governing service specification explicitly permits operation without them.

## 8. Publish Ready State

Only after recovery obligations are resolved may Subete publish:

```json
{
  "state": "ready"
}
```

---

# Recovery Error State

Subete enters a recovery-error state when it cannot safely determine or establish the intended committed world.

Examples include:

* an affected entity matches neither journaled before-state nor after-state;
* a journal entry is internally inconsistent;
* two different transactions claim the same sequence;
* committed journal history contains an unexplained gap;
* database identity does not match;
* an authoritative store is unavailable;
* required after-state cannot be written;
* a derived service required for generation visibility cannot be reconciled.

In recovery error:

* Subete must not announce `ready`;
* ordinary transaction, read, and search service must not proceed;
* status should describe the failure;
* recovery artifacts must be preserved;
* Subete must not silently discard or rewrite journal history to make the error disappear.

Explicit maintenance or operator intervention may be required.

---

# State Summary

| State                                    | Durable transaction obligation? | Authoritative mutation allowed? | Generation advanced? |
| ---------------------------------------- | ------------------------------- | ------------------------------- | -------------------- |
| Inbox request discovered                 | No                              | No                              | No                   |
| Request claimed                          | No                              | No                              | No                   |
| Request validated                        | No                              | No                              | No                   |
| Transaction planned                      | No                              | No                              | No                   |
| Journal write started in `tmp/`          | No                              | No                              | No                   |
| Complete journal in `pending/`           | Yes                             | Yes                             | No                   |
| Mutation in progress                     | Yes                             | In progress                     | No                   |
| Mutation complete                        | Yes                             | Complete                        | No                   |
| Journal committed                        | Completed                       | Complete                        | Yes                  |
| Response delivered                       | Completed                       | Complete                        | Yes                  |
| Request completed                        | Completed                       | Complete                        | Yes                  |
| Request failed before journal completion | No                              | No                              | No                   |

---

# Non-Negotiable Transition Rules

* No authoritative mutation occurs before a complete journal entry exists in `journal/pending/`.
* Once a complete pending journal entry exists, Subete must recover that transaction to its intended after-state.
* A partial physical transaction state is never exposed as a committed world.
* The generation advances only after authoritative mutation is complete, the journal entry is in `committed/`, and `generation.json` is published at that sequence.
* Reply failure never reverses a committed transaction.
* Request archival never determines transaction commitment.
* Startup recovery completes before normal service begins.
* Recovery follows recorded before-and-after state; it does not infer a new transaction meaning.
* One request ID produces at most one logical transaction execution.
* One journal sequence identifies at most one transaction.
