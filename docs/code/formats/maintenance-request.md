# Subete — Maintenance Request Files

Maintenance request files ask the running Subete service to perform one
service-owned checkpoint, retention, or stop operation.

Their semantic structure and behavior are defined by:

* [`protocol-maintenance.md`](../protocol-maintenance.md);
* [`filetalk-protocol.md`](../filetalk-protocol.md).

This document defines only the on-disk file conventions.

## Location

Maintenance request files are submitted to:

```text
subete-data/
  inbox/
```

After Subete claims them, they move through the request-processing locations
defined by the filesystem layout.

## Filename

The inbox filename has no semantic meaning.

Examples:

```text
checkpoint.json
remove-old.json
stop.json
8ae7f0c8-8727-4d51-89ad-7b6d92d8e750.json
```

The `request-id` inside the JSON object is the authoritative identity of the
request.

## Checkpoint Request

```json
{
  "request-id": "8ae7f0c8-8727-4d51-89ad-7b6d92d8e750",
  "request-type": "maintenance",
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/8ae7f0c8-8727-4d51-89ad-7b6d92d8e750.json"
  },
  "request": {
    "operation": "checkpoint"
  }
}
```

## Remove-Old Request

```json
{
  "request-id": "36e96bf8-64b3-41a5-b824-29cce752fef0",
  "request-type": "maintenance",
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/36e96bf8-64b3-41a5-b824-29cce752fef0.json"
  },
  "request": {
    "operation": "remove-old",
    "mode": "dry-run"
  }
}
```

The required `mode` is exactly `"dry-run"` or `"execute"`.

## Stop Request

```json
{
  "request-id": "0424ab37-d003-4507-b9c6-efca41b57940",
  "request-type": "maintenance",
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/0424ab37-d003-4507-b9c6-efca41b57940.json"
  },
  "request": {
    "operation": "stop"
  }
}
```

## File Rules

* The file contains one JSON object.
* The file is encoded as UTF-8.
* The file may be written directly into `inbox/`.
* Subete must tolerate seeing the file before writing is complete.
* A complete JSON object that violates the maintenance protocol is invalid
  input, not an incomplete write.
* The filename does not need to match the `request-id`.
* Retried delivery of the same logical request preserves the same
  `request-id` and complete request content.
* One file contains one maintenance request.
* A maintenance request contains exactly one operation.
* A maintenance request does not contain caller-selected deletion paths.
* Maintenance request files are not authoritative entity state.
* Only the running service performs the requested operation.

