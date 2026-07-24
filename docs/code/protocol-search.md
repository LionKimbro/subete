# Subete — Search Protocol

This document defines the request and reply semantics for searching the committed Subete world.

Search requests discover entities matching one or more predicates. They do not modify authoritative state.

The initial search protocol supports predicates based on:

* `typehint` in the M1 basic aspect;
* presence of specified aspects;
* tags in the M1 basic aspect;
* substrings within `name` in the M1 basic aspect;
* substrings within `title` in the M1 basic aspect;
* link entities whose `from` endpoint is a specified entity;
* link entities whose `to` endpoint is a specified entity;
* link entities attached in either direction to a specified entity;
* combinations of these predicates.

A single request may contain multiple independent searches.

The structures in this document are written as Markdown SoftSpec. Examples illustrate intended meaning and may omit fields that are not relevant to the example.

---

## Search Request Envelope and Shared Delivery

The shared message-file envelope, inbox delivery, incomplete-file handling, claiming, and SASE reply delivery rules are defined in [filetalk-protocol.md](filetalk-protocol.md).

Search messages are request/reply communications.

A search request contains:

* a required UUID `request-id`;
* a required `request-type` of `"search"`;
* a required `reply` destination using a form supported by the shared FileTalk protocol;
* a required `request` object containing the search request body.

```json
{
  "request-id": "d4552606-b3b0-4417-818c-a89fc612b83a",
  "request-type": "search",
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/d4552606-b3b0-4417-818c-a89fc612b83a.json"
  },
  "request": {
    "searches": [
      {
        "typehint": "person",
        "tags": [
          "friend",
          "seattle"
        ]
      }
    ]
  }
}
```

---

# Search Request Body

```json
{
  "searches": [
    {
      "...": "search specification"
    }
  ]
}
```

## `searches`

```json
{
  "type": "array",
  "required": true,
  "minimum-items": 1
}
```

A serialized collection of independent searches.

Each search is evaluated against the same committed database generation.

Array position is preserved in the reply. The result at index `0` corresponds to the search at index `0`, and so on.

A malformed search specification causes the complete request to fail. Subete does not return partial results for the remaining searches in the same request.

---

# Search Specification

A search specification is an object containing one or more predicates.

```json
{
  "typehint": "person",
  "has-aspects": [
    "tag:example.net,2026/aspect/contact"
  ],
  "tags": [
    "friend",
    "seattle"
  ],
  "name-contains": "ali",
  "title-contains": "engineer"
}
```

Every predicate present in the object must match.

A search specification must contain at least one recognized predicate. An empty search object is invalid and does not mean “return every entity.”

The recognized predicates are:

```text
typehint
has-aspects
tags
name-contains
title-contains
link-from
link-to
link-attached-to
```

Additional predicates may be defined in later protocol versions.

---

# Predicate Combination

All predicates within one search specification are combined using logical **AND**.

For example:

```json
{
  "typehint": "person",
  "tags": [
    "friend",
    "seattle"
  ],
  "has-aspects": [
    "tag:example.net,2026/aspect/contact"
  ]
}
```

matches only an entity that:

1. has a basic aspect whose `typehint` matches `"person"`;
2. has every required tag, `"friend"` and `"seattle"`;
3. has the specified contact aspect.

There is no implicit OR behavior.

A caller that wants alternative searches submits multiple search specifications.

```json
{
  "searches": [
    {
      "typehint": "person",
      "tags": [
        "seattle"
      ]
    },
    {
      "typehint": "organization",
      "tags": [
        "seattle"
      ]
    }
  ]
}
```

These are two independent searches, not one combined search.

---

# Basic Aspect

The predicates `typehint`, `tags`, `name-contains`, and `title-contains` inspect the conventional M1 basic aspect:

```text
tag:m1lattice.net,2026/aspect/basic
```

An entity lacking the basic aspect does not match a predicate that requires a field from that aspect.

An entity may still match an aspect-presence search without having a basic aspect.

If the basic aspect exists but the requested field is absent or has an incompatible value type, that predicate does not match.

A malformed basic aspect does not cause the complete search request to fail merely because the malformed entity is encountered. The entity simply does not match the affected predicate, and Subete may record or report the malformed authoritative data through separate diagnostics.

---

# `typehint`

Matches entities whose basic aspect contains a matching `typehint`.

```json
{
  "typehint": "person"
}
```

## Field

```json
{
  "type": "string",
  "required": false
}
```

## Matching Rules

