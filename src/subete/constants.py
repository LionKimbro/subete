"""Stable Subete format identifiers and initial defaults."""

CONFIGURATION_VERSION = 1
GENERATION_FORMAT_VERSION = 1

INITIAL_CONFIGURATION = {
    "configuration-version": CONFIGURATION_VERSION,
    "polling": {
        "inbox-interval-seconds": 1,
        "incomplete-file-quiet-seconds": 20,
        "stale-inbox-file-action": "retain-and-report",
    },
    "filetalk": {"allowed-reply-paths": []},
}
