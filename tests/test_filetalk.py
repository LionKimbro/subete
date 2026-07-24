import json

import pytest

from subete.filetalk import claim_message, deliver_reply, discover_messages, reset, stale_unreadable
from subete.paths import build_paths
from subete.setup import setup_database


def prepared(tmp_path):
    paths = build_paths(tmp_path / "database")
    setup_database(paths["root"])
    return paths


def test_discovery_skips_incomplete_then_claims_complete_object(tmp_path):
    paths = prepared(tmp_path)
    candidate = paths["inbox"] / "request.json"
    candidate.write_text('{"request-id":', encoding="utf-8")
    reset()
    assert discover_messages(paths, 1) == []
    assert stale_unreadable(paths, 21, 20) == [candidate]
    candidate.write_text('{"request-id":"ok"}', encoding="utf-8")
    messages = discover_messages(paths, 22)
    assert messages[0]["message"] == {"request-id": "ok"}
    assert claim_message(paths, candidate).parent == paths["claimed"]


def test_discovery_does_not_claim_complete_non_object(tmp_path):
    paths = prepared(tmp_path)
    (paths["inbox"] / "array.json").write_text("[]", encoding="utf-8")
    assert discover_messages(paths, 1) == []


def test_reply_delivery_requires_configured_external_absolute_path(tmp_path):
    paths = prepared(tmp_path)
    replies = tmp_path / "replies"
    replies.mkdir()
    config = {"filetalk": {"allowed-reply-paths": [str(replies)]}}
    target = replies / "answer.json"
    delivered = deliver_reply(paths, config, {"type": "file", "path": str(target)}, {"ok": True})
    assert delivered == target
    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    with pytest.raises(ValueError, match="invalid"):
        deliver_reply(paths, config, {"type": "file", "path": str(paths["root"] / "bad.json")}, {})
