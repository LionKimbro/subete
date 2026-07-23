# ADR 001 — Permit Links to Absent Endpoint Entities

## Status

Accepted.

## Context

Subete represents relationships as ordinary M1 link entities. A link aspect identifies its `from` and `to` endpoint entity IDs.

An endpoint entity may later be deleted while a link that refers to its stable ID remains meaningful: the link may preserve historical information, record an unresolved relationship, or await later recreation or reconciliation of the endpoint entity.

Requiring entity deletion to find and change every attached link would make deletion non-local, potentially expensive, and dependent on coordinated multi-entity mutation. Implicit cascading deletion would also destroy relationship records without an explicit caller decision.

## Decision

Subete permits dangling links.

* When a link entity is created, each endpoint must identify an entity that will exist after that transaction commits.
* When an existing link aspect changes either endpoint, each resulting endpoint must identify an entity that will exist after that transaction commits.
* A later transaction may delete an endpoint entity without deleting or changing link entities that refer to its ID.
* Subete never implicitly cascades link deletion or link rewriting from `delete-entity`.
* Link-cache entries may exist for entity IDs that have no current entity record.
* Attached-link lookup by an absent entity ID remains valid and returns the authoritative link IDs indexed for that ID.

## Consequences

Entity existence is checked at link creation and endpoint-redirection time, not as a permanent referential-integrity constraint.

Deleting an entity remains local and predictable. Links retain their own stable identities and can preserve historical or unresolved relationships.

Consumers must distinguish an absent endpoint entity from an absent relationship. A link's `from` or `to` field remains a valid reference to the stable entity ID even when a read of that entity currently returns not found.

The link cache remains derived: it indexes link membership by endpoint ID regardless of whether an entity record currently exists for that ID.

## Alternatives Rejected

**Forbid dangling links.** Rejected because it makes ordinary entity deletion require attached-link discovery and coordinated mutation, and prevents historical or unresolved relationships from remaining represented.

**Implicitly cascade link deletion.** Rejected because it silently removes relationship entities and violates the principle that callers explicitly describe intended entity mutations.

**Require callers always to delete or redirect attached links.** Rejected because it adds mandatory, potentially unbounded work to a local entity deletion and is unnecessary for preserving a coherent M1 world.