* The entity must have the conventional basic aspect.
* The basic aspect must contain a string-valued `typehint`.
* Matching is by complete value, not substring.
* Matching is case-insensitive using Unicode case folding.
* Leading and trailing whitespace is significant and is not automatically removed.

Examples:

```text
"person" matches "person"
"person" matches "Person"
"person" does not match "business-person"
"person" does not match " person "
```

---

# `has-aspects`

Matches entities containing all specified aspects.

```json
{
  "has-aspects": [
    "tag:example.net,2026/aspect/contact",
    "tag:example.net,2026/aspect/person"
  ]
}
```

## Field

```json
{
  "type": "array",
  "required": false,
  "minimum-items": 1,
  "items": {
    "type": "entity-id"
  }
}
```

## Matching Rules

* Every listed aspect must be present on the entity.
* Aspect identifiers are compared exactly.
* Aspect-ID comparison is case-sensitive.
* The aspect value may be any valid authoritative value.
* Duplicate aspect IDs in the request are invalid.
* An entity with only some of the required aspects does not match.

Aspect presence is intended to support discovery by specialized or authoritative entity type, independent of the informal `basic.typehint` field.

---

# `tags`

Matches entities whose basic aspect contains all specified tags.

```json
{
  "tags": [
    "friend",
    "seattle"
  ]
}
```

## Field

```json
{
  "type": "array",
  "required": false,
  "minimum-items": 1,
  "items": {
    "type": "string"
  }
}
```

## Matching Rules

* The entity must have the conventional basic aspect.
* The basic aspect must contain a `tags` array.
* Every requested tag must be present in that array.
* An entity may contain additional tags.
* Tag matching is by complete tag value, not substring.
* Tag matching is case-insensitive using Unicode case folding.
* Leading and trailing whitespace is significant and is not automatically removed.
* Duplicate requested tags under case-insensitive comparison are invalid.
* Non-string values inside an entity’s `tags` array do not match any requested tag.

Example:

```json
{
  "entity-tags": [
    "friend",
    "Seattle",
    "programmer"
  ],
  "requested-tags": [
    "FRIEND",
    "seattle"
  ],
  "matches": true
}
```

The `tags` predicate means **contains all required tags**.

It does not mean:

* contains any requested tag;
* contains exactly these tags;
* contains a tag substring.

Alternative tag operators may be defined later.

---

# `name-contains`

Matches entities whose basic `name` contains a specified substring.

```json
{
  "name-contains": "lion"
}
```

## Field

```json
{
  "type": "string",
  "required": false,
  "minimum-length": 1
}
```

## Matching Rules

* The entity must have the conventional basic aspect.
* The basic aspect must contain a string-valued `name`.
* Matching is literal substring matching.
* Matching is case-insensitive using Unicode case folding.
* The value is not interpreted as a regular expression.
* Leading and trailing whitespace in the requested substring is significant.
* An empty substring is invalid.

Examples:

```text
"lion" matches "lion"
"lion" matches "LionKimbro"
"lion" matches "mountain-lion"
"lion" does not match "feline"
```

---

# `title-contains`

Matches entities whose basic `title` contains a specified substring.

```json
{
  "title-contains": "database"
}
```

## Field

```json
{
  "type": "string",
  "required": false,
  "minimum-length": 1
}
```

## Matching Rules

* The entity must have the conventional basic aspect.
* The basic aspect must contain a string-valued `title`.
* Matching is literal substring matching.
* Matching is case-insensitive using Unicode case folding.
* The value is not interpreted as a regular expression.
* Leading and trailing whitespace in the requested substring is significant.
* An empty substring is invalid.

Examples:

```text
"database" matches "M1 Database"
"data" matches "Database Architecture"
"base data" does not match "Database"
```

---

# Link Endpoint Predicates

The predicates `link-from`, `link-to`, and `link-attached-to` match link
entities.

A candidate entity matches a link endpoint predicate only when it contains a
valid conventional M1 link aspect:

```text
tag:m1lattice.net,2026/aspect/link
```

with valid `from` and `to` entity IDs.

An entity lacking the link aspect does not match. An entity whose link aspect
is malformed does not match; encountering it does not fail the complete search
request.

Each endpoint predicate value is an `entity-id`. Accepted UUID input is
canonicalized under the M1/Subete identifier rules before comparison. Tag URI
values are preserved and compared exactly.

## `link-from`

Matches link entities whose `from` endpoint is the specified entity.

