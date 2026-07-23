# Subete — FileTalk Protocol

This document defines the shared protocol for communicating with Subete through FileTalk.

A FileTalk interaction consists of placing one JSON message file into the Subete inbox and, when requested, receiving a reply at a file destination supplied by the sender.

This protocol applies to all Subete FileTalk message families, including requests, commands, notifications, and future forms of interaction.

Message-family protocols define:

* the semantic content of their messages;
* their required and optional fields;
* message identity, when applicable;
* duplicate and retry behavior, when applicable;
* whether a reply is required, optional, or forbidden;
* the meaning and structure of any reply.

This document defines:

* the shared Subete FileTalk envelope;
* inbox file delivery;
* incomplete-file handling;
* optional file reply delivery;
* delivery failures.

The structures in this document are written as Markdown SoftSpec. Examples illustrate intended meaning and may omit fields that are not relevant to the example.

---

# Message Files

Each inbox file contains one complete JSON message object.

Every file directly contained in the Subete inbox is treated as a candidate message file. Directories are ignored.

The inbox is flat. Subete does not search subdirectories.

The filename and filename extension have no semantic meaning. Subete reads the file contents as JSON.

The inbox filename is not the identity of the message. A message-family protocol may define an identity field within the message itself.

---

# Subete Message Envelope

Subete FileTalk messages do not all use one universal semantic structure.

Each message-family protocol defines the fields that identify and carry that kind of message.

For example, a request might look like:

```json
{
  "request-id": "7be711d6-5801-4e28-a300-81772985bcbb",
  "request-type": "transaction",
  "reply": {
    "type": "file",
    "path": "D:/tmp/subete-replies/7be711d6-5801-4e28-a300-81772985bcbb.json"
  },
  "request": {
    "...": "request-family-specific content"
  }
}
```

A one-way notification might look like:

```json
{
  "notification-id": "e748c5ff-a346-47f6-b5cd-319e661dc028",
  "notification-type": "example-notification",
  "notification": {
    "event": "example-event"
  }
}
```

Message families may use different semantic envelopes, but shared Subete delivery fields are placed at the top level of the message object.

The currently defined shared delivery field is `reply`.

---

# Shared Delivery Field: `reply`

When a message family supports replies, the message may carry a top-level `reply` field.

```json
{
  "type": "object",
  "required": false
}
```

When present, `reply` describes where Subete should deliver its reply.

The message-family protocol determines whether `reply` is:

* required;
* optional;
* forbidden.

A message without `reply` is one-way at the delivery layer.

Subete must not infer a reply destination from:

* the inbox filename;
* the sender’s location;
* the current working directory;
* any other ambient state.

The initial Subete FileTalk protocol supports file reply destinations.

Additional destination types may be defined later.

---

# Inbox File Delivery

A sender delivers a message by writing a JSON file directly into the Subete inbox.

The sender may write directly to the final inbox filename.

Atomic delivery by writing a temporary file and renaming it into the inbox is permitted, but it is not required. It is only available when the temporary file and final inbox filename are on the same filesystem; a move across drives or filesystems is not an atomic rename.

Because direct writing is permitted, a file visible in the inbox may still be incomplete.

Subete must not assume that every visible inbox file is ready to process.

---

# Incomplete Files

When Subete cannot yet read an inbox file as one complete JSON message object, it should normally treat the file as still being written.

Subete should:

* skip the file for the current polling cycle;
* attempt to read it again during a later polling cycle;
* avoid immediately treating it as bad input.

Subete may keep short-term observations about an unreadable file, including:

* filename;
* file size;
* modification time;
* time first observed;
* time most recently observed changing.

Subete is not required to retain these observations.

Continued changes in file size or modification time may be treated as evidence that the file is still being written.

If a file remains unchanged and unreadable beyond a configured quiet period, Subete may treat it as stale or abandoned.

The quiet period and stale-file handling policy are operational configuration. `formats/configuration.md` defines the Version 1 action vocabulary and its non-destructive default.

A stale file may, according to configuration:

* be deleted;
* be moved to a bad-input or failed-input location;
* be retained and reported;
* be handled by another configured policy.

A complete JSON object that is invalid under its message-family protocol is bad input, not an incomplete write.

---

# Claiming and Processing

Subete claims a message only after it can read the file as one complete JSON message object.

Once claimed, the message is interpreted according to its message-family protocol.

The message-family protocol determines:

* whether the message is structurally valid;
* whether it is semantically valid;
* whether it has an identity;
* how repeated delivery is handled;
* whether processing produces a reply.

This shared FileTalk protocol does not require request semantics, request identifiers, duplicate suppression, or retries.

Those behaviors belong to the applicable message-family protocol.

---

# File Reply Destination

A file reply destination has this form:

```json
{
  "type": "file",
  "path": "D:/tmp/subete-replies/result.json"
}
```

## Fields

### `type`

```json
{
  "const": "file",
  "required": true
}
```

Identifies the destination as a file destination.

### `path`

```json
{
  "type": "file-path",
  "required": true
}
```

The file path at which Subete should write the reply.

The path is interpreted in Subete’s filesystem environment.

---

# File Reply Delivery

Subete may write the reply directly to the specified path.

Subete is not required to use a temporary file and atomic rename.

The reply path names one complete reply file.

Subete may replace an existing file at the specified reply path.

The sender is responsible for choosing a reply path that is appropriate for the interaction and does not conflict with unrelated replies.

A sender may use a unique request identifier, UUID, or another naming convention when constructing the reply path.

The reply destination must satisfy Subete’s configured destination policy, defined by `formats/configuration.md`.

In particular, it must not point into Subete’s authoritative internal storage unless explicitly allowed by configuration.

---

# Reading Reply Files

Because Subete may write directly to the final reply path, a visible reply file may still be incomplete.

A reply recipient should apply the same patient reading behavior used by Subete for inbox files.

When the reply file cannot yet be read as one complete JSON reply object, the recipient should:

* skip it for the current polling cycle;
* attempt to read it again later;
* avoid immediately treating it as malformed.

The recipient may observe file size, modification time, and elapsed quiet time to identify a reply file that appears stale or abandoned.

Atomic reply delivery remains a permitted optimization, but it is not required by this protocol. It is only available when the temporary file and final reply path are on the same filesystem; a move across drives or filesystems is not an atomic rename.

---

# Processing and Reply Delivery Are Separate

Message processing and reply delivery are separate operations.

Subete may successfully process a message and then fail to deliver its reply.

A reply-delivery failure does not:

* reverse committed state;
* undo a completed operation;
* cause a successful message to become unprocessed;
* require the logical operation to be performed again.

The applicable message-family protocol determines what outcome Subete records for the processed message.

---

# Shared Delivery Errors

Shared delivery errors include:

```text
invalid-reply-destination
reply-delivery-failed
```

`invalid-reply-destination` means that Subete rejected the supplied destination because it was invalid or disallowed by configuration.

`reply-delivery-failed` means that Subete accepted the destination but could not successfully write the reply.

A delivery error may be recorded even when it cannot itself be delivered to the requested reply destination.

Message-family protocols define their own structural, semantic, identity, service-state, and operation-specific errors.
