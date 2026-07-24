```
title: Subete Version 1 Implementation Plan for Codex 5.6 Terra
date: 2026-07-23
document-type: implementation-plan
status: proposed
governing-specification-commit: e211f8b11dab1f087a30261ba2c6ec89f4fd6107
```

# Subete Version 1 Implementation Plan for Codex 5.6 Terra

## 1. Mission

Implement Subete Version 1 as the small, sequential, filesystem-backed M1
database defined by the frozen scope index in
`docs/raw/003__version1-scope-index.json`.

The implementation must preserve this durable pipeline:

```text
FileTalk request
    -> validation
    -> logical transaction plan
    -> immutable pending journal
    -> idempotent authoritative application
    -> link-cache preparation
    -> journal commitment
    -> root generation publication
    -> link-cache current publication
    -> response delivery
    -> terminal request archival
```

Correctness and recoverability are the priority. Do not introduce concurrent
request processing, a persistent search index, entity sharding, SQLite
authority, M1 layering, a repository/ORM framework, or an undocumented
maintenance protocol.

## 2. Source Authority and Working-Tree Rules

Use sources in this order:

1. The governing files listed by
   `docs/raw/003__version1-scope-index.json`, fixed at commit
   `e211f8b11dab1f087a30261ba2c6ec89f4fd6107`.
2. Accepted ADRs in `docs/architecture/`.
3. M1 Lattice Core Specification v3,
   `C:/lion/github/m1/docs/raw/030__m1lattice-spec-core-v3.json`.
4. M1 Lattice Transport Specification v3,
   `C:/lion/github/m1/docs/raw/031__m1lattice-spec-transport-v3.json`, where
   transport representation helps clarify values and identity; Subete does
   not otherwise implement M1 transport layering or tombstones.
5. The `lionscliapp` reference and actual installed/local framework behavior.
6. `docs/raw/004__version1-implementation-design.md` as non-governing
   implementation guidance.
7. Walking examples as conformance fixtures, not authorities.

M1 v3 supersedes M1 v2 for Subete Version 1. Where a frozen Subete document
was written against M1 v2, apply the user-approved v3 identity and aspect-value
rules and update the affected Subete specification text before implementation.

At plan finalization time the shared worktree is active and has user-owned
work, including:

```text
modified:  docs/raw/001__development-process.md
modified:  README.md
modified:  src/subete/__init__.py
untracked: docs/raw/004__version1-implementation-design.md
untracked: .context-jetpack/
untracked: pyproject.toml
untracked: src/subete/commands.py
untracked: src/subete/constants.py
untracked: src/subete/entities.py
untracked: src/subete/fsio.py
untracked: src/subete/paths.py
untracked: src/subete/setup.py
untracked: src/subete/validation.py
untracked: tests/
```

Some implementation files appeared concurrently while this plan was being
written and may continue to change. Before Stage 0, inventory the then-current
worktree, read every existing implementation/test file, run its tests, and map
it onto this plan. Reuse correct work rather than recreating it. Preserve all
pre-existing changes; do not overwrite, stage, or commit them unless Lion
explicitly includes them in the implementation change.

Read `db/rules.md` at the beginning of every implementation session. Keep
`docs/code/` synchronized if implementation work exposes a genuine
specification correction; do not casually rewrite the frozen specification to
fit code.

## 3. Required Pre-Implementation Decisions

Terra must resolve these gates before making a consequential assumption.

### Gate A: `lionscliapp` project root and lock placement — resolved

The framework writes `lock.json` and its own `config.json` beneath its project
root. Subete requires `lock.json` at the selected database root, while its
operational database configuration is a distinct `configuration.json`.

Recommended Version 1 integration:

* declare the `lionscliapp` project directory as `"."`;
* treat the framework execution root as the Subete database root;
* disable `--project-dir` override;
* use `--execroot <database-root>` as the sole database selector;
* do not expose `execpath.dbroot` as an independent configurable key, because
  Lion acquires locks before command dispatch;
