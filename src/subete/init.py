"""Boot the current Subete process after Lionscliapp resolves its command line."""

from . import filetalk, paths, state


def init_system():
    """Establish the shared facts of the current Subete process."""
    paths.init_filesystem_paths()
    filetalk.init_filetalk()
    state.load_existing_database_id()
    state.load_configuration()
