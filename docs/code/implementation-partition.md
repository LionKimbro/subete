# Subete — Implementation Partition

This document divides the Subete program into implementation territories.

A territory is a coherent responsibility with a clear boundary. It may eventually be implemented by one module, several modules, or a small collection of named functions.

This document does not prescribe a class hierarchy.

Subete should prefer:

* plain data;
* named functions;
* explicit filesystem boundaries;
* narrow dependencies;
* direct correspondence between specifications and implementation territories.

---

# Program Shape

Subete is one command-line program with several commands.

```text
subete service
subete gui
subete setup
subete checkpoint
subete remove-old
```

Additional diagnostic or maintenance commands may be added later.

The primary configured path is:

```text
execpath.dbroot
```

It identifies the root directory of the Subete database operated on or observed by the command.

Within command execution:

```python
dbroot = app.ctx["execpath.dbroot"]
```

is an absolute `pathlib.Path`.

All database-relative paths are derived from this root.

---

# Command Summary

## `subete service`

Runs the authoritative Subete disk service.

It:

* acquires exclusive writer authority for the configured database;
* performs startup recovery;
* polls the FileTalk inbox;
* processes transaction, read, search, and maintenance requests;
* mutates authoritative storage;
* writes journals;
* publishes status, heartbeat, and metrics;
* continues until explicitly stopped or fatally unable to proceed.

Only one `service` command may hold writer authority for a database root at a time.

The service is the ordinary owner of all authoritative database mutation.

## `subete gui`

Runs a Tkinter monitor and control interface.

It:

* reads the published files beneath `status/`;
* presents database identity, service state, generation, queues, recovery state, snapshots, checkpoints, and metrics;
* constructs valid FileTalk requests;
* places requests into the database inbox;
* reads responses from its chosen SASE destination.

The GUI does not directly mutate authoritative database state.

It does not require exclusive database ownership.

Multiple GUI instances may observe and send requests to the same Subete service.

The GUI may be a normal Tkinter command without single-instance enforcement.

## `subete setup`

Creates or completes the filesystem structure for a Subete database at `execpath.dbroot`.

It may:

* create the database root;
* create required directories;
* create `identity.json`;
* create an initial `configuration.json`;
* establish generation zero;
* create empty operational directories;
* verify permissions and basic writability.

Setup must not silently replace an existing database identity.

If the target already contains a Subete database, setup should validate it and report what already exists rather than initialize a second database over it.

Setup requires temporary exclusive control of the database root while changing its structure.

It should refuse to run when an active Subete service owns the database.

## `subete checkpoint`

Requests creation of:

1. a new snapshot of a committed generation;
2. validation of that snapshot;
3. a checkpoint referring to the validated snapshot.

This command should normally communicate with the running service through FileTalk.

It does not independently copy live authoritative files while the service may be mutating them.

The command waits for or reports the service response according to normal request and response rules.

The service owns the snapshot consistency boundary and checkpoint publication.

## `subete remove-old`

Requests conservative removal or archival of old operational artifacts.

Possible targets include:

* completed request files;
* failed request files;
* old committed journals no longer required by retained recovery paths;
* old snapshots;
* old checkpoints;
* abandoned temporary files;
* old status-adjacent diagnostic artifacts.

This command should normally send a maintenance request to the running service.

The service determines what may safely be removed while preserving required recovery paths.

`remove-old` must not independently infer that a journal, snapshot, or checkpoint is unnecessary merely from its age.

A future dry-run mode should report proposed removals without performing them.

---

# lionscliapp Command Surface

The command-surface territory owns integration with `lionscliapp`.

It declares:

* application identity and version;
* project directory;
* configuration keys;
* commands;
* command help;
* command locking behavior;
* Tkinter command behavior;
* dispatch into Subete command functions.

It does not implement database semantics.

## Principal Key

```python
app.declare_key("execpath.dbroot", ".")
```

The final default may be changed before implementation.

The key means:

> The root directory of the Subete database used by this invocation.

Every command that operates on a database uses the same resolved key.

## Suggested Command Flags

```text
service:
    locking = true

gui:
    tkinter = true
    single_instance = false
    locking = false

setup:
    locking = true

checkpoint:
    locking = false

remove-old:
    locking = false
```

