# Subete — Failure-Injection Test Matrix

This document defines deliberate crash tests for the Subete transaction lifecycle.

Each test interrupts the service at one precise boundary, restarts it, and verifies that recovery produces the required result.

The purpose is to prove that:

* no transaction mutates authoritative state before its journal is complete;
* a completed pending journal always leads to completion of its intended after-state;
* partial application is repaired idempotently;
* journal commitment occurs only after application is complete;
* response failure never reverses commitment;
* request archival never determines commitment;
* startup returns the database to one coherent generation.

---

# Test Transaction

The matrix uses one representative multi-entity transaction.

The transaction changes three existing entities:

```text
Entity A
Entity B
Entity C
```

Before the transaction:

```text
database generation = N
```

The transaction receives:

```text
journal sequence = N + 1
```

Each entity has:

```text
before-state
after-state
```

The transaction may also require derived link-cache changes.

The same crash boundaries must later be tested with:

* entity creation;
* entity deletion;
* aspect creation;
* aspect deletion;
* link creation;
* link endpoint change;
* link deletion;
* mixed file and SQLite authoritative storage.

---

# Common Test Setup

Before each test:

1. restore the database to a known committed generation `N`;
2. verify that every affected entity matches its expected before-state;
3. verify that the link cache is current at generation `N`;
4. clear unrelated inbox, claimed, pending-journal, and response artifacts;
5. submit one transaction request;
6. enable the selected failure-injection point;
7. run the service until it terminates at that point;
8. inspect and record the filesystem before restart;
9. restart the service without failure injection;
10. verify the expected recovery result.

Each test begins from an independently restored fixture.

A later test must not depend on the side effects of an earlier test.

---

# Required Assertions

Every test should verify the applicable assertions below.

## Before-State Assertions

Before the injected crash:

* the database begins at generation `N`;
* the cache begins current at generation `N`;
* no journal sequence `N + 1` is committed;
* affected entities match their expected before-states.

## Post-Crash Inspection

Before restart, record:

* request location;
* temporary journal files;
* pending journal files;
* committed journal files;
* each affected entity’s current state;
* each authoritative backing store’s current state;
* link-cache entries;
* link-cache generation;
* response-file presence;
* published status;
* recognized database generation.

## Post-Recovery Assertions

After restart:

* the service reaches the expected operational state;
* no partial physical state is exposed as committed;
* every affected entity has the expected revision;
* the cache agrees with authoritative links;
* journal placement is correct;
* database generation is correct;
* the transaction executes at most once;
* the response represents the recorded logical outcome;
* the claimed request reaches the correct archival location.

---

# Failure-Injection Mechanism

Failure injection should terminate the process abruptly.

It should simulate loss of execution rather than orderly exception handling.

Suitable mechanisms include:

* immediate process exit;
* forced termination;
* test-only injected crash exception that bypasses normal cleanup;
* subprocess termination by the test harness.

Failure injection must not:

* run ordinary shutdown handlers;
* complete deferred writes after the selected boundary;
* archive the request automatically;
* release or rewrite transaction artifacts as though processing completed normally.

The test harness must distinguish:

```text
crash occurred at requested boundary
```

from:

```text
operation failed before reaching boundary
```

---

# Boundary 1 — Before Journal Creation

## Injection Point

Crash after request validation and transaction planning, but before any journal file is created.

Conceptually:

```text
transaction planned
        ↓
CRASH
        ↓
journal write not started
```

## Expected State Before Restart

```text
request:
    claimed

temporary journal:
    absent

pending journal:
    absent

committed journal N+1:
    absent

affected entities:
    all match before-state

link cache:
    current at generation N

database generation:
    N

response:
    absent
```

No authoritative mutation may have occurred.

## Expected Recovery Result

On restart:

1. Subete finds the claimed request.
2. It finds no pending or committed journal for the request.
3. It validates and plans the request again.
4. It creates a new complete journal entry.
5. It applies the transaction.
6. It commits sequence `N + 1`.
7. It delivers the success response.
8. It archives the request as completed.

## Final Expected State

