# Subete — Search Request Files

Search request files ask Subete to discover entities matching one or more search specifications.

Their semantic structure and behavior are defined by:

* [`protocol-search.md`](../protocol-search.md);
* [`filetalk-protocol.md`](../filetalk-protocol.md).

This document defines only the on-disk file conventions.

## Location

Search request files are submitted to:

```text
subete-data/
  inbox/
```

After Subete claims them, they move through the request-processing locations defined by the filesystem layout.

## Filename

The inbox filename has no semantic meaning.

Examples:

```text
search.json
request-003
d4552606-b3b0-4417-818c-a89fc612b83a.json
```

The `request-id` inside the JSON object is the authoritative identity of the request.

## Content

Each file contains one complete JSON search request object.

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
        "has-aspects": [
          "tag:example.net,2026/aspect/contact"
        ],
        "tags": [
          "friend",
          "seattle"
        ],
        "name-contains": "ali"
      },
      {
        "title-contains": "subete"
      }
    ]
  }
}
```

The complete definitions of search predicates, predicate combination, case sensitivity, tag matching, batching, result ordering, replies, validation, and errors belong to `protocol-search.md`.

## File Rules

* The file contains one JSON object.
* The file is encoded as UTF-8.
* The file may be written directly into `inbox/`.
* Subete must tolerate seeing the file before writing is complete.
* A complete JSON object that violates the search protocol is invalid input, not an incomplete write.
* The filename does not need to match the `request-id`.
* Retried delivery of the same logical request preserves the same `request-id` and request content.
* One file contains one search request.
* Search request files do not modify authoritative state.
