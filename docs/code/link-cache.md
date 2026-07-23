# Subete — Version 1 Link Cache

The Version 1 link cache is a derived filesystem structure used to locate link entities attached to any entity without scanning the entire authoritative datastore.

It answers questions such as:

* which link entities point outward from this entity;
* which link entities point inward to this entity;
* which link entities are attached in either direction.

The cache is derived and rebuildable.

Authoritative link entities remain the sole authority for relationships.

---

# Purpose

Without a link cache, finding all links attached to one entity would require scanning every entity in the datastore and examining every link aspect.

The link cache provides direct lookup by endpoint.

It does not replace link entities.

It does not contain authoritative relationship meaning beyond identifiers copied from authoritative link entities.

---

# Recognizing Link Entities

An entity is recognized as a link when it contains the link aspect:

```text
tag:m1lattice.net,2026/aspect/link
```

A valid link aspect contains:

```json
{
  "from": "11111111-1111-4111-8111-111111111111",
  "to": "22222222-2222-4222-8222-222222222222",
  "relationship": "participates-in"
}
```

## Required Endpoint Fields

```json
{
  "from": "<entity-id>",
  "to": "<entity-id>"
}
```

Both endpoints are required.

The `relationship` field and any additional link-aspect fields describe the relationship but do not determine cache placement.

## Endpoint Validity

Each endpoint must identify an entity that:

* already exists in the committed database; or
* will exist after the same transaction commits.

A transaction that would leave a committed link pointing to a nonexistent endpoint is invalid.

---

# Authority

The authoritative facts are:

* the link entity exists;
* the link entity contains a link aspect;
* the link aspect contains its `from` and `to` endpoints.

The link cache merely repeats enough information to locate that link entity efficiently.

If the cache disagrees with the authoritative link entity, the authoritative entity wins.

---

# Filesystem Layout

The Version 1 link cache is stored beneath:

```text
subete-data/
  link-cache/
    generation.json
    outgoing/
    incoming/
```

Each endpoint entity may have one outgoing cache file and one incoming cache file.

Example:

```text
link-cache/
  generation.json

  outgoing/
    11111111-1111-4111-8111-111111111111.json

  incoming/
    22222222-2222-4222-8222-222222222222.json
```

Entity IDs are encoded using the same filename encoding rules used elsewhere in Subete.

For UUID entity IDs, the UUID appears unchanged.

For entity IDs requiring filesystem encoding, the encoded filename must decode unambiguously back to the original entity ID.

---

# Cache Generation File

## Location

```text
link-cache/generation.json
```

## Format

```json
{
  "link-cache-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 42,
  "updated": "2026-07-23T23:40:01Z",
  "state": "current"
}
```

## Fields

### `link-cache-format-version`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

Identifies the Version 1 link-cache format.

### `database-id`

```json
{
  "type": "uuid",
  "required": true
}
```

The database identity represented by the cache.

It must match `identity.json`.

### `generation`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 0
}
```

The committed database generation completely represented by the cache.

### `updated`

```json
{
  "type": "timestamp",
  "required": true
}
```

The UTC time at which the cache generation record was last completed.

### `state`

```json
{
  "type": "string",
  "required": true
}
```

Recommended values are:

```text
current
rebuilding
stale
error
```

Ordinary ready-state operation requires:

```text
state = current
```

and:

```text
link-cache generation = database generation
```

---

# Outgoing Cache Files

An outgoing cache file lists link entities whose `from` endpoint is the named entity.

## Location

```text
link-cache/outgoing/<encoded-entity-id>.json
```

## Example

```text
link-cache/outgoing/11111111-1111-4111-8111-111111111111.json
```

## Format

```json
{
  "link-cache-entry-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 42,
  "entity": "11111111-1111-4111-8111-111111111111",
  "direction": "outgoing",
  "links": [
    "33333333-3333-4333-8333-333333333333"
  ]
}
```

## Meaning

The file states that the listed link entities currently have:

```text
from = entity
```

at the recorded generation.

---

# Incoming Cache Files

An incoming cache file lists link entities whose `to` endpoint is the named entity.

## Location

```text
link-cache/incoming/<encoded-entity-id>.json
```

## Example

```text
link-cache/incoming/22222222-2222-4222-8222-222222222222.json
```

## Format

```json
{
  "link-cache-entry-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 42,
  "entity": "22222222-2222-4222-8222-222222222222",
  "direction": "incoming",
  "links": [
    "33333333-3333-4333-8333-333333333333"
  ]
}
```

## Meaning

The file states that the listed link entities currently have:

```text
to = entity
```

at the recorded generation.

---

# Cache Entry Fields

## `link-cache-entry-format-version`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

Identifies the cache-entry format.

## `database-id`

```json
{
  "type": "uuid",
  "required": true
}
```

The database identity represented by the file.

## `generation`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 0
}
```

