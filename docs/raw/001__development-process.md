```
title: Initial Development Process
chatgpt: https://chatgpt.com/c/6a61091b-e724-83e8-9059-b23c3afc6674
date: 2026-07-22
updated: 2026-07-23
```

## Subete — Preparation and Implementation Sequence

**10. Create the project and repository.**
Create the project directory, initialize it using your normal project structure, register it with Zoo/Zookeep, create the Git repository, create the GitHub repository, add the usual license and packaging files, and make the first clean commit.

**20. Establish the documentation structure.**
Create the initial directories:

```text
docs/
  code/
    formats/
    tests/
    walking-examples/
  raw/
```

Also make it explicit in the project guide that `docs/code/` is the agent-maintained technical specification for Subete.

**30. Write the one-page Big Picture document with Wing-Cat.**
Talk with me and jointly produce `docs/code/big-picture.md`, explaining what Subete is, what problem it solves, the idea of one authoritative M1 world, FileTalk access, transactions, search services, journaling, generations, snapshots, and checkpoints.

**40. Write the Anticipated Development Process with Wing-Cat.**
Create `docs/code/anticipated-process.md`, describing the intended sequence of specification, implementation, testing, review, and later optimization. Make clear that correctness and recoverability come before caching, indexing, sharding, and performance work.

**50. Write the system invariants with Wing-Cat.**
Create `docs/code/invariants.md`. Define the non-negotiable rules, including:

* `entities/` is authoritative.
* Only the running Subete writer mutates authoritative files.
* A complete journal entry must exist before datastore mutation begins.
* A transaction is applied completely or recovered to completion.
* Journal sequence and database generation are the same number.
* Reads and searches observe committed state only.
* Search indexes, when later introduced, are derived and rebuildable.
* Cache, when later introduced, reflects disk state only.

**60. Define the Version 1 filesystem layout.**
Write a focused document such as `docs/code/filesystem-layout.md`, specifying the initial tree:

```text
subete-data/
  identity.json
  configuration.json
  lock.json

  entities/

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

Define what owns each directory and which contents are authoritative, derived, temporary, archival, or public.

**65. Define the Version 1 link cache with Wing-Cat.**
Create `docs/code/link-cache.md`. Define the derived structure used to locate link entities attached to any entity without scanning the entire datastore. Specify:

* how links are recognized from their link aspect;
* how link entities are indexed by their `from` and `to` endpoints;
* the filesystem layout and file formats of `link-cache/`;
* how callers request incoming, outgoing, or all attached links;
* how the cache is updated when link entities are created, changed, or deleted;
* how the cache participates in transaction application and recovery;
* how its generation is recorded and compared with the database generation;
* how it is rebuilt entirely from authoritative link entities;
* how Subete behaves when the cache is absent, stale, or undergoing reconstruction.

The link cache is derived and rebuildable. Link entities in the authoritative datastore remain the sole authority for relationships.


**70. Design the CRUD and read protocol with Wing-Cat.**
Create `docs/code/protocol-crud.md` as a Markdown SoftSpec. Define:

* the common FileTalk request envelope;
* transaction requests;
* read requests;
* SASE reply destinations;
* batched operations;
* `create-entity`;
* `set-aspect`;
* `delete-aspect`;
* `delete-entity`;
* whole-aspect replacement;
* batched reads across multiple entities;
* requesting selected aspects or all aspects;
* success, failure, and not-found responses;
* request IDs and duplicate-request behavior.

**80. Design the search protocol with Wing-Cat.**
Create `docs/code/protocol-search.md` as a Markdown SoftSpec. Define Version 1 searches for:

* `basic.typehint`;
* aspect presence;
* required tags;
* substring within `basic.name`;
* substring within `basic.title`;
* combinations of those predicates;
* multiple searches within one request.

Settle case sensitivity, tag semantics, AND behavior, response ordering, and whether results contain only entity IDs.

**90. Define all on-disk JSON formats with Wing-Cat.**
Create focused documents beneath `docs/code/formats/`, likely including:

```text
identity.md
configuration.md
entity.md
transaction-request.md
read-request.md
search-request.md
response.md
journal-entry.md
checkpoint.md
snapshot-manifest.md
status.md
heartbeat.md
metrics.md
```

Specify both JSON content and filename conventions.

**100. Design the transaction and recovery state machine with Wing-Cat.**
Create `docs/code/state.md`. Describe the states and transitions for:

* inbox request discovered;
* request claimed;
* request validated;
* transaction planned;
* journal write started;
* journal complete;
* entity mutation in progress;
* entity mutation complete;
* journal committed;
* response delivered;
* request completed or failed.

Include startup behavior for every recoverable intermediate state.

**110. Define the snapshot and checkpoint lifecycle with Wing-Cat.**
Create `docs/code/snapshot-checkpoint-lifecycle.md`. Keep snapshots and checkpoints distinct:

* A snapshot is a full capture of authoritative state at a generation.
* A checkpoint is a small recovery marker describing the recovery boundary.
* Specify how snapshots are created.
* Specify when checkpoints are written or advanced.
* Specify which journal records remain necessary.
* Specify restoration and journal replay.

**120. Write the implementation partition with Wing-Cat.**
Create `docs/code/implementation-partition.md`. Divide the program into clear responsibilities such as:

* lionscliapp command surface;
* FileTalk inbox intake;
* request claiming;
* request parsing and validation;
* entity storage;
* transaction planning;
* journal writing;
* transaction application;
* recovery;
* read service;
* search scanner;
* snapshot service;
* checkpoint service;
* status publishing;
* response delivery.

This should define territories, not prematurely force a class hierarchy.

**130. Write the first walking example with Wing-Cat.**
Create a complete example under `docs/code/walking-examples/` showing:

1. two entities and one link being created in one transaction;
2. the resulting pending and committed journal records;
3. the entity files after commit;
4. a batched read;
5. a combined search;
6. generation advancement;
7. status output.

Use concrete UUIDs, filenames, JSON documents, and responses.

**140. Write the crash-recovery walking example with Wing-Cat.**
Create another example showing a multi-entity transaction interrupted after only some entity files were changed. Show how startup reads the completed journal entry, compares before and after states, finishes application, commits the journal record, and returns the database to one coherent generation.

**150. Build the failure-injection test matrix with Wing-Cat.**
Create `docs/code/tests/failure-injection.md`. Name every meaningful crash boundary, including:

* before journal creation;
* during journal writing;
* after journal completion;
* before the first entity write;
* between entity writes;
* after all entity writes;
* before journal commitment;
* after commitment but before response delivery;
* after response delivery but before request archival.

For each boundary, define the expected state before restart and expected recovery result.

**160. Review the complete specification folder together.**
Have Wing-Cat inspect all of `docs/code/` for contradictions, missing transitions, underspecified formats, inconsistent terminology, unclear ownership, and operations that cannot be recovered safely.

**170. Commit the completed Version 1 specification.**
Make a clean Git commit containing the reviewed `docs/code/` specification. Do not begin implementation until this commit is stable enough to serve as the implementation target.

**180. Create the Version 1 scope index.**
Write `docs/raw/###__version1-scope-index.json` after the specification commit. Include:

