# Boot boundaries: when a program's world becomes real

This lesson came from wiring Subete's `--execroot` into its setup
operation.

At first, it was tempting to treat the database root as an ordinary
function argument:

```python
setup_database(app.execroot.get_execroot())
```

That call is technically workable, but it tells the wrong story.  The
command is not choosing a database each time it calls setup.  The
framework has already chosen the execution root for this run.  Setup is
simply acting inside that established database world.

The important boundary is the moment at which outside information has
been fully resolved.  Before that point, the command line and framework
are still deciding where the program will operate.  At that point, the
program should:

1. read the resolved external choice once;
2. normalize it once;
3. derive the durable facts that follow from it;
4. install those facts into visible shared state.

After that, the interior of the program should use the established
facts.  It should not repeatedly ask the framework for the execution
root, recreate the path layout, or pass the same context from function
to function.

For Subete, `init.init_system()` is that boundary.  It runs after
Lionscliapp has resolved `--execroot`.  Today it calls
`paths.init_paths()`, which fills `subete.paths.g` with the root,
metadata paths, inbox paths, journal paths, and other fixed facts of
the current database.  Later, it can establish other process-wide
database facts without making the paths module responsible for them.

```python
def cmd_setup():
    init.init_system()
    result = setup_database()
    print(f"Subete database {result['status']}: {result['database-id']}")
```

This makes the program easier to read and inspect.  A debugger can show
which database the process believes it owns.  A setup function can read
like an action of the current database machine rather than a function
that is being handed a portable database-shaped packet.

The same shape helps tests.  A test selects a temporary execution root,
initializes the context, and then exercises the same zero-argument
operations as the real command.  The test has an explicit boot step
rather than a secret alternate path-construction interface.

The principle is:

> Configuration arrives at the edge.  Context is established at boot.
> The program's operations act inside the established world.

This does not mean that every value should be global.  A value that a
caller genuinely chooses still belongs in an argument.  The point is
that stable facts about this one running program are context, not
repeated caller choices.
