# Subete — Response Files

Response files contain Subete replies to transaction, read, and search requests.

Their semantic structure and behavior are defined by:

* [`protocol-crud.md`](../protocol-crud.md);
* [`protocol-search.md`](../protocol-search.md);
* [`filetalk-protocol.md`](../filetalk-protocol.md).

This document defines only the on-disk file conventions.

## Location

A response is written to the file destination supplied by the originating request:

```json
{
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/result.json"
  }
}
```

Response files are not required to be stored inside the Subete data directory.

## Filename

The response filename is chosen by the request sender through the reply destination.

It has no independent semantic meaning.

Examples:

```text
result.json
transaction-reply.json
d4552606-b3b0-4417-818c-a89fc612b83a.json
```

The `request-id` inside the response identifies the request to which the response belongs.

## Content

Each file contains one complete JSON response object.

### Transaction Response

```json
{
  "request-id": "7be711d6-5801-4e28-a300-81772985bcbb",
  "request-type": "transaction",
  "status": "success",
  "generation": 143,
  "response": {
    "journal-sequence": 143,
    "entities": [
      {
        "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
        "revision": 13
      }
    ]
  }
}
```

### Read Response

```json
{
  "request-id": "de780bc3-479b-4389-bf59-d92e5edcd4d3",
  "request-type": "read",
  "status": "success",
  "generation": 143,
  "response": {
    "reads": [
      {
        "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
        "status": "found",
        "revision": 13,
        "aspects": {
          "tag:m1lattice.net,2026/aspect/basic": {
            "title": "Lion Kimbro"
          }
        }
      }
    ]
  }
}
```

### Search Response

```json
{
  "request-id": "d4552606-b3b0-4417-818c-a89fc612b83a",
  "request-type": "search",
  "status": "success",
  "generation": 143,
  "response": {
    "searches": [
      {
        "index": 0,
        "entities": [
          "209ee0b8-36d5-4a47-81ca-c59f0eaac29d"
        ]
      }
    ]
  }
}
```

The complete definitions of success, failure, not-found results, generations, revisions, errors, duplicate delivery, and reply-delivery behavior belong to the governing protocol documents.

## File Rules

* The file contains one JSON object.
* The file is encoded as UTF-8.
* Subete may write directly to the final response path.
* A response recipient must tolerate seeing the file before writing is complete.
* A complete JSON object that violates the applicable response protocol is malformed output.
* The filename does not need to match the `request-id`.
* One file contains one response.
* A response file is not authoritative entity state.
* Failure to write a response does not reverse a completed request or committed transaction.
* A retried transaction request should receive the previously recorded logical response rather than cause the transaction to execute again. Read and search requests may be executed again because they do not mutate authoritative state.