* treat root `config.json` as framework-owned CLI configuration and
  `configuration.json` as Subete-owned operational configuration;
* add a short specification/documentation note acknowledging the
  framework-owned `config.json`.

The integration test proves that `declare_projectdir(".")` causes locking at
`<dbroot>/lock.json` on supported platforms. Lion permits the optional extra
root `config.json`; Subete does not create a second lock.

### Resolved Gate B: entity-ID and aspect-ID validation

Version 1 entity IDs and aspect IDs may be UUIDs or Tag URIs.

For UUID identifiers:

* accept only the standard hyphenated textual form
  `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`;
* accept uppercase or lowercase hexadecimal digits on input;
* reject compact, braced, URN-prefixed, and all other alternate UUID
  spellings;
* validate the UUID according to RFC 9562;
* canonicalize every accepted UUID to lowercase hyphenated form at the
  request boundary;
* use the canonical form for storage, filenames, lookup, comparison,
  duplicate detection, journal content, cache content, and responses;
* treat uppercase and lowercase spellings of the same UUID as the same
  identifier.

For Tag URI identifiers:

* validate according to RFC 4151;
* preserve the submitted identifier exactly;
* compare it exactly;
* do not introduce a Subete-specific canonicalization rule unless the M1
  specification establishes one.

Use strict, reversible UTF-8 percent encoding for non-UUID identifier
filenames. Reject decoded filename/content disagreement and encoding
collisions.

Record this behavior in tests and a focused `docs/code/` clarification before
relying on it as public protocol behavior.

### Gate C: aspect value domain — resolved by M1 v3

M1 Core v3 defines an aspect as an identified value whose content may be any
valid JSON value:

```text
object
array
string
number
boolean
null
```

Subete Version 1 therefore:

* accepts and preserves any valid JSON value as generic aspect content;
* treats an aspect as present when its identifier is present in the entity's
  aspect map, including when its value is `null`;
* treats `null` as an ordinary present aspect value;
* does not interpret `null` as deletion, absence, or a tombstone;
* removes an aspect only through `delete-aspect`, which removes the identifier
  from the entity's aspect map;
* does not implement M1 transport tombstones or transport layering;
* may apply stricter content validation for a recognized conventional aspect
  whose own schema requires it—for example, the conventional link aspect must
  be an object with valid `from` and `to` identifiers.

Update the affected Subete specification text from M1 v2 to v3 before
implementation. Validation must test field presence independently from field
value so a supplied `"value": null` is not mistaken for a missing `value`
field.

### Gate D: public link lookup and maintenance operations — resolved

Version 1 extends the existing `search` request family with three predicates:

```text
link-from
link-to
link-attached-to
```

They return the IDs of matching link entities. `link-attached-to` matches
either endpoint and returns a self-link only once. These predicates combine
with other predicates through the normal search-level AND rule. The link cache
is an internal optimization and never appears in public requests or responses.

Version 1 also defines one FileTalk request family:

```text
request-type = maintenance
```

Its request contains exactly one operation:

```text
checkpoint
remove-old
stop
```

The public commands:

```text
subete checkpoint
subete --maintenance.mode dry-run remove-old
subete --maintenance.mode execute remove-old
subete stop
```

are non-locking FileTalk clients to the running service. They post requests to
the inbox and wait for replies. They never directly copy, remove, mutate,
unlock, signal, or kill the live database service.

Maintenance runs inside the service's strictly sequential request boundary.
It does not mutate the M1 entity world, allocate a transaction journal
sequence, create a pending/committed transaction journal entry, change entity
revisions, or advance root generation.

`checkpoint` captures one committed generation, validates the snapshot, and
publishes its checkpoint before returning success.

`remove-old` requires an explicit `dry-run` or `execute` mode. The service
selects every candidate under its retention and recovery rules; the caller
cannot submit arbitrary paths.

After accepting `stop`, the service begins no later request. It delivers the
successful response, archives the request as completed, returns through normal
shutdown, and releases the writer lock through `lionscliapp`.

