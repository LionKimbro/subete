"""Startup reconciliation of pending journal obligations."""
from .journal import apply_pending, commit_pending, read_validated_journal_entry
from .paths import path

def recover_pending(database_id):
    """Complete pending journals in ascending sequence order."""
    recovered = []
    for pending in sorted(path("journal_pending").glob("*.json")):
        entry = read_validated_journal_entry(pending)
        if entry.get("database-id") != database_id: raise ValueError("journal-database-mismatch")
        apply_pending(pending)
        commit_pending(pending, database_id)
        recovered.append(entry["sequence"])
    return recovered