```text
affected entities:
    all match after-state

pending journal:
    absent

committed journal:
    sequence N+1 present

link cache:
    current at generation N+1

database generation:
    N+1

request:
    completed

response:
    successful transaction response
```

The recomputed plan must produce the same logical transaction result.

---

# Boundary 2 — During Journal Writing

## Injection Point

Crash after a temporary journal file has begun writing but before the complete journal entry is placed in `journal/pending/`.

Conceptually:

```text
temporary journal write started
        ↓
partial bytes written
        ↓
CRASH
```

Several subcases should be tested:

* empty temporary file;
* partial JSON token;
* syntactically complete but not yet finalized file;
* complete temporary file not yet moved to `pending/`;
* file written but not durably flushed according to policy.

## Expected State Before Restart

```text
request:
    claimed

temporary journal:
    absent, partial, or unfinalized

pending journal:
    absent

committed journal N+1:
    absent

affected entities:
    all match before-state

link cache:
    current at generation N

database generation:
    N

response:
    absent
```

A temporary file does not authorize mutation.

## Expected Recovery Result

On restart:

1. Subete identifies the temporary journal artifact as incomplete or unpublished.
2. It does not apply state from that file.
3. It deletes, quarantines, or ignores the temporary artifact according to policy.
4. It resumes the claimed request from validation and planning.
5. It writes a new complete pending journal.
6. It completes and commits the transaction normally.

## Final Expected State

The final state is the same as Boundary 1.

The incomplete temporary journal must never appear in committed history.

---

# Boundary 3 — After Journal Completion

## Injection Point

Crash immediately after the complete immutable journal entry has entered `journal/pending/`, before authoritative mutation begins.

Conceptually:

```text
pending journal complete
        ↓
CRASH
        ↓
first entity write not started
```

## Expected State Before Restart

```text
request:
    claimed

temporary journal:
    absent or harmless leftover

pending journal:
    sequence N+1 present and complete

committed journal N+1:
    absent

affected entities:
    all match before-state

link cache:
    current at generation N

database generation:
    N

response:
    absent
```

The transaction is now a durable recovery obligation.

## Expected Recovery Result

On restart:

1. Subete validates the pending journal.
2. It compares all affected entities with the journal.
3. Every entity matches before-state.
4. It applies every after-state.
5. It applies or verifies all required cache changes.
6. It commits the journal.
7. It advances generation to `N + 1`.
8. It delivers the response.
9. It completes the claimed request.

## Final Expected State

```text
all entities:
    after-state

committed journal:
    sequence N+1

database generation:
    N+1
```

The request must not be replanned as a new transaction.

---

# Boundary 4 — Before the First Entity Write

## Injection Point

Crash after transaction application has begun logically, but immediately before the first authoritative entity or aspect-store write.

This boundary is distinct from journal completion because application setup may already have:

* loaded the journal;
* created temporary replacement files;
* selected physical write order;
* marked status as applying.

## Expected State Before Restart

```text
request:
    claimed

pending journal:
    sequence N+1 complete

affected entities:
    all match before-state

authoritative temporary replacement files:
    possibly present

link cache:
    current at generation N

database generation:
    N

response:
    absent
```

No authoritative entity location has changed.

## Expected Recovery Result

Recovery behaves as a full unapplied pending transaction:

* all entities compare as before-state;
* all after-states are applied;
* temporary replacement artifacts are ignored or safely reused only if validated;
* cache consequences are completed;
* journal sequence `N + 1` commits.

## Final Expected State

All affected entities match after-state at generation `N + 1`.

---

# Boundary 5 — During the First Entity Write

## Injection Point

Crash while replacing or updating the first authoritative entity.

Subcases depend on the storage mechanism.

For a JSON entity file:

* temporary replacement partially written;
* temporary replacement complete but not moved;
* destination move interrupted;
* old file absent and new file present;
* both old and replacement artifacts present.

For SQLite-backed authoritative state:

* before SQL transaction commit;
* after SQL commit but before the caller records completion.

## Expected State Before Restart

The first logical entity may:

* still match before-state;
* already match after-state;
* have temporary filesystem artifacts surrounding one valid authoritative state.

It must not be accepted in an unparseable or logically unclassifiable authoritative form.

