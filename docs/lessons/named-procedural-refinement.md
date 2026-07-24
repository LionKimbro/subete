# Named procedural refinement

A top-level procedure should read like the intention of the machine at
that level.

For example, validating a Subete database currently means three clear
obligations:

```python
def validate_database():
    """Validate the core records required before this process can use the database."""
    validate_database_identity()
    validate_database_configuration()
    validate_database_generation()
```

The top-level procedure does not carry record data, choose paths, or
branch over missing files.  Those details have not been removed; they
have moved to the smallest operation that understands their meaning.

For example, `validate_database_identity()` owns the fact that identity
must be read from the fixed `identity` territory.  `read_json()` owns
the optional `verify-file` behavior because it is the operation that
crosses from a named territory to an opened JSON file.

```python
def validate_database_identity():
    data = read_json("identity", ["verify-file"])
    ...
```

This is named procedural refinement:

1. State the high-level obligations in story order.
2. Give each real obligation a precise name.
3. Descend one level only inside the named operation that owns the
   details.
4. Keep preparation, conditionals, and data fetching with the operation
   that gives them meaning.

The goal is not to hide complexity behind vague helpers.  Each function
name must tell the reader what concrete obligation it fulfills.  A
reader can follow the main procedure as a short account of the machine's
intention, then descend into a named step when the implementation detail
matters.

Shared context makes this shape possible.  Once the program has
established its database territory at boot, high-level procedures do not
need to carry that territory from call to call.  They can name the work
that needs doing instead.

The guiding rule is:

> Make the top-level function read like the machine's intention.  Put
> each piece of machinery behind the name of the obligation it fulfills.
