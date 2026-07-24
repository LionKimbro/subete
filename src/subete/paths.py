"""The fixed filesystem layout of the current Subete database."""

from pathlib import Path

import lionscliapp as app


paths = {
    "root": None,
    "identity": None,
    "configuration": None,
    "generation": None,
    "inbox": None,
    "processing": None,
    "claimed": None,
    "completed": None,
    "failed": None,
    "entities": None,
    "journal": None,
    "journal_pending": None,
    "journal_committed": None,
    "checkpoints": None,
    "snapshots": None,
    "link_cache": None,
    "status": None,
    "tmp": None,
}


def init_path(name, value, flags=None):
    """Declare one named place in the current Subete filesystem territory."""
    if flags is None:
        flags = []

    paths[name] = {
        "path": value,
        "kind": "directory" if "directory" in flags else "file",
        "required": "required" in flags,
    }


def init_filesystem_paths():
    """Install the filesystem facts for Lionscliapp's selected execution root."""
    root = Path(app.execroot.get_execroot()).expanduser().resolve()
    journal = root / "journal"
    processing = root / "inbox-processing"

    init_path("root", root, ["directory", "required"])
    init_path("identity", root / "identity.json", ["required"])
    init_path("configuration", root / "configuration.json", ["required"])
    init_path("generation", root / "generation.json", ["required"])
    init_path("inbox", root / "inbox", ["directory", "required"])
    init_path("processing", processing, ["directory", "required"])
    init_path("claimed", processing / "claimed", ["directory", "required"])
    init_path("completed", processing / "completed", ["directory", "required"])
    init_path("failed", processing / "failed", ["directory", "required"])
    init_path("entities", root / "entities", ["directory", "required"])
    init_path("journal", journal, ["directory", "required"])
    init_path("journal_pending", journal / "pending", ["directory", "required"])
    init_path("journal_committed", journal / "committed", ["directory", "required"])
    init_path("checkpoints", journal / "checkpoints", ["directory", "required"])
    init_path("snapshots", root / "snapshots", ["directory", "required"])
    init_path("link_cache", root / "link-cache", ["directory", "required"])
    init_path("status", root / "status", ["directory", "required"])
    init_path("tmp", root / "tmp", ["directory", "required"])


def path(name):
    """Return the filesystem path declared for one named territory."""
    return paths[name]["path"]


def required_directories():
    """Return the directories setup must create for the current database."""
    return [
        entry["path"]
        for entry in paths.values()
        if entry["kind"] == "directory" and entry["required"]
    ]
