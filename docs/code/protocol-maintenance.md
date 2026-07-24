# Subete — Maintenance Protocol

This document defines the Version 1 FileTalk request and reply semantics for
service-owned maintenance operations.

The maintenance request family has three operations:

```text
checkpoint
remove-old
stop
```

Maintenance requests do not mutate the M1 entity world and do not advance the
database generation. They may create or remove operational and recovery
artifacts, or end the current service process.

All maintenance work executes inside the authoritative Subete service's
strictly sequential request loop. External commands are FileTalk clients.
They do not copy, delete, or directly mutate the live database.

The structures in this document are written as Markdown SoftSpec.

---

# Request Envelope

The shared message-file envelope, inbox delivery, incomplete-file handling,
claiming, and SASE file reply delivery rules are defined in
[filetalk-protocol.md](filetalk-protocol.md).

A maintenance request contains:

* a required UUID `request-id`;
* a required `request-type` of `"maintenance"`;
* a required `reply` destination;
* a required `request` object containing exactly one maintenance operation.

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

The `reply` field is required for every Version 1 maintenance request.

---

# Common Semantics

## Sequential Ownership

The service claims and processes one maintenance request in the same
sequential lifecycle used for transaction, read, and search requests.

No transaction, read, search, or other maintenance request begins while a
maintenance request is active.

## Generation

Every maintenance response contains the database generation observed by the
operation.

Maintenance work does not:

* allocate a journal sequence;
* create a transaction journal entry;
* change entity revisions;
* advance root `generation.json`.

## Request Shape

The request body is a closed object. Unknown fields are invalid.

The `checkpoint` and `stop` operations accept only:

```json
{
  "operation": "checkpoint"
}
```

or:

```json
{
  "operation": "stop"
}
```

The `remove-old` operation additionally requires `mode`.

## Authorization

Version 1 has no separate authentication token, user identity, or role model
inside the maintenance protocol.

Authorization relies on filesystem access:

* the operating-system permissions protecting the Subete inbox;
* the permissions protecting the selected database root;
* the configured FileTalk reply-path policy.

Any process that can place a valid request into the inbox can request
checkpoint creation, retention work, or service stop. Deployments must protect
the FileTalk surfaces accordingly.

---

# `checkpoint`

The `checkpoint` operation asks the running service to:

1. select its current committed generation;
2. hold the sequential execution boundary so that generation cannot change;
3. reuse a valid checkpoint already published for that generation, if one
   exists;
4. otherwise reuse a valid uncheckpointed snapshot for that database and
   generation, or create a complete new snapshot;
5. validate the selected snapshot;
6. publish a checkpoint referring to that snapshot when one does not already
   exist;
7. return the resulting artifact identities.

The snapshot created or reused here is the Version 1 entity-store snapshot:
its archive contains only `entities/` and `snapshot-manifest.json`.
Checkpoint maintenance does not copy `configuration.json`, framework
`config.json`, identity or generation files, locks, journals, checkpoints,
FileTalk state, status data, temporary files, or link-cache data into the
snapshot.

## Request

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

## Success Response

```json
{
  "request-id": "8ae7f0c8-8727-4d51-89ad-7b6d92d8e750",
  "request-type": "maintenance",
  "status": "success",
  "generation": 143,
  "response": {
    "operation": "checkpoint",
    "snapshot": {
      "file": "00000000000000000143__2026-07-23T23-09-42Z.zip",
      "generation": 143
    },
    "checkpoint": {
      "file": "00000000000000000143.json",
      "generation": 143,
      "replay-after": 143
    }
  }
}
```

### Rules

* The outer `generation`, snapshot generation, checkpoint generation, and
  `replay-after` are equal in Version 1.
* `snapshot.file` is a filename directly beneath `snapshots/`.
* `checkpoint.file` is a filename directly beneath
  `journal/checkpoints/`.
* The response is successful only after the snapshot is complete and
  validated and the checkpoint is durably published.
* Because the checkpoint filename is generation-based, a valid checkpoint
  already published for the current generation is returned as success rather
  than replaced.
* When no checkpoint exists, Subete may reuse the newest valid completed
  snapshot for the same database identity and generation. It does not create
  duplicate recovery artifacts merely because an earlier request was
  interrupted after snapshot publication.
