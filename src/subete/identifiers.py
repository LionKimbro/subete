"""M1 v3 entity and aspect identifier normalization."""

import re
from datetime import date
from uuid import UUID

UUID_TEXT = re.compile(r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$")
TAG_URI = re.compile(r"^tag:([^,:\s]+),([0-9]{4}(?:-[0-9]{2}(?:-[0-9]{2})?)?):([^\s]*)$")


def normalize_entity_id(value):
    """Return M1 v3's canonical UUID or exact validated Tag URI."""
    if not isinstance(value, str):
        raise ValueError("entity ID must be a UUID or Tag URI string")
    if UUID_TEXT.fullmatch(value):
        return str(UUID(value))
    tag_match = TAG_URI.fullmatch(value)
    if tag_match is None:
        raise ValueError("entity ID must be a standard UUID or RFC 4151 Tag URI")
    validate_tag_date(tag_match.group(2))
    return value


def validate_tag_date(value):
    """Validate the RFC 4151 date component without rewriting it."""
    if len(value) == 4:
        return
    try:
        if len(value) == 7:
            date.fromisoformat(f"{value}-01")
        else:
            date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Tag URI has an invalid date") from error