The exact framework lock location must be arranged so that the lock protects the selected database root rather than merely an unrelated invocation directory.

Command functions should be small entry points that assemble configuration and call the responsible territory.

---

# Database Context

The database-context territory derives and holds the fixed paths and configuration for one command invocation.

From `execpath.dbroot`, it derives locations such as:

```text
identity.json
configuration.json

inbox/
inbox-processing/claimed/
inbox-processing/completed/
inbox-processing/failed/

entities/

journal/pending/
journal/committed/
journal/checkpoints/

snapshots/

link-cache/

status/status.json
status/heartbeat.json
status/metrics.json

tmp/
```

This territory:

* reads database identity;
* reads operational configuration;
* resolves database-relative paths;
* verifies expected directory relationships;
* provides one shared context to the rest of the command.

It does not perform transaction processing.

The context may be represented as a plain fixed-shape dictionary.

---

# Service Runtime

The service-runtime territory owns the main lifetime of `subete service`.

It:

1. acquires writer authority;
2. opens and validates the database context;
3. publishes `starting`;
4. performs recovery;
5. publishes `ready`;
6. polls for requests;
7. dispatches one claimed request at a time;
8. publishes heartbeat and metrics;
9. performs orderly shutdown.

The initial implementation may process requests sequentially.

Concurrency is not required for Version 1.

A sequential service provides:

* one authoritative writer;
* simple generation ordering;
* straightforward transaction recovery;
* committed-generation reads;
* predictable FileTalk processing.

Performance improvements may later occur within territories without changing the logical service contract.

---

# FileTalk Inbox Intake

The inbox-intake territory observes files directly beneath:

```text
inbox/
```

It owns:

* polling;
* candidate file discovery;
* quiet-time handling;
* attempts to read one complete JSON object;
* tolerance of incomplete files;
* rejection or quarantine policy for permanently malformed files;
* ordering of eligible request candidates.

It does not validate Subete request semantics.

Its output is:

```text
a complete candidate FileTalk message file
```

The intake territory must not delete or mutate a message merely because its JSON is temporarily incomplete.

---

# Request Claiming

The request-claiming territory establishes processing ownership.

It moves an eligible request from:

```text
inbox/
```

to:

```text
inbox-processing/claimed/
```

It owns:

* collision-safe destination selection;
* ambiguous move detection;
* duplicate physical-file handling;
* preservation of original message contents;
* discovery of interrupted claimed requests at startup.

Its output is:

```text
one claimed request file owned by the service
```

Claiming does not imply that the request is valid or accepted.

---

# Request Parsing and Validation

The parsing-and-validation territory converts a claimed JSON object into a recognized Subete request.

It owns validation of:

* FileTalk-level message requirements;
* request ID;
* request type;
* response destination;
* transaction request structure;
* read request structure;
* search request structure;
* maintenance request structure;
* identifier formats;
* operation combinations;
* revision expectations;
* predicate structure;
* supported format versions.

It produces either:

```text
validated request data
```

or:

```text
structured failure data
```

It does not mutate authoritative state.

Protocol-specific validation may be divided into named functions by request family.

---

# Duplicate Request Resolution

The duplicate-resolution territory determines whether a request ID has already been observed.

It examines appropriate records such as:

* claimed requests;
* completed requests;
* failed requests;
* pending journals;
* committed journals.

It owns the rule:

> One request ID produces at most one logical execution.

It determines whether a repeated request should:

* resume incomplete pre-journal processing;
* associate with a pending transaction;
* reproduce a committed response;
* reproduce a previous failure;
* be rejected because the same request ID was reused with different content.

It does not invent a new outcome for an already completed request.

---

# Entity Storage

The entity-storage territory presents logical entity access over authoritative physical stores.

It owns operations such as:

```text
read complete logical entity
read selected aspects
test entity existence
write intended logical entity state
delete logical entity
enumerate entity IDs
```

It understands:

* entity files;
* revisions;
* aspect identifiers;
* filename encoding;
* any authoritative SQLite-backed aspects introduced later;
* which physical store is authoritative for each aspect.

Callers operate on logical entities rather than directly coordinating several stores themselves.

Entity storage does not decide whether a transaction is valid.

It applies or reads state specified by higher-level territories.

---

# Transaction Planning