The committed database generation represented by this entry.

## `entity`

```json
{
  "type": "entity-id",
  "required": true
}
```

The endpoint entity whose attached links are listed.

It must agree with the filename.

## `direction`

```json
{
  "type": "string",
  "required": true,
  "allowed": [
    "incoming",
    "outgoing"
  ]
}
```

The endpoint role represented by this file.

## `links`

```json
{
  "type": "array",
  "required": true,
  "items": {
    "type": "entity-id"
  }
}
```

The link entity IDs attached in the stated direction.

Link IDs appear at most once.

They are sorted in ascending Unicode codepoint order by complete entity ID.

---

# Empty Entries

An endpoint with no links in a direction does not require a cache file for that direction.

For example, if an entity has no outgoing links:

```text
link-cache/outgoing/<entity>.json
```

may be absent.

An absent cache entry means:

```text
no links in that direction
```

only when the cache as a whole is known to be current for the database generation.

An absent file in a stale or incomplete cache proves nothing.

---

# Caller Interface

Callers request attached links through the link-cache service rather than opening cache files directly.

Conceptual operations are:

```text
get_outgoing_links(entity)
get_incoming_links(entity)
get_attached_links(entity)
```

## Outgoing Links

Returns link entity IDs whose authoritative link aspect has:

```text
from = entity
```

## Incoming Links

Returns link entity IDs whose authoritative link aspect has:

```text
to = entity
```

## All Attached Links

Returns the union of incoming and outgoing link IDs.

A self-link whose `from` and `to` endpoints are the same entity appears only once in the combined result.

All returned link IDs are sorted and unique.

---

# Returned Information

The Version 1 link-cache lookup returns link entity IDs.

It does not return:

* the relationship value;
* the opposite endpoint;
* the complete link aspect;
* the complete link entity.

Callers that need those facts read the returned authoritative link entities through the normal read or entity-storage service.

This keeps the cache small and prevents it from becoming a second authority for link meaning.

---

# Link Creation

When a transaction creates a link entity:

1. the link entity is validated;
2. its `from` and `to` endpoints are included in transaction planning;
3. the complete pending journal entry is written;
4. the authoritative link entity is created;
5. the link ID is added to the outgoing entry for `from`;
6. the link ID is added to the incoming entry for `to`;
7. affected cache files are written with the transaction generation;
8. the cache generation is advanced only when all required cache changes are complete;
9. the journal transaction is committed.

Example:

```text
link entity:
33333333-3333-4333-8333-333333333333

from:
11111111-1111-4111-8111-111111111111

to:
22222222-2222-4222-8222-222222222222
```

produces:

```text
outgoing/11111111-1111-4111-8111-111111111111.json
    includes 33333333-3333-4333-8333-333333333333

incoming/22222222-2222-4222-8222-222222222222.json
    includes 33333333-3333-4333-8333-333333333333
```

---

# Link Change

When a transaction changes a link aspect, transaction planning compares the old and new endpoints.

For example:

```text
before:
from = A
to   = B

after:
from = A
to   = C
```

requires:

* no change to outgoing `A`;
* removal of the link ID from incoming `B`;
* addition of the link ID to incoming `C`.

If both endpoints change:

```text
before:
from = A
to   = B

after:
from = C
to   = D
```

requires:

* removal from outgoing `A`;
* removal from incoming `B`;
* addition to outgoing `C`;
* addition to incoming `D`.

If the link aspect is removed entirely, the entity ceases to be recognized as a link and is removed from both endpoint indexes.

If a non-link entity gains a valid link aspect, it is added to both indexes.

---

# Link Deletion

When a link entity is deleted:

1. transaction planning reads its authoritative link aspect;
2. the transaction journal records the complete before-state and null after-state;
3. the authoritative entity is deleted;
4. its link ID is removed from the outgoing file for `from`;
5. its link ID is removed from the incoming file for `to`;
6. empty cache entry files may be deleted;
7. cache generation is advanced with transaction completion.

Deleting an endpoint entity is invalid while committed link entities would continue to refer to it, unless the same transaction also deletes or changes every affected link so that no dangling endpoint remains.

---

# Transaction Planning

Transaction planning determines the complete cache consequences before journal writing.

The plan identifies:

* outgoing entries to add;
* outgoing entries to remove;
* incoming entries to add;
* incoming entries to remove;
* cache entry files that will become empty;
* the resulting cache generation.

The authoritative journal remains centered on logical entity before-states and after-states.

The cache consequences may be recomputed from those journaled states during application or recovery.

The link cache does not need to become authoritative journal content.

---

# Transaction Application

The link cache participates in transaction application because Subete must not present a newly committed generation with an older link cache as though it were current.

For each transaction affecting links:

1. apply the authoritative entity after-states;
2. apply all required link-cache entry changes;
3. verify affected cache entries;
4. write the cache generation record for the new generation;
5. finalize journal commitment.

The exact physical write order may vary, but Subete must not publish:

```text
link-cache state = current
```

for the new generation until all cache changes for that generation are complete.

---

# Recovery

Recovery derives required cache changes from the pending journal entry’s authoritative before-states and after-states.

For each affected entity:

* a non-link before-state and link after-state means add the link;
* a link before-state and non-link after-state means remove the link;
* link states with changed endpoints mean move the index entries;
* identical link endpoints require no membership change;
* a deleted link after-state means remove the old memberships.

Recovery may safely repeat cache writes.

Adding an already-present link ID is a no-op.

Removing an already-absent link ID is a no-op.

After the authoritative transaction after-state and all required cache entries are correct, recovery writes the cache generation and completes journal commitment.

---

# Generation Comparison

The link cache is current only when all of the following are true:

```text
generation.json exists
state = current
database-id matches identity.json
cache generation = committed database generation
```

## Cache Behind the Database

If:

```text
cache generation < database generation
```

the cache is stale.

Subete must not use it as a complete answer for current links.

## Cache Ahead of the Database

If:

```text
cache generation > database generation
```

the cache is inconsistent.

Subete enters recovery or cache-error handling.

It must not trust the cache as current.

## Entry Generation Mismatch

Each entry file should record the generation at which it was last written.

An entry generation older than the global cache generation may still be valid if no attached links changed since that earlier generation.

The global `generation.json` is the declaration that the complete cache represents the current world.

During validation or rebuilding, Subete may verify individual entry generations as additional diagnostic information.

---

# Cache Rebuild

The entire cache can be rebuilt from authoritative link entities.

A rebuild proceeds as follows:

1. select one committed database generation;
2. prevent that generation from changing during the authoritative scan, or use another coherent-view mechanism;
3. create a new temporary cache workspace;
4. scan all authoritative entities;
5. identify every entity containing a valid link aspect;
6. add each link ID beneath its `from` endpoint;
7. add each link ID beneath its `to` endpoint;
8. sort and deduplicate every entry;
9. write all outgoing and incoming files;
10. write a generation record with `state` set appropriately;
11. validate the rebuilt cache;
12. replace the old cache with the completed rebuilt cache;
13. publish `state = current` at the captured generation.

The existing cache must not be destroyed before the replacement is complete unless no current cache exists and normal service remains unavailable.

---

# Rebuild Workspace

A rebuild should occur beneath a temporary location such as:

```text
tmp/link-cache-rebuild/
```

or:

```text
link-cache.rebuilding/
```

The temporary structure must not be mistaken for the active cache.

Only after the full rebuild completes may it replace:

```text
link-cache/
```

Replacement should preserve either:

* the old complete cache; or
* the new complete cache;

rather than exposing a half-built active directory as current.

---

# Cache Absent

If `link-cache/` is absent:

* authoritative entities remain valid;
* transactions and recovery still have authoritative meaning;
* link lookup through the cache is unavailable;
* Subete may rebuild the cache from authoritative link entities.

For Version 1, the service should rebuild the cache before announcing ordinary `ready` state if link lookup is part of the promised running service.

