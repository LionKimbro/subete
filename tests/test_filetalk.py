import json

import pytest

from subete import filetalk, request, state
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
    filetalk.system_init_filetalk()
    state.update_now()
    assert not filetalk.discover_next_message()
    now["value"] = 21
    state.update_now()
    assert filetalk.list_stale_unreadable_messages() == [candidate]
    candidate.write_text('{"request-id":"ok"}', encoding="utf-8")
    now["value"] = 22
    state.update_now()
    assert filetalk.discover_next_message()
    assert filetalk.selected["name"] == "request.json"
    assert filetalk.selected["message"] == {"request-id": "ok"}
    request.possess_current_message()
    request.claim_current_message()
    assert request.current["name"] == "request.json"
    assert request.current["path"].parent == path("claimed")
    assert request.current["location"] == "claimed"


def test_terminal_move_keeps_the_request_name_as_its_durable_identity(tmp_path, use_database):
    prepared(tmp_path, use_database)
    request_file = path("inbox") / "one.json"
    request_file.write_text('{"request-id":"one"}', encoding="utf-8")
    state.update_now()
    assert filetalk.discover_next_message()
    request.possess_current_message()
    request.claim_current_message()

    request.set_response({"outcome": "ok"})
    assert request.current["response"] == {"outcome": "ok"}
    request.record_successful_completion()

    archived_request = path("completed") / "one.json" / "request.json"
    archived_record = path("completed") / "one.json" / "record.json"
    assert archived_request.read_text(encoding="utf-8") == '{"request-id":"one"}'
    assert json.loads(archived_record.read_text(encoding="utf-8")) == {
        "status": "success",
        "response": {"outcome": "ok"},
    }
    assert request.current == {
        "name": None,
        "path": None,
        "message": None,
        "location": None,
        "response": None,
        "error": None,
    }


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
    reply = {"type": "file", "path": str(target)}
    request.current["message"] = {"reply": reply}
    request.set_response({"ok": True})
    delivered = filetalk.deliver_reply_back_to_sender()
    assert delivered == target
    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    with pytest.raises(ValueError, match="invalid"):
        reply = {"type": "file", "path": str(path("root") / "bad.json")}
        request.current["message"] = {"reply": reply}
        request.set_response({})
        filetalk.deliver_reply_back_to_sender()


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
        reply = {"type": "file", "path": str(escape / "answer.json")}
        request.current["message"] = {"reply": reply}
        request.set_response({"ok": True})
        filetalk.deliver_reply_back_to_sender()


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

    reply = {"type": "file", "path": str(target)}
    request.current["message"] = {"reply": reply}
    request.set_response({"ok": True})
    delivered = filetalk.deliver_reply_back_to_sender()

    assert delivered == target


def test_reply_delivery_rejects_the_database_root_even_when_it_is_configured(tmp_path, use_database):
    prepared(tmp_path, use_database)
    state.configuration["filetalk"]["allowed-reply-paths"] = [str(path("root"))]

    with pytest.raises(ValueError, match="invalid"):
        reply = {"type": "file", "path": str(path("root") / "answer.json")}
        request.current["message"] = {"reply": reply}
        request.set_response({"ok": True})
        filetalk.deliver_reply_back_to_sender()