Version 1 maintenance authorization relies on operating-system access to the
database root, inbox, and allowed FileTalk reply paths. It has no separate
authentication or role model.

The governing details are in `docs/code/protocol-maintenance.md`,
`docs/code/protocol-search.md`, and
`docs/code/formats/maintenance-request.md`.

### Gate E: snapshot and restoration scope — resolved

A Version 1 snapshot captures the authoritative entity store only. Its
archive contains exactly `entities/` and `snapshot-manifest.json`; the
manifest carries only the metadata needed to identify and validate the
snapshot, including database identity and generation.

Snapshots contain no Subete or framework configuration, identity or
generation files, locks, journals, checkpoints, FileTalk processing state,
status/heartbeat/metrics, temporary files, or derived link-cache data.

Restoration never reads, merges, replaces, preserves, or otherwise operates
on `configuration.json`. The destination root must already have valid
machine-local configuration. Restoration validates database identity,
replaces `entities/`, publishes the snapshot generation, replays applicable
later journals through normal recovery, and rebuilds derived structures.

## 4. Programming Shape

Follow Lion's procedural machine style.

* Keep `src/subete/` flat and thematic.
* Use visible fixed-shape module bundles such as `g` for stable current
  context and `reg` for short-lived procedural working state.
* Mutate global containers in place; do not rebind them and do not use the
  `global` keyword.
* Put large open collections in their own named containers.
* Pass arguments only for caller-selected variation. Do not courier database
  context, configuration, paths, the active request, or the current journal
  through every function.
* Use zero-argument internal functions when they act on the current machine
  state.
* Keep coherent records intact as dictionaries.
* Initialize and reset register slots explicitly at flow boundaries.
* Do not trust registers across threads, delayed callbacks, recursion, or
  re-entry. Version 1 service execution is sequential.
* Give every state-owning module a test reset/init function.
* Keep import time quiet. All registration and startup work occurs through
  explicit `declare()`, `init()`, or `main()` calls.
* Prefer named filesystem and state-machine actions over broad abstractions.

The main transaction function should read like the actual machine:

```text
validate_transaction()
plan_transaction()
write_pending_journal()
apply_journal_entry()
prepare_link_cache()
commit_journal_entry()
publish_generation()
publish_link_cache_current()
deliver_response()
complete_request()
```

## 5. Target Repository and Package Structure

Complete the project foundation, reusing any correct files already present:

```text
pyproject.toml
run-tests.bat
README.md

src/subete/
  __init__.py
  cli.py
  context.py
  paths.py
  fsio.py
  identifiers.py
  validation.py
  errors.py
  setup.py
  service.py
  filetalk.py
  requests.py
  responses.py
  entities.py
  transactions.py
  journal.py
  generation.py
  link_cache.py
  recovery.py
  reads.py
  searches.py
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
  conformance/
  fixtures/
```

This is a responsibility map, not a requirement to create empty modules in one
commit. Add each module when its vertical slice begins.

Package metadata:

* distribution: `m1-subete`;
* import package: `subete`;
* Python: `>=3.10`, matching `lionscliapp`;
* runtime dependency: `lionscliapp>=0.1.2` unless framework integration work
  establishes a newer minimum;
* console entry point: `subete = "subete.cli:main"`;
* test dependency/group: `pytest`;
* license: `CC0-1.0`.

`run-tests.bat` must run the complete ordinary suite with a project-relative
command and preserve pytest's exit code. Document the separate, longer
failure-injection command.

## 6. Staged Implementation

Each stage ends in a green commit-sized vertical slice. Do not defer tests
until the end.

### Stage 0: bootstrap and prove CLI ownership

Implement:

* `pyproject.toml`, entry point, README, and test runner;
* explicit `lionscliapp` declarations for `setup`, `service`, `gui`,
  `checkpoint`, `remove-old`, and `stop`;
* `uses_locking = True`;
* lock flags on `setup` and `service`;
* non-locking GUI and maintenance FileTalk client command surfaces;
* the accepted Gate A database-root binding;
* no module-load operational calls.

