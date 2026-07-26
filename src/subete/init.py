"""Boot the current Subete process after Lionscliapp resolves its command line."""

from . import filetalk, paths, request, state


def init_system():
    """Establish the shared facts of the current Subete process."""
    paths.system_init_filesystem_paths()
    filetalk.system_init_filetalk()
    request.system_init_request()
    state.load_existing_database_id()
    state.load_configuration()
