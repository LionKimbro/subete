import json

import pytest

from subete import filetalk, state
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
    filetalk.reset_filetalk_observations()
    state.update_now()
    assert not filetalk.discover_next_message()
    now["value"] = 21
    state.update_now()
    assert filetalk.list_stale_unreadable_messages() == [candidate]
    candidate.write_text('{"request-id":"ok"}', encoding="utf-8")
    now["value"] = 22
    state.update_now()
    assert filetalk.discover_next_message()
    assert filetalk.current["message"] == {"request-id": "ok"}
    filetalk.claim_message()
    assert filetalk.current["path"].parent == path("claimed")
    assert filetalk.current["location"] == "claimed"


def test_discovery_does_not_claim_complete_non_object(tmp_path, use_database, monkeypatch):
    prepared(tmp_path, use_database)
    monkeypatch.setattr(state.time, "time", lambda: 1)
    (path("inbox") / "array.json").write_text("[]", encoding="utf-8")
    state.update_now()
    assert not filetalk.discover_next_message()


def test_reply_delivery_requires_configured_external_absolute_path(tmp_path, use_database):
    prepared(tmp_path, use_database)
    replies = tmp_path / "replies"
    replies.mkdir()
    state.configuration["filetalk"]["allowed-reply-paths"] = [str(replies)]
    target = replies / "answer.json"
    filetalk.current["message"] = {"reply": {"type": "file", "path": str(target)}}
    delivered = filetalk.deliver_reply({"ok": True})
    assert delivered == target
    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    with pytest.raises(ValueError, match="invalid"):
        filetalk.current["message"] = {"reply": {"type": "file", "path": str(path("root") / "bad.json")}}
        filetalk.deliver_reply({})


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
        filetalk.current["message"] = {"reply": {"type": "file", "path": str(escape / "answer.json")}}
        filetalk.deliver_reply({"ok": True})


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

    filetalk.current["message"] = {"reply": {"type": "file", "path": str(target)}}
    delivered = filetalk.deliver_reply({"ok": True})

    assert delivered == target


def test_reply_delivery_rejects_the_database_root_even_when_it_is_configured(tmp_path, use_database):
    prepared(tmp_path, use_database)
    state.configuration["filetalk"]["allowed-reply-paths"] = [str(path("root"))]

    with pytest.raises(ValueError, match="invalid"):
        filetalk.current["message"] = {"reply": {"type": "file", "path": str(path("root") / "answer.json")}}
        filetalk.deliver_reply({"ok": True})