Tests:

* installed `subete help` lists the intended commands;
* path coercion produces absolute `pathlib.Path` values;
* service/setup acquire `<dbroot>/lock.json`;
* a second locked command is rejected;
* `unlock` removes only the explicitly selected stale database lock;
* framework config and Subete `configuration.json` remain distinct;
* command declarations and module imports have no unwanted side effects.

Exit criterion: the selected database root and lock authority are
unambiguous.

### Stage 1: database setup, context, formats, and durable I/O

Implement:

* one fixed-shape database context initialized once per command;
* every path from `filesystem-layout.md`;
* setup that creates missing directories and generation zero;
* stable `identity.json` creation/validation;
* complete required `configuration.json` loading and strict known-field
  validation;
* root `generation.json` creation/validation;
* UTC `Z` timestamps;
* entity-ID and sequence filename encoding;
* UUID canonicalization at every external/durable decoding boundary;
* complete UTF-8 JSON reads;
* UTF-8 JSON writes with a trailing newline;
* same-filesystem temporary writes, flush/close, `os.replace`, and the
  documented file/directory sync policy for files beneath the database root;
* direct writes, without temporary sidecar files, to externally owned
  FileTalk reply destinations;
* tolerant JSON read states that distinguish missing, temporarily
  unreadable/incomplete, and complete JSON; format validation distinguishes
  wrong top-level type.

Setup must be idempotent for an existing valid database and must never replace
an existing `database-id`. Mismatched or ambiguous roots fail closed.

Tests:

* exact format validation for identity, configuration, and generation;
* setup of an empty database;
* repeated setup;
* refusal to overwrite invalid/existing identity;
* filename round trips for canonical UUIDs and exact Tag URIs;
* uppercase UUID input canonicalizes to lowercase in files and returned data;
* compact, braced, URN-prefixed, malformed, and other alternate UUID
  spellings are rejected;
* temp-file cleanup and replacement behavior;
* mismatch and malformed-file failures;
* Windows path containment and reparse/symlink-aware reply-root checks.

### Stage 2: authoritative entity store

Implement:

* entity file parse/validate/serialize;
* canonical filename/content identity agreement for UUIDs and exact agreement
  for Tag URIs;
* logical existence and complete reads;
* selected-aspect reads;
* stable entity enumeration by decoded entity ID;
* exact journaled-state comparison;
* creation/replacement/deletion by complete intended state;
* deterministic physical application order.

Entity writes are low-level mechanisms only; they must not allocate revisions
or decide transaction validity.

Tests:

* revision minimum and creation at revision 1;
* empty-aspect entity remains present;
* final-aspect deletion does not delete an entity;
* entity deletion removes the entity file;
* canonical lowercase UUID filenames and percent-encoded Tag URI IDs;
* uppercase UUID lookup resolves the same stored entity as lowercase lookup;
* malformed and duplicate/colliding entity files;
* exact before/after/null state classification;
* idempotent reapplication of an after-state.
* round-trip preservation of object, array, string, number, boolean, and
  `null` aspect values;
* distinction between a present `null` aspect and an absent aspect;
* distinction between a journal `before`/`after` value of `null` (entity
  absence) and a present entity whose aspect content is `null`;

### Stage 3: FileTalk intake, claiming, replies, and request records

Implement:

* flat deterministic inbox polling;
* direct-write tolerance;
* per-file size/mtime/first-seen/last-change observations;
* configured quiet period;
* `retain-and-report`, `quarantine`, and `delete` stale actions;
* claim only after reading one complete JSON object;
* collision-safe claim moves and ambiguous-move normalization;
* common envelope and required file-reply validation;
* allowed-reply-root containment;
* direct or atomic reply writing without assuming cross-filesystem rename;
* completed and failed request records preserving original content and
  structured outcome metadata.

A syntactically invalid visible file cannot always be distinguished
immediately from an incomplete write. Keep it unclaimed until the quiet-time
policy classifies it as stale; never guess from one failed parse.

Tests:

