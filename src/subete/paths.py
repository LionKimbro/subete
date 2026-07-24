"""The fixed filesystem layout of one Subete database."""

from pathlib import Path


def build_paths(dbroot):
    """Return the named paths belonging to *dbroot*."""
    root = Path(dbroot).expanduser().resolve()
    journal = root / "journal"
    processing = root / "inbox-processing"
    return {
        "root": root, "identity": root / "identity.json", "configuration": root / "configuration.json",
        "generation": root / "generation.json", "inbox": root / "inbox", "processing": processing,
        "claimed": processing / "claimed", "completed": processing / "completed", "failed": processing / "failed",
        "entities": root / "entities", "journal": journal, "journal_pending": journal / "pending",
        "journal_committed": journal / "committed", "checkpoints": journal / "checkpoints",
        "snapshots": root / "snapshots", "link_cache": root / "link-cache", "status": root / "status", "tmp": root / "tmp",
    }


def required_directories(paths):
    """Return the directories setup must create for a database."""
    return [paths[key] for key in (
        "root", "inbox", "processing", "claimed", "completed", "failed", "entities", "journal",
        "journal_pending", "journal_committed", "checkpoints", "snapshots", "link_cache", "status", "tmp",
    )]
