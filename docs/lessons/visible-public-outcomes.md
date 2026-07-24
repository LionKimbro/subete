# Keep public outcomes visible

Do not extract a helper merely because a few lines can be extracted.

In particular, keep a function's externally meaningful result visible
in the function that promises it.  A result dictionary is often part of
the operation's public contract, not an implementation detail to hide
behind a helper name.

For Subete setup, the two outcomes should be visible together:

```python
if state.g["database-id"]:
    validate_database()

    return "existing"

...

return "created"
```

This lets a reader understand the setup outcome without leaving
`setup_database()`: an existing valid database is reported as
`"existing"`, and a newly initialized database is reported as
`"created"`.  The already-established database ID belongs in live
process state, where the command layer can use it when presenting that
outcome to the user.

A helper is valuable when it owns a real named obligation, a separate
piece of machinery, or a reusable operation.  A helper that only
packages the current function's public return value can obscure the
very behavior the reader came to inspect.

The rule is:

> Keep a public outcome in view unless extracting it reveals a real,
> separately meaningful operation.