The transaction-planning territory computes the complete effect of a validated transaction.

It owns:

* loading affected logical entities;
* checking expected revisions;
* validating create, change, and delete preconditions;
* applying operations to working copies;
* calculating final revisions;
* producing complete before-states;
* producing complete intended after-states;
* identifying no-op effects;
* identifying required storage changes;
* identifying link-cache consequences;
* constructing the logical success response.

Its principal output is a transaction plan containing enough information to construct the complete journal entry.

The plan exists only in memory until journal writing completes.

Transaction planning does not alter authoritative storage.

---

# Journal Writing

The journal-writing territory creates immutable transaction records.

It owns:

* allocating the next journal sequence;
* constructing the journal entry;
* selecting the journal filename;
* writing beneath `tmp/`;
* flushing and closing according to durability policy;
* moving the complete entry into `journal/pending/`;
* detecting filename or sequence conflicts.

Its successful output is:

```text
a complete immutable pending journal entry
```

Before that output exists, transaction application is forbidden.

The journal-writing territory does not apply entity mutations.

---

# Transaction Application

The transaction-application territory brings authoritative storage to a pending journal entry’s intended after-state.

It owns:

* applying entity creations;
* applying aspect changes;
* applying entity deletions;
* coordinating all authoritative stores;
* checking whether each component already matches before or after;
* making application idempotent;
* reconciling the link cache;
* confirming that the complete logical after-state has been established.

It operates from the journal entry, not from an unjournaled in-memory plan.

Its successful output is:

```text
all affected authoritative state matches journaled after-state
```

---

# Journal Commitment

The journal-commitment territory finalizes an applied transaction.

It owns:

* confirming application completion;
* moving the journal entry from `pending/` to `committed/`;
* handling an ambiguous interrupted move;
* advancing the recognized database generation;
* preserving sequence order;
* making the committed result available for response reconstruction.

Commitment is logically distinct from transaction application even when they are adjacent function calls.

Response delivery is not part of commitment.

---

# Recovery

The recovery territory runs before normal service begins and whenever explicit restoration invokes the same recovery logic.

It owns:

* inspecting temporary journal files;
* validating pending journal entries;
* resolving ambiguous pending and committed placement;
* completing partially applied transactions;
* finalizing already-applied transactions;
* reconciling generation;
* inspecting claimed requests;
* associating requests with journal outcomes;
* rebuilding or reconciling required derived structures;
* entering recovery-error state when safe resolution is impossible.

Recovery uses the same entity-storage, transaction-application, and journal-commitment functions used during normal processing.

Normal processing should not have one mutation implementation while recovery has another.

---

# Read Service

The read-service territory executes validated read requests.

It owns:

* selecting one committed generation;
* loading requested entities;
* selecting requested aspects;
* distinguishing found and missing entities;
* preserving entity revision information;
* constructing the logical read response.

It reads through the entity-storage territory.

It does not inspect a partially applied transaction state.

It does not advance generation or create journal records.

---

# Search Scanner

The search-scanner territory executes validated search requests.

Version 1 may scan logical entities directly.

It owns:

* enumerating entity IDs;
* loading the logical data required for predicates;
* applying search predicates;
* applying required Unicode comparisons;
* collecting matching entity IDs;
* sorting results;
* reporting the committed generation searched.

The scanner should be written so that a future index-backed implementation may replace internal scanning without changing search protocol semantics.

Search optimization belongs behind this territory.

---

# Link Cache Service

The link-cache territory owns the derived index of link entities.

It provides:

* incoming link lookup;
* outgoing link lookup;
* all-attached link lookup;
* transaction consequence planning;
* application of link-cache changes;
* generation recording;
* stale-state detection;
* complete rebuilding from authoritative link entities.

No other territory should modify link-cache files directly.

The link cache remains derived and rebuildable.

---

# Snapshot Service

The snapshot-service territory creates and validates full captures of authoritative state.

It owns:

* selecting a committed generation;
* establishing a consistent capture boundary;
* pausing transaction processing when required;
* copying or exporting every authoritative store;
* constructing the snapshot manifest;
* packaging the snapshot;
* validating the completed snapshot;
* publishing the completed artifact;
* reporting snapshot success or failure.

It does not write a checkpoint until snapshot validation succeeds.

