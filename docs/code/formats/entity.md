# Subete — Entity Files

Entity files are the initial authoritative storage format for Subete entities.

They are stored beneath:

```text
subete-data/
  entities/
```

## Filename

Each entity file is named from its entity ID:

```text
<encoded-entity-id>.json
```

UUID entity IDs remain unchanged:

```text
209ee0b8-36d5-4a47-81ca-c59f0eaac29d.json
```

Entity IDs containing characters unsafe for filenames are encoded using UTF-8 percent encoding:

```text
tag%3Am1lattice.net%2C2026%3Aexample.json
```

The entity ID inside the file is authoritative. The filename is its filesystem representation.

## Format

```json
{
  "entity": "209ee0b8-36d5-4a47-81ca-c59f0eaac29d",
  "revision": 12,
  "aspects": {
    "tag:m1lattice.net,2026/aspect/basic": {
      "typehint": "person",
      "name": "lion",
      "title": "Lion Kimbro",
      "tags": [
        "programmer",
        "writer"
      ]
    },
    "tag:example.net,2026/aspect/contact": {
      "email": "lion@example.net"
    }
  }
}
```

## Fields

### `entity`

```json
{
  "type": "entity-id",
  "required": true
}
```

The stable identifier of the entity.

It must agree with the entity ID represented by the filename.

### `revision`

```json
{
  "type": "integer",
  "required": true,
  "minimum": 1
}
```

The current committed revision of the entity.

A newly created entity begins at revision `1`.

A transaction that changes the entity advances its revision by one, regardless of how many aspects it changes.

### `aspects`

```json
{
  "type": "object",
  "required": true
}
```

Maps aspect IDs to their complete authoritative values.

An existing entity may have an empty `aspects` object.

## Rules

* Each file contains one JSON object.
* Each entity has at most one authoritative entity file in `entities/`.
* Aspect values are stored wholesale.
* Aspect IDs are JSON object keys and are compared exactly.
* Removing the final aspect does not remove the entity file.
* Deleting the entity removes its entity file.
* Entity files contain committed state only.
* Temporary replacement files belong in `tmp/` until promoted into authoritative storage.
* A partially applied transaction must not be exposed as a committed generation.
* JSON object key order has no semantic meaning.
* Files are encoded as UTF-8.

## Hybrid Storage

The logical entity may later include aspects held in other authoritative storage mechanisms.

When hybrid storage is introduced:

* the entity revision still describes the complete logical entity across all authoritative stores;
* an aspect has exactly one authoritative current location;
* `aspects` contains only the aspects assigned to the entity-file store;
* reads assemble the logical entity from all applicable authoritative stores;
* transactions and recovery keep every authoritative store at one committed generation.

The entity file remains authoritative for the entity metadata and aspects assigned to it.