* Snapshot or checkpoint creation does not advance the generation.
* Checkpoint creation does not read or copy `configuration.json` as snapshot
  content.
* A completed snapshot may remain available if later checkpoint publication
  fails. Such a partial maintenance outcome is reported as failure and must
  not be represented as a completed checkpoint operation.

---

# `remove-old`

The `remove-old` operation asks the running service to identify operational
and recovery artifacts that its retention policy considers old and that can
be removed without destroying a required recovery path.

The caller chooses only whether to preview or execute the service's plan. The
caller cannot name paths, files, generations, or artifact IDs to delete.

## Request

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

## `mode`

```json
{
  "type": "string",
  "required": true,
  "allowed-values": [
    "dry-run",
    "execute"
  ]
}
```

`"dry-run"` computes and reports the removal plan without removing any
artifact.

`"execute"` computes the plan, revalidates its safety inside the same
sequential request, and removes the planned artifacts.

There is no implicit default. The caller must explicitly select one mode.

## Artifact Record

Every reported artifact has this shape:

```json
{
  "kind": "committed-journal",
  "path": "journal/committed/00000000000000000042__44444444-4444-4444-8444-444444444444.json"
}
```

### `kind`

Version 1 values are:

```text
completed-request
failed-request
committed-journal
snapshot
checkpoint
abandoned-temporary
```

### `path`

`path` is a normalized forward-slash path relative to the database root.

It is descriptive output selected by the service. It is never accepted as
request input.

## Dry-Run Success Response

```json
{
  "request-id": "36e96bf8-64b3-41a5-b824-29cce752fef0",
  "request-type": "maintenance",
  "status": "success",
  "generation": 143,
  "response": {
    "operation": "remove-old",
    "mode": "dry-run",
    "candidates": [
      {
        "kind": "committed-journal",
        "path": "journal/committed/00000000000000000042__44444444-4444-4444-8444-444444444444.json"
      }
    ],
    "removed": []
  }
}
```

## Execute Success Response

```json
{
  "request-id": "56e9ade8-5bf5-427f-845f-0dc74d0375dd",
  "request-type": "maintenance",
  "status": "success",
  "generation": 143,
  "response": {
    "operation": "remove-old",
    "mode": "execute",
    "candidates": [
      {
        "kind": "committed-journal",
        "path": "journal/committed/00000000000000000042__44444444-4444-4444-8444-444444444444.json"
      }
    ],
    "removed": [
      {
        "kind": "committed-journal",
        "path": "journal/committed/00000000000000000042__44444444-4444-4444-8444-444444444444.json"
      }
    ]
  }
}
```

### Safety Rules

* The service, not the caller, selects every candidate.
* Selection follows the configured/local retention policy and the recovery
  rules in `snapshot-checkpoint-lifecycle.md`.
* The operation may conservatively return no candidates.
* A pending journal is never a candidate.
* A claimed request is never a candidate.
* Current entity state, identity, configuration, root generation, link-cache
  state, inbox contents, and status files are never candidates.
* A committed journal is removable only when a retained validated
  snapshot/checkpoint chain makes it unnecessary for every retained recovery
  path that policy requires.
* A snapshot referenced by a retained checkpoint is not removable.
* A checkpoint is not removable if policy retains it as part of a required
  recovery path.
* The active `remove-old` request is not a candidate.
* A completed or failed maintenance request record is not a Version 1
  candidate, because its retained request and response are the durable basis
  for preventing repeated maintenance effects.
* In `"execute"` mode, success means every reported candidate was removed;
  therefore `removed` equals `candidates`.
* In `"dry-run"` mode, `removed` is empty.
* Removing operational or recovery artifacts does not advance the database
  generation.

If execution fails after removing only part of the plan, the response is a
failure and reports both the complete `candidates` list and the successfully
`removed` prefix. Already removed redundant artifacts are not recreated.

---

# `stop`

The `stop` operation asks the current authoritative service process to end
through its normal shutdown path.

## Request

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

## Success Response