Other affected entities still match before-state.

The pending journal remains complete.

## Expected Recovery Result

Recovery reads the authoritative logical entity, not merely temporary filenames.

If the first entity matches before-state:

```text
apply after-state
```

If it matches after-state:

```text
leave unchanged
```

If it matches neither:

```text
enter recovery error
```

Recovery then applies all remaining entities and commits the transaction.

---

# Boundary 6 — Between Entity Writes

## Injection Point

Crash after one or more affected entities have reached after-state, while one or more others remain at before-state.

Example:

```text
Entity A:
    after-state

Entity B:
    after-state

Entity C:
    before-state

journal:
    pending

generation:
    N
```

This is the principal partial-application test.

## Expected State Before Restart

```text
request:
    claimed

pending journal:
    sequence N+1 complete

committed journal N+1:
    absent

some entities:
    after-state

remaining entities:
    before-state

link cache:
    generation N, partially changed, or not yet changed

database generation:
    N

response:
    absent
```

The disk may contain a mixed physical state, but the published committed generation remains `N`.

## Expected Recovery Result

For every affected logical entity:

```text
current == after:
    no mutation

current == before:
    apply after

current == neither:
    recovery error
```

Recovery must not increment revisions again on entities already at after-state.

After all entity after-states are established:

1. reconcile cache consequences;
2. advance cache to target generation;
3. commit the journal;
4. advance database generation;
5. deliver the response;
6. archive the request.

## Final Expected State

Every affected entity matches after-state exactly once.

No entity remains at before-state.

---

# Boundary 7 — During a Later Entity Write

## Injection Point

Crash while writing an entity after at least one earlier entity has already reached after-state.

This combines:

* partial transaction application;
* ambiguous completion of the currently written entity.

## Expected State Before Restart

Earlier entities match after-state.

Later untouched entities match before-state.

The entity being written may match before or after when interpreted through authoritative storage.

## Expected Recovery Result

Recovery classifies each entity independently.

The current entity must resolve to:

* before-state;
* after-state; or
* an explicit recovery error.

The transaction is then completed exactly as in Boundary 6.

---

# Boundary 8 — After All Entity Writes

## Injection Point

Crash after all authoritative entity stores match after-state, but before required derived cache work is complete.

Conceptually:

```text
all authoritative entities complete
        ↓
CRASH
        ↓
link cache incomplete or behind
```

## Expected State Before Restart

```text
pending journal:
    sequence N+1 complete

all affected entities:
    after-state

link cache:
    current at N, stale, or partially updated

committed journal N+1:
    absent

database generation:
    N

response:
    absent
```

## Expected Recovery Result

Recovery:

1. confirms all authoritative entities already match after-state;
2. performs no entity revision changes;
3. derives cache consequences from journaled before and after states;
4. completes or rebuilds affected cache entries;
5. prepares an updating cache record with published generation `N` and target generation `N + 1`;
6. commits the journal and advances database generation;
7. publishes the cache as current at generation `N + 1`.

The cache must not be treated as current for generation `N + 1` before reconciliation completes.

---

# Boundary 9 — During Link-Cache Update

## Injection Point

Crash after authoritative entity writes complete but while cache files are being changed.

Subcases include:

* outgoing entry updated but incoming entry not updated;
* incoming entry updated but outgoing entry not updated;
* endpoint membership removed but replacement membership not added;
* entry files correct but global cache generation still `N`;
* global generation temporary file written but not published.

## Expected State Before Restart

```text
authoritative entities:
    all after-state

pending journal:
    sequence N+1 complete

cache:
    incomplete, stale, or partially changed

database generation:
    N
```

The authoritative link entities define the required cache result.

## Expected Recovery Result

Recovery recomputes the required memberships from the journaled authoritative before and after states.

Cache operations are repeated idempotently:

```text
add existing membership:
    no-op

remove absent membership:
    no-op
```

After all entries are correct, recovery writes or verifies an updating cache record with published generation `N` and target generation `N + 1`, commits the journal, and then publishes the cache as current at `N + 1`.

---

# Boundary 10 — After All Entity and Cache Writes

