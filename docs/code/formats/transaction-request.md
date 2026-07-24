# Subete — Transaction Request Files

Transaction request files submit one atomic set of entity and aspect mutations to Subete.

Their semantic structure and behavior are defined by:

* [`protocol-crud.md`](../protocol-crud.md);
* [`filetalk-protocol.md`](../filetalk-protocol.md).

This document defines only the on-disk file conventions.

## Location

Transaction request files are submitted to:

```text
subete-data/
  inbox/
```

After Subete claims them, they move through the request-processing locations defined by the filesystem layout.

## Filename

The inbox filename has no semantic meaning.

Examples:

```text
transaction.json
request-001
7be711d6-5801-4e28-a300-81772985bcbb.json
```

The `request-id` inside the JSON object is the authoritative identity of the request.

## Content

Each file contains one complete JSON transaction request object.

```json
{
  "request-id": "7be711d6-5801-4e28-a300-81772985bcbb",
  "request-type": "transaction",
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/7be711d6-5801-4e28-a300-81772985bcbb.json"
  },
  "request": {
    "operations": [
      {
        "operation": "set-aspect",
        "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
        "expected-revision": 12,
        "aspect": "tag:m1lattice.net,2026:aspect/basic",
        "value": {
          "title": "Updated Title"
        }
      }
    ]
  }
}
```

The complete definitions of the envelope, operations, revision preconditions, validation, transaction semantics, replies, and errors belong to `protocol-crud.md`.

## File Rules

* The file contains one JSON object.
* The file is encoded as UTF-8.
* The file may be written directly into `inbox/`.
* Subete must tolerate seeing the file before writing is complete.
* A complete JSON object that violates the transaction protocol is invalid input, not an incomplete write.
* The filename does not need to match the `request-id`.
* Retried delivery of the same logical request preserves the same `request-id` and request content.
* One file contains one transaction request.
* Transaction request files are not authoritative entity state.
