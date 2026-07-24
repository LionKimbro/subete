# Subete — Version 1 Implementation Design

## Status and Scope

This is an implementation design, not a protocol change and not source code.

It is derived from [the Version 1 scope index](003__version1-scope-index.json), which fixes the governing specification set at commit `e211f8b11dab1f087a30261ba2c6ec89f4fd6107`.

The design preserves these Version 1 constraints:

* one authoritative filesystem-backed entity store;
* one authoritative writer and strictly sequential request processing;
* FileTalk delivery with incomplete-file tolerance;
* write-ahead journal recovery to the complete intended after-state;
* root `generation.json` as the authoritative published-generation record;
* a required, derived Version 1 link cache;
* no hybrid SQLite authority, concurrent request processing, or persistent search index;
* no new FileTalk message family without a governing protocol document.

## Design Principles

The implementation should use plain immutable-or-replaceable data structures, narrow functions, and `pathlib.Path` filesystem boundaries. It should not hide journal, generation, or recovery decisions behind an ORM, a generalized repository abstraction, or a broad transaction framework.

The central separation is:

```text
protocol interpretation → logical plan → durable journal → filesystem application → publication → response
```

Only the journal authorizes authoritative mutation. Only root `generation.json` publishes the recognized current database generation. Only `link-cache/generation.json` with `state = current` publishes the cache as current.

## Proposed Package Structure

```text
src/
  subete/
    __init__.py
    commands.py
    context.py
    setup.py
    service.py
    paths.py
    fsio.py
    model.py
    filetalk.py
    requests.py
    transactions.py
    reads.py
    searches.py
    entities.py
    journal.py
    generation.py
    link_cache.py
    recovery.py
    snapshots.py
    checkpoints.py
    maintenance.py
    status.py
    gui.py
    testhooks.py

tests/
  unit/
  integration/
  failure/
  fixtures/
```

`src/subete/` remains one package. Version 1 does not need plugins, a service mesh, a separate worker process, or a storage-driver registry.

### Module Boundaries

| Module | Owns | Must not own |
| --- | --- | --- |
| `commands` | CLI registration, argument/configuration assembly, framework lock declarations | Database semantics or direct entity mutation |
| `context` and `paths` | Validated database-root context and every fixed path | Request processing or recovery decisions |
| `setup` | First-time directory creation, identity/configuration/generation-zero creation | Replacement of an existing database identity |
| `service` | Strict sequential lifecycle, polling loop, startup/shutdown state | Protocol-specific validation details |
| `fsio` | Complete-file reads, durable replacement helpers, directory moves, fsync policy, filesystem error normalization | Entity or journal meaning |
| `filetalk` | Candidate-file observation, incomplete-file policy, claiming, reply destination validation, reply delivery | CRUD/search semantics |
| `requests` | Envelope parsing, request-family dispatch, duplicate routing, common structured errors | Transaction planning or entity persistence |
| `transactions` | Declarative operation validation, complete before/after planning, revision assignment, response construction | Direct filesystem mutation before journaling |
| `reads` | Read selectors and committed-generation read result construction | Mutation or journal allocation |
| `searches` | Version 1 full-scan predicate evaluation and result ordering | Persistent indexing or mutation |
| `entities` | Entity-file encoding, decoding, logical entity reads, exact before/after replacement | Journal sequencing or cache publication |
| `journal` | Sequence allocation, pending/committed entry persistence, validation, ambiguous-move normalization | Replanning transaction meaning |
| `generation` | Root `generation.json` validation, replacement, and journal/generation reconciliation | Link-cache state |
| `link_cache` | Prepared entry changes, global updating/current records, lookup, rebuild | Authority over link facts |
| `recovery` | Startup orchestration, pending completion, journal/generation reconciliation, claimed-request resumption | A second transaction semantic model |
| `snapshots` and `checkpoints` | Consistent capture, manifest/checkpoint validation, restoration/replay coordination | Live mutation outside service ownership |
| `maintenance` | Conservative retention analysis and requested cleanup after a protocol exists | Independent deletion of recovery artifacts |
| `status` | Derived status, heartbeat, and metrics publication | Commitment or recovery authority |
| `gui` | Read-only monitoring and FileTalk request construction | Direct database mutation |
| `testhooks` | Named, test-only failure points | Production behavior when disabled |

`model` contains small in-memory representations shared across modules: database context, parsed request, transaction plan, journal entry, entity state, cache change set, and structured result/error data. It contains no I/O.

