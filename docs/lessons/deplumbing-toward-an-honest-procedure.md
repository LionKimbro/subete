# Deplumbing toward an honest procedure

The function-arguments rule says that caller choices belong in arguments
and established context does not.  This lesson is about the process of
getting from over-plumbed code to code that tells the truth about the
machine it is running.

Start with a working procedure, even if it is crowded:

```python
def setup_database(dbroot):
    paths = build_paths(dbroot)
    ...
```

Then ask about each argument and each local value carried through the
procedure:

> Is the caller choosing this now, or is it already a fact of this
> program run?

If it is an established fact, do not simply hide it.  Give it an honest
home and establish it at the right boundary.

For Subete, the execution root is resolved by Lionscliapp.  At boot,
`init_system()` derives the declared filesystem territory.  The current
database ID is then held in `state.g`.  `setup_database()` does not need
to receive either fact as an argument.

Refactor in small, safe movements:

1. Establish one shared fact at a clear boot boundary.
2. Give that fact a visible owner, such as `paths.py` or `state.py`.
3. Replace one plumbing argument with the established fact.
4. Move path lookup, validation, or I/O to the smallest operation that
   owns its meaning.
5. Give each remaining real obligation a precise name.
6. Keep the procedure's meaningful outcome visible and simple.
7. Run the relevant tests before making the next movement.

Do not remove arguments indiscriminately.  A caller-chosen entity ID,
an explicit file path, or a record being written is real variation and
should remain an argument.  The goal is not fewer parameters for their
own sake.  The goal is to remove false choices and courier variables.

The result should be a procedure that can be read as an account of what
it actually does:

```python
def setup_database():
    if state.g["database-id"]:
        validate_database()
        return "existing"

    _create_required_directories()
    _reject_incomplete_root_metadata()

    _create_identity_record()
    _write_initial_configuration_record()
    _write_generation_zero_record()

    return "created"
```

The details have not vanished.  They have moved behind the names of the
obligations that own them.  The top-level procedure is no longer a
coordinator carrying the world from function to function.  It is the
machine stating its intention.