```json
{
  "link-from": "11111111-1111-4111-8111-111111111111"
}
```

Matching is:

```text
link aspect from = requested entity ID
```

## `link-to`

Matches link entities whose `to` endpoint is the specified entity.

```json
{
  "link-to": "22222222-2222-4222-8222-222222222222"
}
```

Matching is:

```text
link aspect to = requested entity ID
```

## `link-attached-to`

Matches link entities whose `from` or `to` endpoint is the specified entity.

```json
{
  "link-attached-to": "11111111-1111-4111-8111-111111111111"
}
```

Matching is:

```text
link aspect from = requested entity ID
OR
link aspect to = requested entity ID
```

The OR belongs inside this one predicate. The predicate as a whole is combined
with every other supplied predicate using the normal search-level AND rule.

A self-link whose `from` and `to` both equal the requested entity matches once.
Its link entity ID appears at most once in the result.

## Returned Identities

These predicates return the IDs of matching link entities.

They do not return:

* the opposite endpoint entity;
* endpoint pairs;
* link aspect contents;
* link-cache records.

The caller may read returned link entities through the ordinary read protocol.

---

# Complete Combined Search Example

```json
{
  "request-id": "66be4ce8-1940-4e6c-b057-0ce803842736",
  "request-type": "search",
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/66be4ce8-1940-4e6c-b057-0ce803842736.json"
  },
  "request": {
    "searches": [
      {
        "typehint": "person",
        "has-aspects": [
          "tag:example.net,2026/aspect/contact"
        ],
        "tags": [
          "friend",
          "seattle"
        ],
        "name-contains": "ali",
        "title-contains": "engineer"
      }
    ]
  }
}
```

An entity matches only if every supplied predicate matches.

---

# Multiple Searches in One Request

```json
{
  "request-id": "d0cbca52-87e3-4431-884f-0c3981493dae",
  "request-type": "search",
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/d0cbca52-87e3-4431-884f-0c3981493dae.json"
  },
  "request": {
    "searches": [
      {
        "typehint": "person",
        "tags": [
          "programmer"
        ]
      },
      {
        "has-aspects": [
          "tag:example.net,2026/aspect/project"
        ],
        "title-contains": "subete"
      },
      {
        "name-contains": "wing"
      }
    ]
  }
}
```

All searches observe the same committed database generation.

The searches are independent. An entity may appear in more than one result.

---

# Search Execution

Searches observe committed authoritative state only.

They must not expose:

* transaction planning state;
* partially applied transactions;
* incomplete recovery work;
* speculative memory;
* stale authoritative-store views.

The implementation may satisfy a search by:

* scanning authoritative entity storage;
* consulting an authoritative store’s native query capabilities;
* consulting a derived index known to reflect the required generation;
* combining results from multiple authoritative and derived stores.

The Version 1 link cache may satisfy the link endpoint predicates only when it
is current for the searched committed generation. It is an internal
optimization. Requests and responses never name the cache or reveal whether it
was used. If the cache cannot supply a complete current answer, Subete must use
a coherent authoritative scan or fail the search; it must not return stale or
partial link results.

The physical search method does not change the protocol’s matching semantics.

If Subete cannot provide results consistent with one committed generation, it must not return the search as successful.

---

# Search Results

Search results contain entity IDs only.

They do not include:

* entity revisions;
* basic-aspect values;
* matched excerpts;
* complete aspects;
* match scores;
* explanatory metadata.

A caller may issue a read request afterward to retrieve current aspects and revisions for selected entities.

This separation keeps search focused on discovery and read focused on retrieval.

---

# Search Result Ordering

Entity IDs within each search result are ordered by ascending Unicode code-point order of the complete entity-ID string.

For ordinary lowercase UUIDs, this is equivalent to ascending lexicographic UUID order.

Result order does not indicate:

* relevance;
* creation time;
* modification time;
* title order;
* type order;
* storage order.

The deterministic entity-ID ordering exists so that repeated execution against the same committed generation produces stable serialized results.

Each independent search has its own ordered result array.

No ordering relationship is implied between separate searches in the same request beyond their retained request-array positions.

---

# Search Success Reply

```json
{
  "request-id": "d0cbca52-87e3-4431-884f-0c3981493dae",
  "request-type": "search",
  "status": "success",
  "generation": 143,
  "response": {
    "searches": [
      {
        "index": 0,
        "entities": [
          "0cb710b2-1686-4e02-904b-510a01ce245f",
          "209ee0b8-36d5-4a47-81ca-c59f0eaac29d"
        ]
      },
      {
        "index": 1,
        "entities": [
          "69091b6c-f087-45b4-9560-cbe90c127b8e"
        ]
      },
      {
        "index": 2,
        "entities": []
      }
    ]
  }
}
```