## Internal Data Flow

### Service Startup

```text
commands
  → context validates root, identity, configuration, and paths
  → service acquires writer authority
  → status publishes starting/recovering
  → recovery reconciles journals, root generation, cache, and claimed requests
  → status publishes ready
  → strictly sequential polling loop begins
```

Startup must finish recovery before it considers any new inbox candidate. The runtime does not start a second request while the active request is waiting for reply delivery or archival.

### Inbox Intake and Claiming

```text
inbox path
  → filetalk observes candidate
  → complete JSON object? no: retry or apply configured stale action
  → complete JSON object? yes: claim into inbox-processing/claimed
  → requests parses and dispatches the retained original file
```

The intake layer must not assume visibility means completeness. `fsio` should expose a result that distinguishes incomplete/unreadable, complete JSON, and complete malformed JSON; this prevents parsing mechanics from being mistaken for protocol validation.

### Transaction Request

```text
claimed transaction
  → requests validates envelope and duplicate identity
  → transactions validates declarative operations
  → entities reads affected logical entity states at generation N
  → transactions produces one complete transaction plan
  → journal writes and closes pending sequence N+1
  → entities applies journaled after-states idempotently
  → link_cache prepares target-N+1 entries and global updating record
  → journal moves entry to committed
  → generation publishes root generation N+1
  → link_cache publishes current at N+1
  → filetalk delivers transaction response
  → request record reaches completed
```

Recovery starts from the journal entry at any point after pending placement. It never uses a lost in-memory plan and never increments an already-applied entity revision again.

### Read and Search Request

```text
claimed read/search
  → requests validates envelope and request body
  → reads or searches observes one committed generation
  → response is constructed and delivered
  → request record reaches completed
```

The service's sequential execution rule means no later mutation can occur while an active read or search is unfinished. Startup can therefore discard an incomplete temporary reply and rerun that retained claimed request at the same generation. A later identical completed read/search delivery may run again as a new non-mutating observation of the then-current generation.

### Cache and Generation Publication

The implementation should express the required sequence as one named orchestration function rather than scattering individual writes across transaction code:

```text
authoritative after-state established
  → cache entries prepared; cache global record = updating N → target N+1
  → journal entry committed
  → root generation.json = N+1
  → link-cache generation.json = current N+1
```

No module other than `generation` writes root `generation.json`. No module other than `link_cache` writes `link-cache/`. The transaction/recovery orchestrator calls these modules in the required order.

## Command Structure

| Command | Version 1 shape | Ownership and safety |
| --- | --- | --- |
| `subete setup` | Create or validate a database root, identity, initial configuration, and generation zero | Requires exclusive control; never overwrites an existing identity |
| `subete service` | Run recovery, then the sequential FileTalk service loop | Sole ordinary authoritative writer; holds writer lock |
| `subete gui` | Tkinter monitor and FileTalk request producer | Reads derived status only; never mutates internal files |
| `subete checkpoint` | Command surface reserved for requesting snapshot/checkpoint work from service | Must not copy a live datastore independently |
| `subete remove-old` | Command surface reserved for conservative service-owned retention work | Must not independently delete journals, snapshots, or checkpoints |

The scope currently governs transaction, read, and search FileTalk message families only. Before `checkpoint` or `remove-old` becomes functional through FileTalk, a maintenance message-family specification must define its envelope, identity, reply rule, authorization, and recovery behavior. Until then, the commands may report that the operation is not yet specified; they must not create an undocumented control plane.

Useful diagnostic commands may be added only if they are read-only or receive their own governing protocol/command specification.

## Testing Strategy

### Unit Tests

Unit tests should cover deterministic, I/O-free or temporary-directory-local behavior:

* entity-ID filename encoding and entity JSON validation;
* request and response envelope validation;
* transaction conflict detection and declarative plan construction;
* revision preconditions and revision advancement;
* read selector and search predicate evaluation;
* journal filename/sequence parsing;
* root and cache generation-record validation;
* dangling-link validation at creation/redirection time;
* cache membership diff construction;
* configuration defaults and reply-path containment checks.

### Integration Tests

Use a real temporary database root and the actual filesystem helpers:

