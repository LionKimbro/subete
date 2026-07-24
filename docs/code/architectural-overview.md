# Subete — Big Picture

## Purpose

Subete is a single authoritative database for M1 entities.

It maintains one persistent world of entities, aspects, and links, and makes that world available to programs through a FileTalk request interface. It is intended to become a shared memory system for applications that need to store, retrieve, connect, search, and safely modify complex structured information.

Subete is not merely a collection of M1 files. It is a long-running database process that sits above an authoritative filesystem representation and provides transactional access, recovery, search, status reporting, snapshots, and historical continuity.

The name *Subete* means “everything.” The aspiration is not that every possible thing must be stored in one rigid schema, but that many different kinds of things can coexist within one shared space of stable identities.

## The Problem

Many programs maintain their own isolated data:

* projects;
* people;
* files;
* events;
* notes;
* software components;
* documents;
* products;
* conversations;
* timelines;
* relationships among all of these.

Each application tends to invent its own storage format, identifiers, indexes, and connection model. Information becomes fragmented across programs, and links between domains are difficult to preserve.

Subete provides one common substrate.

Applications may continue to have their own interfaces, workflows, and specialized behavior, but they can share a common world of M1 entities. A person represented in one program can be the same entity referenced by another. A project can link to documents, software repositories, events, conversations, and people without requiring all of those systems to share one application-specific schema.

## One Authoritative M1 World

Subete maintains one current authoritative state.

Each entity has a stable identifier and a collection of aspects. Meaning and structure are expressed through those aspects. Links are themselves entities containing link aspects, so relationships participate in the same storage and identity model as everything else.

Subete does not interpret multiple layers of competing M1 documents. It does not maintain runtime overlays or document priority orders. It stores the materialized world directly.

The authoritative entity files are the database.

Other structures—status displays, snapshots, the Version 1 link cache, and search indexes introduced in later versions—are derived from or describe that authoritative state. They must never become competing sources of truth.

In Version 1, entity files are stored directly under `entities/`, without sharding. The Version 1 link cache is the sole cache: it is a required, rebuildable derived index for attached-link lookup, not a competing source of truth. Simplicity, inspectability, and correctness take priority over scale optimizations.

## The Subete Process

Subete runs as a single authoritative database process.

Only that process may modify the database’s internal files. External programs do not directly edit entity files, journals, checkpoints, or database metadata. Instead, they submit FileTalk requests to Subete.

This single-writer design allows transactions to be serialized and makes consistency, recovery, locking, and journal sequencing much easier to reason about.

The surrounding command-line application is built with `lionscliapp`, which provides process-locking behavior. Some commands, such as starting the database service, require exclusive locking. Other commands, such as reporting the current number of entities, may operate without taking the full service lock where that is safe.

## FileTalk Access

Programs interact with Subete through an inbox-based FileTalk protocol.

A request is written into the database inbox. Subete claims the request, processes it, and writes its response to the return destination specified by the request. This return destination follows the SASE principle: the request carries its own self-addressed return path.

The first version supports four broad request families:

* transaction requests;
* read requests;
* search requests;
* maintenance requests.

These are separate request types with separate semantics.

Transaction requests change the world. Read requests retrieve known entity aspects. Search requests discover entity identifiers matching specified conditions.

Maintenance requests ask the running service to create a snapshot/checkpoint,
remove safely disposable old artifacts, or stop through normal shutdown.
Maintenance does not mutate the M1 entity world or advance its generation.

Multiple operations, reads, or searches may be included in a single request.

## Transactions

All changes to authoritative state are submitted as transactions.

A transaction may affect multiple aspects across multiple entities. It may create entities, create or replace aspects, delete aspects, or delete entities.

The transaction is treated as one unit. Either its complete intended result becomes the authoritative state, or recovery continues the transaction until that result is reached.

Version 1 uses whole-aspect replacement rather than nested patch operations. A caller reads an aspect, modifies it locally, and submits the complete replacement value. This keeps transaction meaning explicit and avoids introducing a complex patch language.

Before changing authoritative files, Subete:

1. reads the affected current entity states;
2. validates the entire request;
3. computes the complete before and after states;
4. assigns the next journal sequence;
5. writes the full transaction to the journal.

Only after the journal record is complete may Subete begin changing entity files.

## Reads

Read requests retrieve committed entity state.

A request may ask for:

* specific aspects on an entity;
* all known aspects on an entity;
* multiple aspects across multiple entities.

Version 1 returns aspects wholesale. It does not provide field-level extraction from inside aspect values.

Read responses clearly distinguish among:

* an entity that exists;
* an entity that does not exist;
* an aspect that exists;
* an aspect that is absent.

Each response reports the database generation from which the results were read.

## Search Services

Subete is not only a CRUD service. It is also a search service over the M1 world.

Version 1 supports searches such as:

* all entities with a specified `basic.typehint`;
* all entities containing a specified aspect;
* all entities containing a required collection of tags;
* all entities whose `basic.name` contains a substring;
* all entities whose `basic.title` contains a substring;
* link entities whose `from` endpoint is a specified entity;
* link entities whose `to` endpoint is a specified entity;
* link entities attached in either direction to a specified entity;
* combinations of these conditions.

A request may contain multiple searches.