* files growing across polls;
* stable truncated JSON;
* complete non-object JSON;
* complete protocol-invalid objects;
* all stale policies;
* claim collisions and source/destination ambiguity;
* allowed, escaped, internal-dbroot, relative, symlink, and reparse reply
  paths;
* partial/direct reply reads and replacement;
* reply failure separated from logical request outcome.

### Stage 4: validated read/search vertical slice and sequential service

Implement:

* common request identity/type/content validation;
* one-at-a-time claimed-request lifecycle;
* startup processing of unfinished claimed non-mutating requests;
* read selected-aspect and all-aspect semantics;
* full-scan search with the eight Version 1 predicates, including
  `link-from`, `link-to`, and `link-attached-to`;
* Unicode `casefold()` matching;
* exact whitespace behavior;
* AND combination;
* entity-ID-only results sorted by Unicode code-point order;
* response delivery and terminal archival;
* graceful `KeyboardInterrupt` shutdown;
* no request begins until the active request is terminal.

Reads and searches capture root generation once and run while the single
service pipeline excludes all later mutations.

Tests:

* entity versus aspect not-found shapes;
* found empty entities;
* stable all-aspect serialization;
* every search predicate and every validation error;
* link endpoint predicates return link entity IDs, not opposite endpoints;
* a self-link appears once in `link-attached-to` results;
* link predicates combine with other predicates through AND;
* cache-backed and authoritative-scan link searches produce identical public
  results;
* malformed basic aspects are non-matches, not request failures;
* multiple reads/searches see one generation;
* repeat completed read/search behavior;
* interrupted claimed read/search reruns at the unchanged generation;
* reads/searches never change files, revisions, or generation;
* a second request cannot run while the first is delivering/archiving.

### Stage 5: pure transaction planning

Implement planning without any filesystem mutation:

* validate every operation and recognized field;
* reject unknown fields where the protocol requires a closed shape;
* detect all entity/aspect operation conflicts before state changes;
* load one committed before-state per affected entity;
* verify consistent expected revisions;
* apply independent operations to working copies;
* assign one revision increment per changed existing entity;
* preserve revisions for complete no-ops;
* produce complete before/after logical states;
* validate M1 link aspects;
* validate link endpoints against the complete transaction after-world,
  including entities created or deleted in the same transaction;
* permit later deletion of link endpoints without cascading or rewriting
  existing links;
* construct the deterministic logical success response.

Use deep copies for working aspect values so planning cannot dirty shared
committed objects.

Use key-presence checks for required fields. In particular, `"value": null`
is a supplied `set-aspect` value, while an absent `value` key is an invalid
operation.

Tests:

* all four mutation operations;
* multi-aspect same-entity changes with one revision increment;
* every prohibited operation combination;
* revision conflicts;
* no-op aspect deletion and no-op whole transaction;
* setting an aspect to `null`, replacing `null` with another JSON value, and
  deleting a present `null` aspect;
* arbitrary JSON aspect-value round trips without coercion;
* create/redirect link endpoint rules;
* dangling endpoints after later deletion;
* self-links;
* planner purity and deterministic plans;
* failure leaves the entire database byte-for-byte unchanged.

Exit criterion: the planner can reproduce both walking examples' entity
transitions without creating a journal or entity file.

### Stage 6: journal and authoritative transaction application

Implement:

* next sequence as published generation + 1;
* conflict checks against both journal directories;
* complete journal construction with the original request;
* 20-digit filename formatting;
* write under `tmp/`, flush/close, then publish immutable pending file;
* application driven only from the pending journal, never the lost planner;
* exact before/after/null classification;
* deterministic idempotent entity application;
* after-state verification;
* pending-to-committed move normalization;
* root generation publication only after committed placement;
* transaction response reconstruction from the committed journal.

No-op transactions still journal, consume a sequence, and advance root
generation, while unchanged entity revisions remain unchanged.

Tests:

