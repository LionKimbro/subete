
# Subete — Big Picture

Subete is a single authoritative world of M1 entities.

It exists to give programs a common place to store, retrieve, connect, search, and safely modify shared structured information. Instead of every application maintaining entirely isolated identities for common things like people, projects, files, events, documents, products, conversations, and relationships, Subete provides one shared space of stable identities and shared facts.

In the M1 model, each thing is an entity. An entity has a stable identifier and any number of aspects describing what is known about it. Links are themselves entities, so relationships participate in the same model as everything else.

Subete maintains one current authoritative state. It is not a layered M1 runtime and does not resolve competing document priorities. The authoritative world is the committed state of its entities and aspects.

Subete runs as a single authoritative database process. Other programs do not directly edit its internal storage. They communicate with it through FileTalk requests placed into an inbox. Each request includes its own return destination, following the SASE pattern.

The main request families are:

* transactions;
* reads;
* searches.

Transactions may create or delete entities, add or replace aspects, delete aspects, and modify multiple entities in one operation, as a single unit.

Reads retrieve complete aspects from one or more entities. A caller may request selected aspects or all known aspects of an entity.

Searches discover entities by properties from the basic aspect (such as typehint, tags, name, title, text content), or by the presence of aspects (indicating the "real" type(s) of the entity), or by link relationships.

The system is durable and ACID. Transactions are protected by write-ahead journaling and receive monotonically increasing journal sequence numbers when committed. The database maintains a corresponding generation number, preserves snapshots at identified generations, and uses checkpoints to establish safe recovery and journal-replay boundaries.

Subete also publishes a read-only status surface describing its current generation, process state, heartbeat, counts, recent activity, recovery state, and the freshness of derived services such as indexes.

The long-term vision is a durable, searchable, interconnected memory substrate shared across many programs: one world of identities, aspects, and links, broad enough to represent the central structure of a complex data ecology.
