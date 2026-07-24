"""Startup reconciliation of pending journal obligations."""
from .fsio import read_json_file
from .journal import apply_pending, commit_pending

def recover_pending(paths, database_id):
    """Complete pending journals in ascending sequence order."""
    recovered = []
    for pending in sorted(paths["journal_pending"].glob("*.json")):
        entry = read_json_file(pending)
        if entry.get("database-id") != database_id: raise ValueError("journal-database-mismatch")
        apply_pending(paths, pending)
        commit_pending(paths, pending, database_id)
        recovered.append(entry["sequence"])
    return recovered