* journal schema/filename/content agreement;
* no mutation before pending publication;
* creation, replacement, deletion, and no-op journal transitions;
* duplicate sequence/request conflicts;
* byte-identical pending/committed copies;
* committed-at-N+1/root-at-N reconciliation;
* suspicious pending-at-published-N+1 state;
* response reconstruction without replanning.

### Stage 7: Version 1 link cache and publication ordering

Implement:

* valid-link recognition using the conventional link aspect ID;
* incoming/outgoing entry formats;
* sorted unique membership;
* no file for an empty direction;
* cache consequences derived from journaled before/after states;
* create, remove, endpoint move, self-link, and ceased/became-link changes;
* idempotent entry mutation;
* global `updating` record with old generation and target generation;
* mandatory ordering:

```text
entity after-states complete
    -> cache entries prepared
    -> cache global state updating
    -> journal committed
    -> root generation published
    -> cache global state current
```

* current-state validation;
* incoming/outgoing/attached internal lookup;
* full coherent cache rebuild in a separate workspace;
* startup reconciliation/rebuild before `ready`;
* support cache keys for absent dangling endpoints.

Even transactions with no link membership changes perform the global
`updating` then `current` publication.

Tests:

* incremental cache equals a full authoritative rebuild;
* link creation, removal, endpoint move, and link-aspect deletion;
* self-link de-duplication in attached results;
* absent endpoint lookup;
* stale/absent/updating/ahead/mismatched cache states;
* entry files may retain older generations when membership is unchanged;
* partial rebuild is never visible;
* cache loss never changes authoritative links.

### Stage 8: startup recovery and duplicate transaction handling

Implement the exact startup order:

1. acquire writer authority;
2. validate identity, layout, configuration, and root generation;
3. conduct an entity-store structural correctness study: parse every entity
   file and verify its filename, identity, record shape, revision, aspect IDs,
   and JSON values; enter recovery error rather than publish `ready` when the
   authoritative store is structurally incoherent;
4. inspect database-owned temporary replacements, pending/committed journals,
   and sequence continuity; remove only abandoned temporary files whose
   filename and location establish Subete ownership;
5. normalize byte-identical ambiguous journal moves;
6. recover pending entries in ascending contiguous sequence order;
7. reconcile committed journals newer than root generation;
8. reconcile/rebuild link cache;
9. resolve claimed requests against journals and terminal records;
10. publish `ready`.

Recovery reuses the same journal application, cache preparation, commitment,
generation, response, and archival functions as normal execution. There must
not be a second mutation model.

Duplicate rules:

* same transaction ID and identical complete request: never re-execute;
  reconstruct/redeliver the original outcome;
* same ID with any changed content, including reply path:
  `request-id-conflict`;
* duplicate while active: at most one execution;
* completed identical reads/searches may execute again;
* failed pre-journal requests may be revalidated to reproduce failure.

Tests:

* every generation/journal combination in `formats/generation.md`;
* multiple contiguous pending entries;
* gaps, conflicting sequences, wrong database IDs, malformed journals;
* structurally malformed or filename-incoherent entity files enter recovery
  error before the service publishes `ready`;
* abandoned owned temporary files removed while unrelated files are retained;
* current entity matching before, after, or neither;
* identical versus conflicting duplicate journal files;
* committed transaction with claimed request and missing/partial/complete
  reply;
* request archive ambiguity;
* service never publishes `ready` in recovery error.

### Stage 9: status, heartbeat, metrics, and minimal GUI

Implement:

* fixed-shape runtime/status bundles;
* complete replacement of `status.json`, `heartbeat.json`, and
  `metrics.json`;
* required format versions, identity, generation, state, and timestamps;
* transaction/recovery/cache state transitions;
* inexpensive counters and timings;
* best-effort optional storage/queue counts;
* a minimal Tkinter monitor that reads only public/derived surfaces,
  tolerates missing/partial/stale files, and never treats status as authority;
* shared FileTalk client helpers for future GUI/maintenance use.

The GUI must not read or mutate journal/entity internals as an alternate
database client.

Tests:

