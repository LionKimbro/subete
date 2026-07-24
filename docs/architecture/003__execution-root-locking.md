# ADR 003 — Bind Database Ownership to Lion's Execution Root

## Status

Accepted.

## Context

`lionscliapp` locates its project root at `<execroot>/<project-dir>` and
places `lock.json` there. Its generic configuration keys may be overridden
while startup builds the command context, but framework locking occurs before
the command handler runs.

An independent `execpath.dbroot` selector would therefore allow a command to
operate on one database while Lion locks the launch directory's project root.
Adding a framework pre-lock validation extension or a second Subete lock would
solve that mismatch, but both expand the work beyond the Version 1 need.

## Decision

For Version 1, the Lion execution root is the Subete database root.

* Operators select a database with `subete --execroot <database-root> <command>`.
* Subete declares Lion's project directory as `.` and forbids `--project-dir`
  overrides.
* Subete enables Lion locking. `setup` and the future `service` command require
  that lock.
* Subete does not expose a separately configurable `execpath.dbroot` key.
* Lion's optional root `config.json` is framework-owned CLI configuration;
  Subete's `configuration.json` remains the operational database configuration.

## Consequences

A lock-requiring command holds exactly `<database-root>/lock.json`, so commands
targeting the same database share one lock regardless of their launch directory.
The integration is small and uses Lion's existing behavior without framework
changes or a second locking protocol.

The root directory may contain both `config.json` and `configuration.json`.
Operators must not treat the former as Subete database state.

The generic database-root option is intentionally unavailable. A future need
for an independent database-root key requires a pre-lock framework validation
mechanism or a replacement ADR; it must not be added as a command-handler-only
check.

## Alternatives Rejected

**Keep `execpath.dbroot` and validate it in command handlers.** Rejected because
the framework lock has already been acquired by then, so the critical lock/root
invariant is not enforced before locking.

**Keep `.subete` as the project directory.** Rejected because the lock would
belong to the execution directory rather than the selected database root.

**Add a second Subete lock.** Rejected for expedience: it duplicates ownership
semantics that Lion already provides.

**Extend Lion immediately.** Rejected for expedience. Existing execution-root
selection and project-directory binding fully meet Version 1's requirement.
