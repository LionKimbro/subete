import json

import pytest

from subete import state
from subete.filetalk import (
    claim_inbox_message,
    deliver_reply,
    discover_messages,
    list_stale_unreadable_messages,
    reset_filetalk_observations,
)
from subete.paths import path
from subete.setup import setup_database


def prepared(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()


def test_discovery_skips_incomplete_then_claims_complete_object(tmp_path, use_database, monkeypatch):
    prepared(tmp_path, use_database)
    now = {"value": 1}
    monkeypatch.setattr(state.time, "time", lambda: now["value"])
    candidate = path("inbox") / "request.json"
    candidate.write_text('{"request-id":', encoding="utf-8")
    reset_filetalk_observations()
    state.update_now()
    assert discover_messages() == []
    now["value"] = 21
    state.update_now()
    assert list_stale_unreadable_messages() == [candidate]
    candidate.write_text('{"request-id":"ok"}', encoding="utf-8")
    now["value"] = 22
    state.update_now()
    messages = discover_messages()
    assert messages[0]["message"] == {"request-id": "ok"}
    assert claim_inbox_message(candidate).parent == path("claimed")


def test_discovery_does_not_claim_complete_non_object(tmp_path, use_database, monkeypatch):
    prepared(tmp_path, use_database)
    monkeypatch.setattr(state.time, "time", lambda: 1)
    (path("inbox") / "array.json").write_text("[]", encoding="utf-8")
    state.update_now()
    assert discover_messages() == []


def test_reply_delivery_requires_configured_external_absolute_path(tmp_path, use_database):
    prepared(tmp_path, use_database)
    replies = tmp_path / "replies"
    replies.mkdir()
    state.configuration["filetalk"]["allowed-reply-paths"] = [str(replies)]
    target = replies / "answer.json"
    delivered = deliver_reply({"type": "file", "path": str(target)}, {"ok": True})
    assert delivered == target
    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    with pytest.raises(ValueError, match="invalid"):
        deliver_reply({"type": "file", "path": str(path("root") / "bad.json")}, {})


def test_reply_delivery_rejects_an_allowed_root_escape_through_a_symlink(tmp_path, use_database):
    prepared(tmp_path, use_database)
    replies = tmp_path / "replies"
    replies.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    escape = replies / "escape"

    try:
        escape.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks are unavailable: {error}")

    state.configuration["filetalk"]["allowed-reply-paths"] = [str(replies)]

    with pytest.raises(ValueError, match="invalid"):
        deliver_reply(
            {"type": "file", "path": str(escape / "answer.json")},
            {"ok": True},
        )


def test_reply_delivery_accepts_an_allowed_root_that_is_a_symlink(tmp_path, use_database):
    prepared(tmp_path, use_database)
    actual_replies = tmp_path / "actual-replies"
    actual_replies.mkdir()
    configured_replies = tmp_path / "configured-replies"

    try:
        configured_replies.symlink_to(actual_replies, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks are unavailable: {error}")

    state.configuration["filetalk"]["allowed-reply-paths"] = [str(configured_replies)]
    target = actual_replies / "answer.json"

    delivered = deliver_reply({"type": "file", "path": str(target)}, {"ok": True})

    assert delivered == target


def test_reply_delivery_rejects_the_database_root_even_when_it_is_configured(tmp_path, use_database):
    prepared(tmp_path, use_database)
    state.configuration["filetalk"]["allowed-reply-paths"] = [str(path("root"))]

    with pytest.raises(ValueError, match="invalid"):
        deliver_reply(
            {"type": "file", "path": str(path("root") / "answer.json")},
            {"ok": True},
        )
