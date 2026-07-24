# Required fields and proportionate validation

Normal code should primarily do the work it is meant to do.

Do not turn every function into a maze of assertions, presence checks,
and defensive branches when the operation depends on a record having a
required shape.  Use direct dictionary indexing for a required field:

```python
identity = read_json("identity")
state.g["database-id"] = identity["database-id"]
```

This is an honest statement of the operation: an identity record has a
database ID, and the current process is loading it.  If the JSON is not
an object or the required key is absent, ordinary Python fails exactly
where the false assumption was discovered.

Do not use `.get()` merely to avoid an exception:

```python
# Bad when database-id is required:
state.g["database-id"] = identity.get("database-id")
```

That can convert corruption into an ordinary-looking `None` value and
let later code misinterpret a broken database as an uninitialized one.

Use `.get()` when absence has a real, intended meaning and the program
has a genuine alternate behavior.  Use explicit validation at a
boundary when the system needs a clear protocol error, needs to protect
durable state, or must check a format before accepting it.

The default is:

> Use direct access for required fields.  Let normal code do its work.
> Add validation where it has a concrete job to do.