* the exact Git commit hash;
* the Version 1 designation;
* the complete list of governing specification files;
* the role or reason for including each file;
* any explicitly excluded exploratory files.

Commit the scope index separately.

**190. Ask Codex to design the implementation.**
Give Codex the entire `docs/code/` tree and the Version 1 scope index. Ask it to propose:

* package structure;
* module boundaries;
* internal data flow;
* command structure;
* testing strategy;
* failure-injection mechanism;
* staged implementation order.

Have Codex produce a design document, not code yet.

**200. Review Codex’s implementation design.**
Review the design with Wing-Cat. Compare it against the invariants, state machine, recovery contract, and your programming guides. Remove unnecessary architecture, premature abstraction, caching, indexing, concurrency, or generalized database machinery.

**210. Have Codex implement the storage and format foundations.**
Implement configuration loading, identity handling, entity-file reading and writing, request parsing, response writing, filenames, directory setup, and basic lionscliapp commands.

2026-07-23 update: include root generation.json, FileTalk stale-file/reply-path configuration, and strict sequential service scaffolding.

**220. Have Codex implement read operations.**
Implement batched reads for selected aspects and all aspects, with generation reporting and clearly differentiated entity-not-found and aspect-not-found results.

**230. Have Codex implement transaction planning without mutation.**
Implement validation and computation of complete before-and-after entity states, but initially stop before writing journals or changing authoritative entity files. Test the planner extensively.

**240. Have Codex implement journaling and transaction application.**
Implement sequence allocation, pending journal creation, completion detection, entity-file mutation, committed-journal transition, generation advancement, and transaction responses.

2026-07-23 update: include Version 1 link-cache preparation/publication with transaction application. It is required derived infrastructure, not deferred caching.

**250. Have Codex implement startup recovery.**
Implement handling for incomplete journal files, complete pending journal entries, partially applied transactions, fully applied but uncommitted transactions, and duplicate request delivery.

2026-07-23 update: explicitly cover root-generation publication and cache states: prepared/updating, journal committed, root generation published, cache current.

**260. Have Codex implement full-scan search.**
Implement Version 1 search by scanning `entities/` directly. Do not add in-memory or on-disk indexes yet. Support every predicate and combination defined in the search protocol.

**270. Have Codex implement status publication.**
Implement `status.json`, `heartbeat.json`, and `metrics.json`, including current generation, process state, counts, last commit, queue depth, and recovery activity where appropriate.

**280. Have Codex implement snapshots and checkpoints.**
Implement snapshot creation, snapshot manifests, checkpoint records, restoration, and replay from the checkpoint boundary.

2026-07-23 update: snapshots/checkpoints remain valid, but functional checkpoint/remove-old commands need a specified maintenance FileTalk family before implementation; do not invent it ad hoc.

**290. Run the ordinary functional test suite.**
Test creation, replacement, deletion, batched reads, all-aspect reads, search predicates, combined searches, malformed requests, duplicate requests, snapshots, checkpoints, and restoration.

2026-07-23 update: include link-cache lookup/rebuild, dangling endpoint behavior, direct/incomplete FileTalk delivery, and repeat read/search behavior.

**300. Run the complete crash-boundary test suite.**
Inject failure at every named durable boundary and verify that restart always produces the correct authoritative state, correct generation, correct journal state, and safe request outcome.

2026-07-23 update: explicitly cover root-generation publication and cache states: prepared/updating, journal committed, root generation published, cache current.

**310. Perform a manual walking-example verification.**
Run the documented examples against the real implementation and confirm that actual files and responses match the specification. Correct either the implementation or the specification wherever they disagree.

**320. Conduct a Version 1 completion review with Wing-Cat.**
Review the finished system against the scope index and invariants. Confirm that no deferred systems—caching, sharding, persistent search indexes, layering, or generalized runtime behavior—have accidentally entered Version 1.

2026-07-23 update: change “no deferred systems—caching...” to “no deferred systems—other than the required Version 1 link cache—such as sharding, persistent search indexes, layering, or generalized runtime behavior.”

**330. Tag and preserve Version 1.**
Create the final Version 1 commit, update or create the corresponding frozen scope index with the implementation commit as appropriate, tag the release in Git, and preserve a known-good snapshot of a test Subete world.