## Injection Point

Crash after:

* every authoritative entity matches after-state;
* all required cache entries are correct;
* `generation.json` is prepared with `state = updating`, published generation `N`, and target generation `N + 1`;

but before journal commitment.

## Expected State Before Restart

```text
pending journal:
    sequence N+1 complete

all entities:
    after-state

link cache:
    state updating
    published generation N
    target generation N+1

committed journal N+1:
    absent

recognized database generation:
    N

response:
    absent
```

## Expected Recovery Result

Recovery verifies that all state already matches the intended result.

It performs no logical entity mutation.

It then:

1. commits the pending journal;
2. advances recognized database generation to `N + 1`;
3. publishes the cache as current at `N + 1`;
4. delivers the response;
5. archives the request.

This proves that recovery can finalize an already-applied transaction without applying it twice.

---

# Boundary 11 — Before Journal Commitment

## Injection Point

Crash immediately before moving the pending journal record into `journal/committed/`.

This may be operationally identical to Boundary 10, but it should have a separate injection point to verify the final pre-commit check.

## Expected State Before Restart

```text
all intended state:
    complete

pending journal:
    present

committed journal:
    absent

database generation:
    N
```

## Expected Recovery Result

Recovery confirms the complete after-state and commits sequence `N + 1`.

No entity or cache content changes unless verification finds an incomplete component.

---

# Boundary 12 — During Journal Commitment

## Injection Point

Crash during movement of the journal file from `pending/` to `committed/`.

Possible filesystem states include:

* file only in `pending/`;
* file only in `committed/`;
* identical copies in both locations;
* destination complete while source removal did not occur;
* ambiguous directory metadata after an interrupted move.

## Expected State Before Restart

All transaction after-state is complete.

Journal placement may be ambiguous.

The database generation metadata or published status may still report `N`.

## Expected Recovery Result

Recovery determines whether the pending and committed artifacts represent the same logical journal entry.

### Only Pending Exists

Finalize the move and advance generation.

### Only Committed Exists

Recognize sequence `N + 1` as committed after verifying authoritative after-state.

### Identical Copies Exist

Retain one committed record and remove or quarantine the duplicate pending copy.

### Conflicting Copies Exist

Enter recovery error.

Recovery must never apply the transaction as a new sequence.

---

# Boundary 13 — After Journal Commitment, Before Cache-Current Publication

## Injection Point

Crash after the journal record is committed and generation has logically advanced, but before the cache is published as current and before response construction or delivery.

Conceptually:

```text
journal committed
generation N+1
        ↓
CRASH
        ↓
cache still updating; response not delivered
```

## Expected State Before Restart

```text
affected entities:
    all after-state

link cache:
    state updating
    generation N
    target-generation N+1

committed journal:
    sequence N+1 present

pending journal:
    absent

database generation:
    N+1

request:
    still claimed

response:
    absent
```

## Expected Recovery Result

On restart:

1. Subete finds the claimed request.
2. It associates the request ID with committed journal sequence `N + 1`.
3. It does not execute, plan, or journal the transaction again.
4. It publishes the cache as current at generation `N + 1`.
5. It reconstructs the committed success response.
6. It attempts response delivery.
7. It archives the request as completed if delivery policy permits.

The transaction remains committed regardless of response delivery outcome.

---

# Boundary 14 — During Response Writing

## Injection Point

Crash while writing the response to the SASE destination.

Subcases include:

* empty response file;
* partial JSON;
* complete temporary response not published;
* complete response published but delivery function did not return;
* replacement of a preexisting partial response interrupted.

## Expected State Before Restart

```text
transaction:
    committed

database generation:
    N+1

request:
    claimed

response destination:
    absent, partial, or complete
```

## Expected Recovery Result

Recovery recognizes the committed request and reproduces the same logical response.

It may safely replace or redeliver the response.

It must not create another transaction or journal sequence.

The recipient must tolerate receiving the same logical response again.

---

# Boundary 15 — After Commitment but Before Response Delivery

## Injection Point

Crash after transaction commitment and before the first response byte is written.

This is the required clean post-commit/pre-response boundary.

## Expected State Before Restart