The service runtime invokes this territory in response to a maintenance request or internal policy.

---

# Checkpoint Service

The checkpoint-service territory publishes recovery boundaries.

It owns:

* selecting a validated snapshot;
* confirming database identity and generation;
* determining `replay-after`;
* writing the checkpoint file;
* validating the checkpoint-to-snapshot relationship;
* listing usable recovery paths;
* determining which journal records remain required after the checkpoint.

It does not create the full snapshot itself.

A convenience operation may call:

```text
snapshot service
        ↓
checkpoint service
```

but the two responsibilities remain distinct.

---

# Maintenance and Removal Service

The maintenance territory determines which old artifacts may safely be archived or removed.

It owns:

* retention policy;
* dry-run planning;
* recovery-path analysis;
* identifying abandoned temporary files;
* identifying old completed and failed requests;
* identifying superseded snapshots and checkpoints;
* identifying committed journals outside all required retained recovery paths;
* performing approved removals;
* reporting exactly what was retained and removed.

It must preserve:

* all pending journals;
* the selected retained recovery paths;
* journals required after retained checkpoints;
* artifacts needed to reproduce unresolved request outcomes;
* the current database identity and authoritative stores.

Age alone is not proof that a recovery artifact is disposable.

---

# Status Publishing

The status-publishing territory writes:

```text
status/status.json
status/heartbeat.json
status/metrics.json
```

It owns:

* translating internal runtime facts into published formats;
* periodic heartbeat updates;
* state-transition publication;
* metrics counters and timing;
* best-effort operational counts;
* safe complete-file replacement.

It receives facts from other territories.

It does not determine whether a transaction committed.

Published status is a consequence of authoritative activity, not authority over it.

---

# Response Construction

The response-construction territory converts logical outcomes into protocol response objects.

It owns responses for:

* successful transactions;
* rejected transactions;
* reads;
* searches;
* duplicate requests;
* maintenance operations;
* snapshot and checkpoint requests;
* validation failures;
* recovery-related service rejection.

It preserves the original request ID and required generation information.

Construction is separate from physical delivery.

---

# Response Delivery

The response-delivery territory writes one response to the request’s SASE destination.

It owns:

* validating allowed response paths;
* constructing a destination filename when required;
* writing one complete UTF-8 JSON response;
* retry-safe replacement or duplicate delivery;
* reporting delivery success or failure.

It does not reverse or re-execute a committed transaction when delivery fails.

It should be usable equally by:

* normal request processing;
* duplicate-response reproduction;
* startup completion of interrupted post-commit work.

---

# Request Completion and Failure Records

The request-record territory concludes the physical request lifecycle.

It owns moving or recording requests beneath:

```text
inbox-processing/completed/
inbox-processing/failed/
```

Completed records preserve enough information to recognize duplicate requests and reproduce outcomes.

Failed records preserve:

* the request;
* structured error information;
* relevant generation;
* response-delivery result.

This territory does not decide transaction commitment.

A committed transaction may still have unfinished request-record work.

---

# GUI Monitor

The GUI-monitor territory implements `subete gui`.

It reads:

* `identity.json`;
* `status/status.json`;
* `status/heartbeat.json`;
* `status/metrics.json`;
* other explicitly public diagnostic files.

It may display:

* database identity;
* service availability;
* committed generation;
* heartbeat age;
* pending and completed request counts;
* recovery state;
* recent transaction information;
* link-cache state;
* snapshot and checkpoint information;
* storage and timing metrics.

The GUI must tolerate:

* missing files;
* partially rewritten JSON;
* stale status;
* a stopped service;
* database setup that is not yet complete.

It must never infer authority from status files.

---

# GUI Request Client

The GUI request-client territory creates FileTalk requests and observes their responses.

It owns:

* request ID generation;
* request object construction;
* SASE destination creation;
* writing into `inbox/`;
* tracking outstanding requests;
* reading responses;
* displaying success or structured failure.

The same client functions may support command-line commands such as:

```text
subete checkpoint
subete remove-old
```

The GUI should not have a private protocol implementation separate from the command-line maintenance clients.

---

# Dependency Direction

The intended dependency direction is approximately:

