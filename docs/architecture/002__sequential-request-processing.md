# ADR 002 — Process Requests Sequentially in Version 1

## Status

Accepted.

## Context

Subete has one authoritative world, one writer, a write-ahead journal, and generation-based read/search responses. Concurrent request execution would require additional scheduling, snapshot-isolation, response-recovery, and duplicate-resolution machinery.

Version 1 deliberately favors a small, inspectable, recoverable service over request parallelism.

## Decision

Version 1 processes exactly one claimed request at a time, from validation through response delivery or terminal archival.

No later request may begin execution while the active request is executing, recovering, delivering a reply, or awaiting terminal archival. Consequently, no database mutation can occur between an interrupted read or search and its startup-recovery rerun.

## Consequences

Transactions have a total execution order. Reads and searches observe one stable committed generation, and an unfinished claimed read or search can be rerun after restart at that same generation without a durable result record.

Throughput is intentionally limited by serialized request handling. A future concurrency design must replace or revise this ADR together with the relevant isolation, duplicate, generation, and recovery rules.

## Alternatives Rejected

**Concurrent reads with serialized writes.** Rejected for Version 1 because it complicates the recovery guarantee for interrupted read/search replies and introduces additional scheduling and isolation semantics.

**General concurrent request processing.** Rejected because it expands the failure surface without serving the Version 1 priority of simple, durable operation.
