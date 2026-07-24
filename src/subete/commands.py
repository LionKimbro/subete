"""The small lionscliapp command surface for Subete."""

import lionscliapp as app

from .setup import setup_database
from .service import run_service


def cmd_setup():
    """Create or validate the configured database root."""
    result = setup_database()
    print(f"Subete database {result['status']}: {result['database-id']}")


def cmd_not_specified():
    """Keep reserved command names visible without inventing a protocol."""
    print("This command is reserved; its Version 1 request protocol is not implemented yet.")

def cmd_service():
    run_service()


def declare_application():
    """Declare Subete's framework-owned command surface."""
    app.declare_app("subete", "0.1.0")
    app.describe_app("A durable, filesystem-backed authoritative M1 entity database.")
    app.declare_projectdir(".")
    app.set_flag("allow_projectdir_override", False)
    app.set_flag("uses_locking", True)
    app.declare_cmd("setup", cmd_setup)
    app.describe_cmd("setup", "Create or validate a generation-zero Subete database.")
    app.set_cmd_flag("setup", "locking", True)
    app.declare_cmd("service", cmd_service)
    app.describe_cmd("service", "Run the authoritative Subete database service.")
    app.set_cmd_flag("service", "locking", True)
    app.declare_cmd("gui", cmd_not_specified)
    app.describe_cmd("gui", "Run the read-only Subete monitor.")
    app.declare_cmd("checkpoint", cmd_not_specified)
    app.describe_cmd("checkpoint", "Reserved until its FileTalk request protocol is implemented.")
    app.declare_cmd("remove-old", cmd_not_specified)
    app.describe_cmd("remove-old", "Reserved until its FileTalk request protocol is implemented.")
    app.declare_cmd("stop", cmd_not_specified)
    app.describe_cmd("stop", "Request orderly shutdown from the running service.")


def main():
    """Run the CLI after all declarations are complete."""
    declare_application()
    app.main()


if __name__ == "__main__":
    main()
