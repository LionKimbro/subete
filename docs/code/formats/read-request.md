# Subete — Read Request Files

Read request files ask Subete to retrieve committed entity and aspect state.

Their semantic structure and behavior are defined by:

* [`protocol-crud.md`](../protocol-crud.md);
* [`filetalk-protocol.md`](../filetalk-protocol.md).

This document defines only the on-disk file conventions.

## Location

Read request files are submitted to:

```text
subete-data/
  inbox/
```

After Subete claims them, they move through the request-processing locations defined by the filesystem layout.

## Filename

The inbox filename has no semantic meaning.

Examples:

```text
read.json
request-002
de780bc3-479b-4389-bf59-d92e5edcd4d3.json
```

The `request-id` inside the JSON object is the authoritative identity of the request.

## Content

Each file contains one complete JSON read request object.

```json
{
  "request-id": "de780bc3-479b-4389-bf59-d92e5edcd4d3",
  "request-type": "read",
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/de780bc3-479b-4389-bf59-d92e5edcd4d3.json"
  },
  "request": {
    "reads": [
      {
        "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
        "aspects": [
          "tag:m1lattice.net,2026:aspect/basic"
        ]
      },
      {
        "entity": "69091b6c-f087-45b4-9560-cbe90c127b8e",
        "aspects": "*"
      }
    ]
  }
}
```

The complete definitions of selected-aspect reads, all-aspect reads, batching, revisions, not-found results, replies, validation, and errors belong to `protocol-crud.md`.

## File Rules

* The file contains one JSON object.
* The file is encoded as UTF-8.
* The file may be written directly into `inbox/`.
* Subete must tolerate seeing the file before writing is complete.
* A complete JSON object that violates the read protocol is invalid input, not an incomplete write.
* The filename does not need to match the `request-id`.
* Retried delivery of the same logical request preserves the same `request-id` and request content.
* One file contains one read request.
* Read request files do not modify authoritative state.
