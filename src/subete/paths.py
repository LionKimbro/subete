"""The fixed filesystem layout of the current Subete database."""

from pathlib import Path

import lionscliapp as app


g = {
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


def init_paths():
    """Install the filesystem facts for Lionscliapp's selected execution root."""
    root = Path(app.execroot.get_execroot()).expanduser().resolve()
    journal = root / "journal"
    processing = root / "inbox-processing"

    g["root"] = root
    g["identity"] = root / "identity.json"
    g["configuration"] = root / "configuration.json"
    g["generation"] = root / "generation.json"
    g["inbox"] = root / "inbox"
    g["processing"] = processing
    g["claimed"] = processing / "claimed"
    g["completed"] = processing / "completed"
    g["failed"] = processing / "failed"
    g["entities"] = root / "entities"
    g["journal"] = journal
    g["journal_pending"] = journal / "pending"
    g["journal_committed"] = journal / "committed"
    g["checkpoints"] = journal / "checkpoints"
    g["snapshots"] = root / "snapshots"
    g["link_cache"] = root / "link-cache"
    g["status"] = root / "status"
    g["tmp"] = root / "tmp"


def required_directories():
    """Return the directories setup must create for the current database."""
    return [
        g["root"],
        g["inbox"],
        g["processing"],
        g["claimed"],
        g["completed"],
        g["failed"],
        g["entities"],
        g["journal"],
        g["journal_pending"],
        g["journal_committed"],
        g["checkpoints"],
        g["snapshots"],
        g["link_cache"],
        g["status"],
        g["tmp"],
    ]