```text
lionscliapp command surface
        ↓
command entry points
        ↓
service runtime / GUI / maintenance clients
        ↓
request-family services
        ↓
transaction planning / reads / search / snapshots / checkpoints
        ↓
entity storage / journal storage / link cache / filesystem utilities
```

Cross-cutting outputs flow outward through:

```text
response construction
response delivery
status publishing
request records
```

Lower-level storage territories must not call the GUI or CLI command surface.

Protocol parsing must not directly manipulate entity files.

Search code must not write journals.

Status publication must not establish commitment.

---

# Shared Low-Level Utilities

Small shared utilities may support several territories.

Examples include:

* UTF-8 JSON reading and writing;
* complete-file replacement;
* filesystem-safe timestamps;
* UUID handling;
* entity ID filename encoding;
* journal sequence formatting;
* directory enumeration;
* checksum computation;
* retryable file reads;
* structured error creation.

These utilities should remain semantically small.

A generic utility module must not become an unstructured location for transaction policy.

---

# Suggested Initial Module Territories

The implementation may begin with modules resembling:

```text
subete/
  cli.py
  dbcontext.py
  layout.py

  service.py
  intake.py
  requests.py
  responses.py

  entities.py
  transactions.py
  journal.py
  recovery.py

  reads.py
  search.py
  links.py

  snapshots.py
  checkpoints.py
  maintenance.py

  status.py
  gui.py

  jsonfiles.py
  identifiers.py
  errors.py
```

These names are illustrative.

They are territories, not mandatory permanent module names.

A territory may initially occupy part of one module and later split when its implementation becomes large enough to justify it.

---

# Function and Data Orientation

The implementation should prefer named operations over objects that obscure state transitions.

Examples:

```text
discover_requests()
claim_request()
parse_request()
validate_transaction()
plan_transaction()
write_pending_journal()
apply_journal_entry()
commit_journal_entry()
recover_database()
execute_read()
execute_search()
create_snapshot()
write_checkpoint()
publish_status()
deliver_response()
complete_request()
fail_request()
```

Core data may use plain dictionaries or other transparent fixed-shape records:

```text
database context
validated request
transaction plan
journal entry
logical response
recovery finding
maintenance plan
```

The implementation may introduce classes where they provide clear value, but the architecture does not depend on assigning each territory to a class.

---

# Authority Boundaries

Only the following territories may change authoritative M1 state:

* transaction application;
* recovery, through transaction application;
* restoration, through recovery and authoritative store replacement.

Only journal writing allocates pending transaction sequence records.

Only journal commitment advances recognized generation.

Only the snapshot service creates full recovery captures.

Only the checkpoint service publishes checkpoint boundaries.

Only the maintenance service removes retained operational or recovery artifacts.

Only response delivery writes to external SASE destinations.

Only status publishing writes the public status surfaces.

The GUI and maintenance command clients are request producers, not alternate database writers.

---

# Version 1 Simplicity

Version 1 should favor a direct sequential pipeline:

```text
poll
claim
parse
validate
dispatch
respond
archive
repeat
```

For transactions:

```text
validate
plan
journal
apply
commit
respond
archive
```

For reads and searches:

```text
validate
execute against committed generation
respond
archive
```

For snapshot and maintenance requests:

```text
validate
perform controlled service operation
respond
archive
```

The architecture should not introduce worker pools, event buses, dependency injection frameworks, repository classes, or elaborate object graphs unless a demonstrated implementation need appears.

The important partition is semantic responsibility, not ceremony.

---

# Non-Negotiable Rules

* `execpath.dbroot` identifies the database root for every command.
* Only one authoritative service may own a database root at a time.
* The GUI may have multiple instances because it observes status files and communicates through FileTalk.
* The GUI never directly mutates authoritative state.
* Maintenance commands should normally request work from the running service rather than race it on disk.
* Request intake, claiming, validation, planning, journaling, application, and commitment remain distinct responsibilities.
* Entity storage hides the physical partition of logical entities across authoritative stores.
* Transaction application operates from the durable journal entry.
* Recovery reuses normal application and commitment logic.
* Reads and searches observe one committed generation.
* Snapshots and checkpoints remain distinct services and artifacts.
* Status publication and response delivery do not determine transaction commitment.
* Territories define ownership and dependency direction without requiring a class hierarchy.
