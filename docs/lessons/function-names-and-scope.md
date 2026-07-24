# Function names and scope

Function names should tell a reader both what an operation does and how
widely it is meant to be used.

Use a verb-noun name for an action:

```python
setup_database()
validate_database()
```

These names are short because they are public actions or actions used
from more than one place.  A short name signals that the operation is a
real capability of the module, not merely one private step in a single
procedure.

When a function is called in only one place, give it a longer, specific
name.  Its job is to make the containing procedure readable as a
sequence of named steps:

```python
_create_required_directories()
_reject_incomplete_root_metadata()
_create_identity_record()
_write_initial_configuration_record()
_write_generation_zero_record(identity)
```

The leading underscore is a separate decision.  It says that a function
is internal to this module: another module should not ordinarily call
it.  The private setup steps above are both long and underscored because
they are one-use steps owned by `setup.py`.

Sometimes a deliberately one-use, long, specific function thematically
belongs in another module.  In that case, leave off the underscore.  Its
long name still says that it is a particular operation rather than a
small general utility; its lack of an underscore says that cross-module
use is part of the intended design.

This produces a useful contrast:

```python
def setup_database():
    _create_required_directories()

    if state.g["database-id"]:
        validate_database()
        return "existing"

    _reject_incomplete_root_metadata()
    ...
```

The public procedure has a compact name.  Its private, one-use steps
are long enough to explain themselves.  The result is code that reads
as an account of this exact machine, rather than a collection of vague
or falsely reusable helper functions.

Do not make names long merely to be formal.  Two signals are at work:

- short names are usually for reusable or public operations;
- long names are usually for one-use, exact operations;
- a leading underscore marks module-internal ownership;
- name length and underscore privacy are independent choices.