```json
{
  "request-id": "0424ab37-d003-4507-b9c6-efca41b57940",
  "request-type": "maintenance",
  "status": "success",
  "generation": 143,
  "response": {
    "operation": "stop",
    "state": "stopping"
  }
}
```

## Required Ordering

After a valid nonduplicate stop request becomes the active request, the
service:

1. accepts no later request for execution;
2. constructs the success response at the current committed generation;
3. delivers the complete success response;
4. moves the stop request to `inbox-processing/completed/`, retaining the
   exact request and response;
5. publishes stopping status as appropriate;
6. returns from the service command through normal shutdown;
7. releases the writer lock through `lionscliapp` normal cleanup.

The service must not exit successfully before Steps 3 and 4 complete.

If response delivery or terminal archival cannot complete, the stop request
remains the active request and no later request begins. The service retries or
enters an explicit operational error; it does not perform an abrupt exit that
leaves a successful stop request unarchived.

A completed stop request belongs to the service process that handled it. On a
later explicit service start, its retained completed record does not
automatically stop the new process.

---

# Common Success Envelope

Every successful maintenance response has:

```json
{
  "request-id": "<originating-request-id>",
  "request-type": "maintenance",
  "status": "success",
  "generation": 143,
  "response": {
    "operation": "<checkpoint | remove-old | stop>"
  }
}
```

The operation-specific fields are defined above.

---

# Failure Responses

A maintenance failure uses the common failure shape:

```json
{
  "request-id": "8ae7f0c8-8727-4d51-89ad-7b6d92d8e750",
  "request-type": "maintenance",
  "status": "failure",
  "generation": 143,
  "response": {
    "operation": "checkpoint",
    "error": {
      "code": "checkpoint-failed",
      "message": "The snapshot could not be validated."
    }
  }
}
```

For a partially executed `remove-old`, the failure response also includes
`mode`, `candidates`, and `removed`.

A failed maintenance request does not advance the generation.

Initial maintenance error codes include:

```text
invalid-maintenance-request
unsupported-maintenance-operation
invalid-remove-old-mode
checkpoint-failed
remove-old-failed
stop-failed

invalid-request-id
invalid-reply-destination
request-id-conflict
request-already-in-progress
reply-delivery-failed
internal-error
recovery-required
service-not-ready
```

---

# Duplicate Request Behavior

Maintenance operations may have durable operational effects even though they
do not mutate M1 entities.

Version 1 therefore makes terminal maintenance retries replayable and active
maintenance retries single-owned by `request-id`:

* a completed or failed maintenance record retains the complete original
  request and complete logical response;
* the same request ID with byte-equivalent logical request content reproduces
  or redelivers the retained response without executing the operation again;
* the same request ID with different content, including a different reply
  destination or remove-old mode, fails with `request-id-conflict`;
* a duplicate received while the original is active is not executed
  independently.

A claimed maintenance request interrupted before its terminal record is
resumed by the single service. Recovery inspects already completed operational
work and continues safely under the checkpoint or retention rules; it does not
start an independent second active execution.

A caller that intentionally wants to retry a terminally failed maintenance
operation submits a new request ID.

---

# Command Clients

The command-line commands:

```text
subete checkpoint
subete remove-old
subete stop
```

are FileTalk clients to the running service.

They:

1. read the selected database's `configuration.json`;
2. choose a unique reply file beneath the first configured
   `filetalk.allowed-reply-paths` directory;
3. create a UUID request ID;
4. write the maintenance request into the database inbox;
5. patiently wait for one complete response file;
6. report the response and exit appropriately.

They do not acquire the writer lock and do not directly create snapshots,
write checkpoints, remove database artifacts, or remove the service lock.

`remove-old` requires an explicit mode:

```text
subete --maintenance.mode dry-run remove-old
subete --maintenance.mode execute remove-old
```

Omitting or invalidly setting `maintenance.mode` is a command error and no
request is posted.

`checkpoint` and `stop` do not use `maintenance.mode`.

---

# Protocol Boundaries

The maintenance protocol does not define:

* arbitrary file deletion;
* caller-selected journal, snapshot, or checkpoint removal;
* entity mutation;
* database restoration;
* forced process termination;
* remote/network authentication;
* scheduling or periodic maintenance;
* concurrent maintenance execution.