```text
journal:
    committed

generation:
    N+1

request:
    claimed

response:
    absent

entities and cache:
    complete at N+1
```

## Expected Recovery Result

The response is reconstructed from the committed outcome and delivered.

No authoritative mutation occurs.

The request then moves to `completed/`.

---

# Boundary 16 — After Response Delivery

## Injection Point

Crash after the complete response file is published, but before the request is archived.

## Expected State Before Restart

```text
transaction:
    committed

generation:
    N+1

response:
    complete

request:
    still claimed
```

## Expected Recovery Result

On restart:

1. Subete recognizes the committed journal outcome.
2. It may verify or redeliver the same response.
3. It does not re-execute the transaction.
4. It moves the request to `completed/`.

A repeated response must be logically identical to the original response.

---

# Boundary 17 — After Response Delivery but Before Request Archival

## Injection Point

Crash at the exact required boundary:

```text
response delivery succeeded
        ↓
CRASH
        ↓
claimed request not yet moved to completed
```

## Expected State Before Restart

```text
committed journal:
    sequence N+1 present

database generation:
    N+1

response:
    complete

request:
    claimed

completed record:
    absent
```

## Expected Recovery Result

Recovery resolves the claimed request as already committed and already answered or answerable.

It archives the request as completed.

No transaction work is repeated.

---

# Boundary 18 — During Request Archival

## Injection Point

Crash while moving the request from `claimed/` to `completed/`.

Possible states include:

* request only in `claimed/`;
* request only in `completed/`;
* identical copies in both locations;
* incomplete auxiliary completion metadata.

## Expected State Before Restart

The transaction is committed and the response has been delivered or recorded as attempted.

Only request-record placement is ambiguous.

## Expected Recovery Result

Recovery normalizes the request to one completed record.

It does not:

* replan the transaction;
* write another journal entry;
* advance generation;
* modify entity revisions.

Conflicting copies with the same request ID but different request content cause an explicit error.

---

# Boundary 19 — After Request Archival

## Injection Point

Crash immediately after the request reaches `completed/`.

## Expected State Before Restart

```text
transaction:
    committed

response:
    delivered or recorded

request:
    completed

generation:
    N+1
```

## Expected Recovery Result

No transaction recovery is required.

Startup recognizes the request as completed.

A duplicate inbox delivery of the same request ID receives the recorded result without re-execution.

---

# Boundary 20 — Validation Failure Before Journal Creation

Although not a successful transaction crash boundary, validation failures require injection tests.

## Injection Point

Crash after a validation failure has been determined but before:

* error response delivery;
* failed-request archival.

## Expected State Before Restart

```text
journal:
    absent

authoritative state:
    unchanged at N

request:
    claimed

recorded failure:
    absent or incomplete

response:
    absent
```

## Expected Recovery Result

The request may be validated again.

It must fail with the same logical validation outcome.

Subete delivers the error response and moves the request to `failed/`.

Generation remains `N`.

---

# Boundary 21 — After Failure Response but Before Failed Archival

## Injection Point

Crash after delivering a pre-journal failure response but before moving the request to `failed/`.

## Expected State Before Restart

```text
journal:
    absent

authoritative state:
    unchanged

response:
    complete failure response

request:
    claimed
```

## Expected Recovery Result

Subete reproduces or confirms the same failure result and archives the request in `failed/`.

No journal is created.

---

# Boundary 22 — No-Op Transaction

A transaction whose operations produce no authoritative change should be tested at all journal and post-journal boundaries according to the chosen protocol rule.

If no-op transactions receive journal sequences:

```text
pending journal:
    complete

entity before-state:
    equals after-state

recovery:
    verifies equality and commits sequence
```

Recovery must not invent a revision increment.

If protocol policy changes so no-op transactions do not journal, this test must be updated explicitly.

---

# Boundary 23 — Entity Creation Interrupted

Test creation with:

```text
before = null
after  = entity revision 1
```

## Expected Recovery Classification

```text
entity absent:
    matches before-state

entity present and equal to after:
    matches after-state

entity present with different contents:
    recovery error
```

Crash points must include:

* before created file exists;
* after one created entity exists;
* after all created entities exist;
* during cache membership creation for a new link.

---

# Boundary 24 — Entity Deletion Interrupted

Test deletion with:

```text
before = complete entity
after  = null
```

## Expected Recovery Classification

```text
entity present and equal to before:
    apply deletion

entity absent:
    matches after-state

entity present but unequal to before:
    recovery error
```

For link deletion, cache removals must also be tested independently.

---

# Boundary 25 — Link Endpoint Change Interrupted

Use a link whose endpoints change:

```text
before:
    from = A
    to   = B

after:
    from = C
    to   = D
```

Inject crashes after each individual cache operation:

1. removed from outgoing A;
2. removed from incoming B;
3. added to outgoing C;
4. added to incoming D;
5. global cache generation updated.

After recovery, the link ID must exist:

```text
outgoing C
incoming D
```

and must not exist:

```text
outgoing A
incoming B
```

unless an endpoint is shared between before and after.

---

# Boundary 26 — Authoritative SQLite Commit

When authoritative aspects are stored in SQLite, test at least:

* before SQL transaction begins;
* during SQL transaction before commit;
* immediately after SQL commit;
* after SQLite state commits but before entity-file changes;
* after entity-file changes but before SQLite commit;
* after all authoritative stores commit but before journal commitment.

Recovery always compares the complete logical entity assembled across all authoritative stores.

It must not judge only one physical store in isolation.

A logical entity matching neither complete before-state nor complete after-state causes recovery error.

---

# Boundary 27 — Cache Rebuild During Recovery

When the cache is absent or unusable during pending transaction recovery:

## Expected State Before Restart

```text
authoritative entities:
    classifiable from journal

cache:
    absent, stale, or malformed

pending journal:
    complete
```

## Expected Recovery Result

Subete:

1. completes authoritative transaction application;
2. rebuilds or reconciles the cache from authoritative link entities;
3. confirms target cache generation;
4. commits the pending journal;
5. announces ready only after cache readiness rules are satisfied.

The transaction must not fail merely because a derived cache was lost.

---

# Boundary 28 — Unknown Entity State

This is a deliberate corruption test rather than an ordinary crash boundary.

Before restart, alter one affected entity so it matches neither journaled before-state nor after-state.

## Expected Recovery Result

Subete enters recovery error.

It must not:

* overwrite the unexplained state automatically;
* choose before or after by similarity;
* commit the journal;
* announce ready;
* process later requests.

Status should identify:

* journal sequence;
* entity ID;
* failed comparison;
* recovery phase.

---

# Boundary 29 — Conflicting Journal Sequence

Create two different pending or committed journal files claiming sequence `N + 1`.

## Expected Recovery Result

Subete enters recovery error.

It must not select one by:

* filename order;
* modification time;
* request arrival time;
* whichever file parses first.

One sequence may identify only one logical transaction.

---

# Boundary 30 — Duplicate Request ID with Different Content

Submit a request using a request ID already associated with a pending or committed journal, but change its contents.

## Expected Recovery Result

Subete rejects the duplicate as a request-ID conflict.

It must not:

* execute the changed request;
* replace the original journal meaning;
* return the original success as though the changed contents matched.

The original transaction outcome remains intact.

---

# Core Matrix

| Crash boundary                    | Journal before restart      | Entity state before restart  |  Generation before restart | Expected recovery                                      |
| --------------------------------- | --------------------------- | ---------------------------- | -------------------------: | ------------------------------------------------------ |
| Before journal creation           | None                        | All before                   |                          N | Revalidate and execute normally                        |
| During journal writing            | Temporary only              | All before                   |                          N | Discard or quarantine temporary journal; retry request |
| After journal completion          | Pending                     | All before                   |                          N | Apply all after-states and commit                      |
| Before first entity write         | Pending                     | All before                   |                          N | Apply all after-states and commit                      |
| During first entity write         | Pending                     | First entity before or after |                          N | Classify first entity; finish transaction              |
| Between entity writes             | Pending                     | Mixed before and after       |                          N | Leave after-states; apply remaining before-states      |
| After all entity writes           | Pending                     | All after                    |                          N | Reconcile cache and commit                             |
| During cache update               | Pending                     | All after                    |                          N | Complete cache idempotently and commit                 |
| Before journal commitment         | Pending                     | All after; cache updating    |                          N | Commit, then publish cache current                     |
| During journal commitment         | Pending, committed, or both | All after                    | N or uncertain publication | Normalize one committed journal; recognize N+1         |
| After commitment, before cache publication | Committed            | All after                    |                        N+1 | Publish cache current; no re-execution                 |
| During response delivery          | Committed                   | All after                    |                        N+1 | Redeliver same logical response                        |
| After response, before archival   | Committed                   | All after                    |                        N+1 | Archive claimed request                                |
| During request archival           | Committed                   | All after                    |                        N+1 | Normalize one completed record                         |
| After request archival            | Committed                   | All after                    |                        N+1 | No recovery work required                              |