* `setup` creates a usable generation-zero database;
* service claims complete inbox files but patiently ignores incomplete ones;
* transaction, read, and search replies match their protocols;
* declared link cache lookup agrees with authoritative link entities;
* a deleted endpoint retains its link-cache membership and attached-link lookup;
* replies written directly to final paths are readable with retry behavior;
* status, heartbeat, and metrics are derived only;
* snapshots/checkpoints restore and replay to the same authoritative world.

### Specification-Example Tests

Treat each walking example as a fixture recipe, not as governing authority. Tests should execute its setup and assert the governing protocol shapes, journal placement, revisions, root generation, and cache state. This prevents examples from silently drifting again.

### Property and Metamorphic Tests

For generated valid transaction plans, test that:

* applying the same journaled after-state twice is logically idempotent;
* cache rebuild equals cache incrementally derived from the same authoritative world;
* read/search requests never change root generation, entity content, or revisions;
* equivalent cache update order for independent entry files produces the same current cache;
* recovery from any prefix of an application sequence reaches the same after-state as uninterrupted application.

## Failure-Injection Mechanism

Failure injection belongs in production modules only as inert named hook calls. `testhooks` supplies no-op hooks by default and an enabled test controller only in tests.

Each named hook is placed immediately after a meaningful durable boundary, never before an operation merely because it is convenient to test. The controller must be able to stop the service process abruptly, without normal cleanup, after the preceding write has been flushed according to the implementation's durability policy.

Use subprocess tests for crash semantics:

1. create a known database at generation `N`;
2. start a service subprocess with one named hook enabled;
3. submit one request and wait until the hook records that it was reached;
4. terminate the process abruptly;
5. inspect on-disk artifacts without repair;
6. start a fresh service subprocess without the hook;
7. wait for `ready` or explicit recovery error;
8. assert the exact authoritative world, root generation, journal placement, link-cache state, request record, and response behavior.

The named hook catalog should map directly to `tests/failure-injection.md`: journal construction/publication, each authoritative entity replacement, cache-entry preparation, cache updating-record publication, journal move, root-generation publication, cache-current publication, response writing, and request archival. Hooks should also cover incomplete inbox/reply files and stale-file policy paths.

The failure harness must distinguish an expected abrupt termination from a test failure. It must preserve the failed database root for diagnostic inspection when an assertion fails.

## Staged Implementation Order

1. **Foundation:** establish package skeleton, command registration, database context, paths, filesystem helpers, configuration/identity/generation format validation, and `setup` generation zero.
2. **Authoritative entity store:** implement entity-file encoding, complete read/write replacement helpers, and entity format tests.
3. **FileTalk mechanics:** implement candidate observation, incomplete-file tolerance, claiming, configured stale-file actions, reply-path validation, and reply delivery.
4. **Read/search vertical slice:** implement request parsing, reads, full-scan searches, response construction, sequential service loop, and completed-request handling. This provides a non-mutating end-to-end service before journaling.
5. **Transaction planning:** implement declarative operation validation, revisions, complete before/after planning, conventional link endpoint validation, and transaction response construction.
6. **Journal and root generation:** implement pending journal persistence, sequence allocation, committed moves, root generation publication, and their format/unit tests.
7. **Transaction application and recovery:** apply journaled entity after-states idempotently; implement pending recovery, ambiguous journal movement handling, and claimed transaction response reconstruction.
8. **Version 1 link cache:** implement cache membership derivation, prepared/updating/current publication, lookup, rebuild, dangling-endpoint behavior, and recovery reconciliation.
9. **Status and observability:** implement status, heartbeat, metrics, startup/recovery/error presentation, and GUI read-only monitoring.
10. **Snapshots, checkpoints, restoration:** implement consistent capture, validation, checkpoint publication, journal replay, root-generation reconstruction, and conservative retention analysis.
11. **Failure campaign:** add the full crash-boundary subprocess harness, first for journal/entity/generation/cache boundaries and then response/request-record boundaries. Make it required in continuous testing.
12. **Maintenance protocol gate:** specify and then implement service-owned checkpoint/remove-old request families. Do not bypass the gate with direct live-datastore commands.

Each stage should end with a working, tested vertical slice. Later stages may extend behavior but must not weaken the invariants already exercised by earlier failure tests.

## Completion Criteria for Version 1 Implementation

Version 1 is implementation-ready when all governing format/protocol documents have executable tests, every required failure-injection boundary has a subprocess recovery test, the walking examples pass as conformance fixtures, and no command can mutate or remove recovery-critical state outside the service ownership model.
