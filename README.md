# Subete

Subete is a durable, filesystem-backed authoritative database for M1 entities.

The initial foundation can create or validate a database root:

```text
subete --execroot C:/data/subete setup
```

It creates the Version 1 directory layout, a stable database identity, operational
configuration, and authoritative generation zero. Transaction, read, search, and
service processing are implemented in later stages.

`--execroot` selects the database root. Lion's framework-owned `config.json` may
also appear there when its CLI configuration is persisted; it is distinct from
Subete's operational `configuration.json`.
