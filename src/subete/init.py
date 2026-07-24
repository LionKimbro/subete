"""Boot the current Subete process after Lionscliapp resolves its command line."""

from . import paths
from . import state


def init_system():
    """Establish the shared facts of the current Subete process."""
    paths.init_filesystem_paths()
    state.load_existing_database_id()
