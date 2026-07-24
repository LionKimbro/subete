import json

import pytest

from subete.filetalk import claim_message, deliver_reply, discover_messages, reset, stale_unreadable
from subete.paths import path
from subete.setup import setup_database


def prepared(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()


def test_discovery_skips_incomplete_then_claims_complete_object(tmp_path, use_database):
    prepared(tmp_path, use_database)
    candidate = path("inbox") / "request.json"
    candidate.write_text('{"request-id":', encoding="utf-8")
    reset()
    assert discover_messages(1) == []
    assert stale_unreadable(21, 20) == [candidate]
    candidate.write_text('{"request-id":"ok"}', encoding="utf-8")
    messages = discover_messages(22)
    assert messages[0]["message"] == {"request-id": "ok"}
    assert claim_message(candidate).parent == path("claimed")


def test_discovery_does_not_claim_complete_non_object(tmp_path, use_database):
    prepared(tmp_path, use_database)
    (path("inbox") / "array.json").write_text("[]", encoding="utf-8")
    assert discover_messages(1) == []


def test_reply_delivery_requires_configured_external_absolute_path(tmp_path, use_database):
    prepared(tmp_path, use_database)
    replies = tmp_path / "replies"
    replies.mkdir()
    config = {"filetalk": {"allowed-reply-paths": [str(replies)]}}
    target = replies / "answer.json"
    delivered = deliver_reply(config, {"type": "file", "path": str(target)}, {"ok": True})
    assert delivered == target
    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    with pytest.raises(ValueError, match="invalid"):
        deliver_reply(config, {"type": "file", "path": str(path("root") / "bad.json")}, {})