Version 1 performs ordinary searches by scanning authoritative entity files
directly. Link endpoint predicates may use the required current link cache as
an internal optimization. The public search protocol returns matching link
entity IDs and does not expose cache representation. Version 1 does not
maintain persistent or in-memory search indexes.

Later versions may introduce derived indexes for:

* tags;
* aspect presence;
* typehints;
* names;
* titles;
* general text search;
* links and link direction.

Those indexes must remain rebuildable from authoritative entity files and must report the generation through which they are current.

## Journal

The journal is Subete’s write-ahead history of transactions.

Every transaction receives a monotonically increasing journal sequence number. A journal entry records:

* the originating request;
* the affected entities;
* their complete relevant state before the transaction;
* their intended complete state after the transaction;
* transaction metadata;
* the assigned sequence number.

The journal entry must be complete before authoritative entity mutation begins.

If Subete crashes while writing a journal entry, no datastore changes have yet been permitted. The incomplete journal file can be discarded and the original request retried.

If Subete crashes after the journal is complete but before all entity files have been updated, recovery can inspect each affected entity:

* entities matching the intended after-state are already complete;
* entities matching the before-state still need the transaction applied;
* entities matching neither state indicate an unexpected inconsistency.

Because replaying the journal entry leads to the same intended after-state, transaction application is designed to be idempotent.

Pending journal entries represent transactions that may still require application or finalization. Committed journal entries represent transactions whose authoritative changes have been completed.

## Generations

The database generation is the sequence number of the latest fully committed journal transaction.

The journal sequence and database generation use the same numbering system.

When transaction 143 commits, the database enters generation 143.

Generations provide a shared consistency language across Subete:

* read responses identify the generation observed;
* transaction responses identify the generation committed;
* status files report the current generation;
* snapshots identify the generation captured;
* checkpoints identify recovery boundaries;
* the Version 1 link cache and future indexes report the generation through which they are current.

A generation identifies an authoritative state of the Subete world.

## Snapshots

A Version 1 snapshot is a complete preserved copy of the authoritative
`entities/` store at a specific generation.

Snapshots exist to make backup, restoration, transport, and historical preservation practical without requiring replay from the beginning of the journal.

A snapshot includes a manifest identifying at least:

* the database identity;
* the generation captured;
* the time of capture;
* the entity data included.

The archive contains only `entities/` and `snapshot-manifest.json`. It does
not contain configuration, framework configuration, identity or generation
files, locks, journals, checkpoints, FileTalk processing state, status data,
temporary files, or derived link-cache data.

Snapshots are large state artifacts. They preserve the world as it existed at a defined generation.

## Checkpoints

A checkpoint is a small recovery marker.

It is distinct from a snapshot.

A checkpoint records what durable recovery boundary has been established—for example, which snapshot is accepted as a recovery base and through which journal generation that base represents authoritative state.

During restoration, Subete can:

1. load the checkpointed snapshot;
2. replace the authoritative entity store;
3. publish the snapshot generation;
4. replay applicable later journals through normal recovery;
5. rebuild derived structures.

Restoration never reads, merges, replaces, preserves, or otherwise operates
on `configuration.json`. Valid machine-local configuration must already exist
at the destination.

Snapshots contain state. Checkpoints describe the recovery boundary and how journal replay should proceed.

Keeping them separate allows recovery metadata to advance, be inspected, and be reasoned about independently from the large snapshot artifacts themselves.

## Status Surface

Subete publishes a read-only status surface under `status/`.

This surface allows people and programs to inspect the database without modifying it. It may report:

* whether the service is starting, recovering, ready, or stopping;
* the current generation;
* the most recent commit;
* entity counts;
* inbox and processing counts;
* recovery activity;
* snapshot and checkpoint information;
* search or index freshness in later versions;
* operational metrics;
* heartbeat information.

The status surface is descriptive and derived. It is not authoritative database state.

## Recovery and Failure Testing

Crash recovery is a central feature, not an afterthought.

Subete must be tested at every meaningful durability boundary, including crashes:

* before journal creation;
* during journal writing;
* after journal completion;
* before entity mutation;
* between entity-file updates;
* after all entity updates;
* before journal commitment;
* after commitment but before response delivery;
* after response delivery but before request archival.

After every simulated crash, restarting Subete must produce the correct authoritative world, generation, journal state, and request outcome.

Ordinary CRUD and search tests prove that the system works when everything goes well. Failure-injection tests prove that the database can be trusted.

## Version 1 Direction

Version 1 aims to be small, complete, and recoverable.

It includes:

* one authoritative M1 world;
* filesystem-backed entity storage;
* FileTalk requests and SASE responses;
* atomic multi-entity transactions;
* batched reads;
* full-scan search;
* write-ahead journaling;
* generations;
* startup recovery;
* snapshots;
* checkpoints;
* public status reporting;
* the rebuildable link cache for attached-link lookup;
* crash-boundary testing.

It deliberately postpones:

* entity-directory sharding;
* persistent search indexes;
* in-memory indexes;
* generalized nested patch operations;
* multiple writers;
* distributed operation;
* M1 document layering and priority interpretation.

The first goal is not to build the most sophisticated database possible.

The first goal is to create a clear, durable, inspectable M1 world that many programs can safely share.