A maintenance or recovery state may remain available while rebuilding.

---

# Cache Stale

If the cache generation is older than the committed database generation:

* Subete must not return cache results as complete current answers;
* status reports the cache as `stale`;
* Subete reconciles missing journal consequences or performs a full rebuild;
* normal link lookup waits, fails explicitly, or uses an authoritative fallback scan according to service policy.

Version 1 should prefer rebuilding or reconciling before announcing `ready`, rather than silently performing unpredictable full-store scans during ordinary requests.

---

# Cache Rebuilding

While reconstruction is in progress:

* status reports `rebuilding`;
* the temporary cache is not used as current;
* callers must not observe partial rebuilt results;
* authoritative link entities remain unchanged;
* transaction processing may pause if required to preserve one coherent generation.

After successful rebuild, the cache generation must equal the committed database generation before its state becomes `current`.

---

# Cache Error

If the cache is malformed, belongs to another database, or cannot be reconciled:

* Subete reports `error`;
* the cache is not trusted;
* authoritative link entities remain the relationship authority;
* Subete may quarantine the cache and perform a full rebuild.

A link-cache error alone does not justify modifying authoritative link entities.

If the cache is required for ready-state service and cannot be rebuilt, Subete must not falsely publish itself as fully ready.

---

# Reads and Searches

Ordinary entity reads do not require the link cache unless the caller explicitly requests attached-link lookup.

Searches over authoritative link aspects may scan authoritative entities or use a future search index.

The link cache is specifically optimized for endpoint attachment lookup.

It must not silently change the semantics of normal read or search protocols.

---

# Status Publication

`status.json` may publish:

```json
{
  "link-cache": {
    "state": "current",
    "generation": 42
  }
}
```

Other examples include:

```json
{
  "link-cache": {
    "state": "rebuilding",
    "generation": 41,
    "target-generation": 42
  }
}
```

and:

```json
{
  "link-cache": {
    "state": "stale",
    "generation": 41,
    "database-generation": 42
  }
}
```

Status is descriptive.

The authoritative cache-generation record remains:

```text
link-cache/generation.json
```

---

# Example Cache After One Link

Given the authoritative link entity:

```json
{
  "entity": "33333333-3333-4333-8333-333333333333",
  "revision": 1,
  "aspects": {
    "tag:m1lattice.net,2026/aspect/link": {
      "from": "11111111-1111-4111-8111-111111111111",
      "to": "22222222-2222-4222-8222-222222222222",
      "relationship": "participates-in"
    }
  }
}
```

the cache at generation `42` contains:

```text
link-cache/
  generation.json

  outgoing/
    11111111-1111-4111-8111-111111111111.json

  incoming/
    22222222-2222-4222-8222-222222222222.json
```

## `generation.json`

```json
{
  "link-cache-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 42,
  "updated": "2026-07-23T23:40:01Z",
  "state": "current"
}
```

## Outgoing Entry

```json
{
  "link-cache-entry-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 42,
  "entity": "11111111-1111-4111-8111-111111111111",
  "direction": "outgoing",
  "links": [
    "33333333-3333-4333-8333-333333333333"
  ]
}
```

## Incoming Entry

```json
{
  "link-cache-entry-format-version": 1,
  "database-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "generation": 42,
  "entity": "22222222-2222-4222-8222-222222222222",
  "direction": "incoming",
  "links": [
    "33333333-3333-4333-8333-333333333333"
  ]
}
```

---

# Non-Negotiable Rules

* Link entities in authoritative storage are the sole authority for relationships.
* An entity is indexed as a link only when it contains a valid link aspect.
* Every link is indexed by both its `from` and `to` endpoints.
* Cache lookups return link entity IDs, not authoritative relationship contents.
* The cache is derived and completely rebuildable.
* Cache files must not be edited directly by callers.
* A cache is current only when its database identity and generation match the committed database.
* A stale, absent, rebuilding, or malformed cache must not be presented as complete current link information.
* Transaction application and recovery keep the cache synchronized with committed link changes.
* Recovery may repeat cache mutations idempotently.
* Rebuilding scans authoritative link entities and constructs a complete replacement cache.
* Cache failure must never cause Subete to rewrite authoritative link entities to match the cache.