## Rules

* `request-id` is copied from the request.
* `request-type` is `"search"`.
* `status` is `"success"`.
* `generation` identifies the committed world observed by every search in the request.
* `response.searches` contains one result for each submitted search.
* `index` identifies the zero-based position of the corresponding search.
* `entities` contains the matching entity IDs in deterministic order.
* No matches is represented by an empty `entities` array.
* No matches is a successful search result, not a request failure.

---

# Search Failure Reply

```json
{
  "request-id": "d0cbca52-87e3-4431-884f-0c3981493dae",
  "request-type": "search",
  "status": "failure",
  "generation": 143,
  "response": {
    "error": {
      "code": "empty-search",
      "message": "Each search specification must contain at least one recognized predicate.",
      "search-index": 1
    }
  }
}
```

## Rules

* A structurally or semantically invalid search causes the complete request to fail.
* No partial successful search results are returned.
* `generation` is the committed database generation when the failure reply is produced.
* The error should identify the failing search index when applicable.
* One primary error is sufficient.
* Subete may later report multiple validation errors.

---

# Duplicate Request Behavior

Search requests use `request-id` to make repeated FileTalk delivery safe.

Version 1 does not require a completed search request record to retain a replayable result. A later identical search delivery may execute again against the generation current when it is processed and returns that generation in its reply.

If the original search remains claimed because the process stopped before completion, startup recovery reruns it from the retained request. Subete's single-request execution model guarantees that no later request mutated the database between the interrupted search and that recovery, so the rerun observes the same generation. The response is then delivered under `filetalk-protocol.md`.

If the same `request-id` is reused for materially different request content, Subete rejects it with `request-id-conflict`. The reply destination is part of the request content.

If a duplicate arrives while the original search is still being processed, Subete must not independently execute both. Once the original search reaches a terminal record, a later identical delivery may execute as a new search.

Shared delivery and reply-redelivery behavior is governed by [filetalk-protocol.md](filetalk-protocol.md).

---

# Validation Rules

Before executing any search in the request, Subete validates:

* the request identity;
* that `request-type` is `"search"`;
* the required reply destination;
* that `request.searches` is a nonempty array;
* that each search is an object;
* that each search contains at least one recognized predicate;
* that no unrecognized predicate is present;
* the value type of every predicate;
* that `has-aspects` contains valid, nonduplicate aspect IDs;
* that `tags` contains nonempty, nonduplicate strings;
* that substring predicates are nonempty strings.
* that each supplied link endpoint predicate contains one valid entity ID.

Validation does not modify authoritative state.

---

# Initial Error Codes

The search protocol may use error codes including:

```text
invalid-search-request
empty-search-request
invalid-search
empty-search
unsupported-search-predicate

invalid-typehint-predicate
invalid-has-aspects-predicate
invalid-tags-predicate
invalid-name-contains-predicate
invalid-title-contains-predicate
invalid-link-from-predicate
invalid-link-to-predicate
invalid-link-attached-to-predicate

duplicate-required-aspect
duplicate-required-tag
invalid-aspect-id

internal-error
recovery-required
service-not-ready
```

Shared FileTalk delivery errors and request-identity conflicts are defined by the applicable shared and request-family conventions.

The error code is intended for programmatic handling.

The message is intended for human understanding.

Additional structured fields may identify the search index, predicate, aspect ID, tag, or other relevant location.

---

# Protocol Boundaries

This protocol deliberately does not define:

* arbitrary querying inside specialized aspects;
* full-text relevance scoring;
* ranked search results;
* regular-expression search;
* fuzzy matching;
* stemming;
* language-specific tokenization;
* OR or NOT expressions;
* numeric comparison;
* date-range comparison;
* pagination;
* result limits;
* sorting by arbitrary fields;
* returning aspects alongside search results;
* returning opposite endpoints or performing multi-hop link traversal;
* historical-generation search.

These capabilities may be defined separately if needed.

The central model remains:

* one request may contain multiple searches;
* each search contains one or more predicates;
* all predicates within one search are combined using AND;
* all searches observe one committed generation;
* successful results contain deterministically ordered entity IDs only;
* link endpoint predicates return matching link entity IDs.