* format validation and partial-read tolerance;
* status generation never leads root generation;
* heartbeat does not substitute for lock ownership;
* metrics reset safely on restart;
* GUI parsing/view-model tests without requiring a display;
* a small real Tk lifecycle smoke test only if the repository's GUI test
  tooling is available.

### Stage 10: snapshots, checkpoints, and replay foundations

Implement:

* consistent snapshot capture while the sequential service pauses mutation;
* separate temporary workspace and final ZIP publication;
* `snapshot-manifest.json`;
* database identity/generation/content validation;
* an archive containing exactly `entities/` and
  `snapshot-manifest.json`;
* rejection of snapshots containing configuration, identity/generation
  files, locks, journals, checkpoints, FileTalk state, status data,
  temporary files, or derived data;
* immutable checkpoint files written only after snapshot validation;
* highest-valid-checkpoint selection with fallback;
* ascending committed-journal replay using normal application logic;
* pending-next-transaction recovery after replay;
* restoration that replaces `entities/`, publishes the snapshot generation,
  replays applicable later journals through normal recovery, and rebuilds
  derived structures;
* strict exclusion of `configuration.json` from every restoration action,
  with valid machine-local destination configuration as a precondition;
* conservative retention analysis/dry-run as a pure plan;
* the `maintenance` request parser, validator, response construction, terminal
  record retention, and duplicate resolution;
* checkpoint and remove-old execution inside the sequential service;
* non-locking FileTalk clients for `subete checkpoint`,
  `subete remove-old`, and `subete stop`;
* explicit `maintenance.mode` validation for remove-old;
* successful stop response delivery and terminal archival before normal
  lock-releasing shutdown;
* refusal to begin a later request after accepting stop.

Maintenance does not use the transaction journal or advance generation.

Tests:

* snapshot at generation zero and nonzero;
* manifest/archive/identity/generation mismatch;
* rejection of every prohibited snapshot member;
* restoration leaves `configuration.json` byte-for-byte untouched;
* restoration publishes the snapshot generation before replay and rebuilds
  derived state after replay;
* incomplete snapshot/checkpoint publication;
* multiple checkpoints with invalid newest fallback;
* replay after checkpoint produces the same authoritative world;
* pending transaction after replay;
* old journals remain until a complete recovery path is proven;
* checkpoint requests return exact snapshot/checkpoint identities without
  changing generation;
* remove-old dry-run removes nothing;
* remove-old execute accepts no caller paths and preserves every required
  recovery chain;
* terminal maintenance retries reproduce retained responses without
  intentionally repeating operational effects;
* stop delivers and archives success before exit, begins no later request,
  and releases the writer lock normally;
* retention never selects pending journals or the only valid recovery chain.

### Stage 11: full subprocess crash campaign

Implement `testhooks.py` as inert named hook calls in production. In tests,
enable exactly one hook through a test-only environment setting and terminate
with `os._exit()` or external process kill so normal cleanup does not run.

The harness must:

1. create an independent generation-N fixture;
2. start the installed `subete service` in a subprocess;
3. submit one request;
4. wait for a durable marker proving the named hook was reached;
5. observe abrupt termination;
6. inspect disk before repair;
7. remove the known-stale framework lock through the selected database's
   `subete unlock` command only after proving the prior process is dead;
8. restart without failure injection;
9. wait for `ready` or explicit recovery error;
10. assert entities, revisions, journals, root generation, cache, response,
    and request placement.

Cover every named boundary in `docs/code/tests/failure-injection.md`, including
individual entity/cache writes, journal move ambiguity, root-generation
publication, cache-current publication, response writing, request archival,
no-op transactions, creates/deletes, endpoint moves, unknown state,
conflicting sequences, and read/search interruption.

Retain a failed test database and print a compact artifact inventory when a
test fails.

### Stage 12: conformance, documentation, and release readiness

Implement executable conformance fixtures from both walking examples.

Verify:

* exact request/reply shapes;
* complete journal records;
* entity revisions and files;
* generation 41 -> 42 and 42 -> 43 timelines;
* link-cache updating/current transitions;
* read and search output;
* partial application recovery;
* no double revision advancement.