---

# Automated Test Shape

Each failure test should follow a common harness shape:

```text
prepare_fixture(N)
submit_request()
enable_failure_point(name)
start_service_subprocess()
assert_service_crashed_at(name)
inspect_disk_state()
restart_service_without_failure()
wait_for_ready_or_recovery_error()
assert_expected_final_state()
```

The harness should preserve the failed-run directory long enough to inspect it when assertions fail.

A failed test report should include:

* failure-point name;
* process exit result;
* database generation;
* request location;
* pending and committed journal filenames;
* entity-state classifications;
* cache generation and state;
* response state;
* published status.

---

# Suggested Failure-Point Names

Stable symbolic names should be used by implementation and tests.

```text
transaction.after_plan
journal.before_create
journal.after_temp_create
journal.during_write
journal.after_temp_complete
journal.after_pending_publish

apply.before_first_entity
apply.before_entity
apply.after_entity
apply.between_entities
apply.after_all_entities

cache.before_update
cache.after_outgoing
cache.after_incoming
cache.before_generation
cache.after_generation
cache.before_current_publish
cache.during_current_publish
cache.after_current_publish

commit.before_move
commit.during_move
commit.after_move
commit.after_generation

response.before_write
response.during_write
response.after_write

request.before_complete_archive
request.during_complete_archive
request.after_complete_archive

failure.before_response
failure.after_response
failure.before_failed_archive
```

Entity-specific injection points may include an entity index:

```text
apply.before_entity.0
apply.after_entity.0
apply.before_entity.1
apply.after_entity.1
```

Tests should not depend on incidental dictionary iteration order.

The transaction plan or application layer should expose a deterministic physical application order for the fixture.

---

# Pass Criteria

The failure-injection suite passes only when every recoverable boundary results in one of two explicit outcomes.

## Successful Recovery

```text
all intended after-state established
journal committed exactly once
generation advanced exactly once
response reproducible
request completed
service ready
```

## Explicit Recovery Error

```text
state cannot safely be classified
journal not falsely committed
generation not guessed forward
service not ready
artifacts preserved
operator-visible error published
```

No test may pass with:

* silent data loss;
* a partially committed generation;
* duplicate revision advancement;
* a second transaction created for the same request;
* a stale cache presented as current;
* a committed transaction reported as failed;
* an uncommitted transaction reported as successful;
* unexplained automatic rewriting of corrupt state.

---

# Non-Negotiable Test Invariants

* Before `journal/pending/`, a crash leaves authoritative state unchanged.
* After `journal/pending/`, recovery completes the recorded transaction.
* A temporary journal never authorizes mutation.
* Every affected entity is classified against complete before-state and after-state.
* Matching after-state is left unchanged.
* Matching before-state is advanced to after-state.
* Matching neither produces recovery error.
* Entity revisions advance at most once.
* Cache updates are derived and repeatable.
* Journal commitment occurs only after complete authoritative state and required derived cache-entry preparation.
* A cache is published as current only after the corresponding journal commitment establishes the same database generation.
* Generation advances at most once.
* Response delivery failure never reverses commitment.
* Request archival failure never causes re-execution.
* Duplicate requests return or reproduce one logical outcome.
* Startup does not announce `ready` while a recoverable pending transaction remains unresolved.
