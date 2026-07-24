"""Boot the current Subete process after Lionscliapp resolves its command line."""

from . import paths


def init_system():
    """Establish the shared facts of the current Subete process."""
    paths.init_paths()