Then:

* map every governing specification section to at least one test;
* run unit, integration, conformance, and failure suites;
* run on Windows, and another platform if supported;
* update README with setup/service/client examples and crash/unlock guidance;
* update `docs/code/` only for accepted clarifications or verified behavior;
* ensure examples match actual serialized output;
* verify `git diff` contains no unrelated user-owned changes;
* perform a final Version 1 scope audit.

## 7. Cross-Cutting Validation Rules

Use strict structural validation at public and durable boundaries.

* Protocol envelopes and durable records must have their specified top-level
  types; generic aspect content may be any valid JSON value, including
  `null`.
* Boolean values must not pass integer checks.
* UUID request IDs must be UUID strings.
* UUID entity and aspect IDs use only standard hyphenated input syntax and
  canonical lowercase internal form; Tag URI IDs are RFC 4151-valid and
  preserved exactly.
* Unknown request/search/operation predicates or fields are rejected where
  the governing protocol defines a closed vocabulary.
* Duplicate tags use Unicode case-folded comparison.
* Duplicate UUID aspect IDs are detected after canonicalization; duplicate
  Tag URI aspect IDs use exact comparison.
* Reply destinations are absolute and under an allowed normalized root.
* All durable metadata carries and verifies `database-id`.
* Journal filename, internal sequence, and request ID agree.
* Cache entry filename, entity, direction, and database identity agree.
* Snapshot/checkpoint filename and internal generation agree.
* Root generation never advances over a missing or incoherent recovery chain.

Represent expected protocol failures as structured data, not exceptions used
for ordinary branching. Reserve exceptions for I/O failure, programmer error,
and unrecoverable corruption boundaries.

## 8. Test Organization and Commands

Recommended markers/directories:

```text
tests/unit/          deterministic validation and planning
tests/integration/   real temporary database roots and CLI/service flows
tests/conformance/   walking examples and protocol shapes
tests/failure/       subprocess crash and corruption cases
```

Recommended commands:

```text
python -m pytest tests/unit tests/integration tests/conformance
python -m pytest tests/failure
python -m pytest
```

Every test receives its own temporary database root. Tests must not depend on
execution order or a developer's real Subete database.

Add property/metamorphic coverage for:

* applying a journaled after-state twice;
* incremental cache versus full rebuild;
* recovery from every prefix of the durable transaction sequence;
* reads/searches preserving all authoritative bytes and generation;
* deterministic response ordering independent of input dictionary order.

## 9. Required Commit Sequence

Prefer small reviewable commits aligned with the stages:

1. packaging and CLI/root-lock proof;
2. setup/formats/fsio;
3. entity storage;
4. FileTalk and records;
5. read/search service;
6. transaction planner;
7. journal/application/generation;
8. link cache;
9. startup recovery and duplicates;
10. status/GUI;
11. snapshots/checkpoints/replay;
12. failure harness;
13. conformance/docs.

Do not combine speculative refactors with durable-state work. Do not stage or
commit pre-existing user changes without explicit instruction.

## 10. Definition of Done

Version 1 is done only when:

* all frozen governing formats and protocols have executable coverage;
* only the service/recovery/restoration path mutates authoritative state;
* no authoritative mutation can occur before a complete pending journal;
* every complete pending transaction reaches its exact after-state or a
  visible recovery error;
* root generation, committed journal, and link-cache publication obey the
  required order;
* reads/searches observe one committed generation and never mutate it;
* transaction request IDs cannot execute twice;
* every required crash boundary passes in a real subprocess;
* both walking examples pass as conformance tests;
* snapshot/checkpoint recovery paths validate and replay correctly;
* link-search and maintenance protocols have executable coverage;
* restoration replaces only the authoritative entity store and never
  operates on machine-local configuration;
* README, packaging, test runner, and `docs/code/` accurately describe the
  finished implementation;
* no deferred Version 2 machinery has entered the codebase.
