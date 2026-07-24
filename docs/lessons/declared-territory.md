# Declared territory and named places

A program's stable filesystem layout is part of its shared world.

Do not treat that layout as a loose dictionary of paths assembled by
whichever function happens to need it.  Declare the territory once, at
boot, in the module that owns the layout.

For Subete, each named place is a small record:

```python
paths["identity"] = {
    "path": root / "identity.json",
    "kind": "file",
    "required": True,
}
```

This makes the layout inspectable.  A reader can see not only where a
place is, but what it is and what setup is responsible for.

Use a small accessor for ordinary work:

```python
read_json_file(path("identity"))
write_json_replace(path("generation"), generation)
```

The name identifies the place inside the already-established world.  It
does not ask the caller to carry or choose the whole world again.

Keep metadata beside the thing it describes.  If setup needs to create
required directories, derive that from the declarations:

```python
def required_directories():
    return [
        entry["path"]
        for entry in paths.values()
        if entry["kind"] == "directory"
        and entry["required"]
    ]
```

This avoids parallel lists of all paths, directories, and required
directories that can drift apart.

The boundary remains important:

- Caller-chosen paths are arguments.
- Stable places belonging to this running program are declared territory.
- The paths module owns the declaration.
- The initialization module establishes it at boot.

The goal is not a universal path registry.  It is an honest map of the
small fixed territory that this particular machine owns.
