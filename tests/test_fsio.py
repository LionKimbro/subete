import json

import pytest

from subete import fsio
from subete.fsio import write_json
from subete.paths import path
from subete.setup import setup_database


def test_read_json_accepts_a_named_territory_or_explicit_path(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()

    assert fsio.read_json("identity") == "complete"
    identity = fsio.read["data"]

    explicit_file = tmp_path / "external.json"
    explicit_file.write_text(json.dumps({"kind": "external"}), encoding="utf-8")

    assert fsio.read_json(path("identity")) == "complete"
    assert identity == fsio.read["data"]
    assert fsio.read_json(explicit_file) == "complete"
    assert fsio.read["data"] == {"kind": "external"}


def test_required_read_rejects_a_missing_named_territory(tmp_path, use_database):
    use_database(tmp_path / "database")

    with pytest.raises(ValueError, match="required JSON file is missing: identity.json"):
        fsio.read_json("identity", ["required"])

    assert fsio.read == {
        "data": None,
        "status": "missing",
        "path": path("identity"),
    }


def test_read_json_records_an_incomplete_document(tmp_path, use_database):
    use_database(tmp_path / "database")
    incomplete_file = tmp_path / "incomplete.json"
    incomplete_file.write_text('{"kind":', encoding="utf-8")

    assert fsio.read_json(incomplete_file) == "incomplete"
    assert fsio.read == {
        "data": None,
        "status": "incomplete",
        "path": incomplete_file,
    }


def test_read_json_records_an_unreadable_file(tmp_path, use_database, monkeypatch):
    use_database(tmp_path / "database")
    unreadable_file = tmp_path / "unreadable.json"
    unreadable_file.write_text("{}", encoding="utf-8")

    def reject_open(self, *args, **kwargs):
        raise PermissionError("permission denied")

    monkeypatch.setattr(fsio.Path, "open", reject_open)

    assert fsio.read_json(unreadable_file) == "unreadable"
    assert fsio.read == {
        "data": None,
        "status": "unreadable",
        "path": unreadable_file,
    }


def test_read_json_records_complete_json_null(tmp_path, use_database):
    use_database(tmp_path / "database")
    null_file = tmp_path / "null.json"
    null_file.write_text("null", encoding="utf-8")

    assert fsio.read_json(null_file) == "complete"
    assert fsio.read == {
        "data": None,
        "status": "complete",
        "path": null_file,
    }


def test_write_json_accepts_a_named_territory_or_explicit_path(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()

    write_json("configuration", {"kind": "configuration"})

    explicit_file = tmp_path / "external.json"
    write_json(explicit_file, {"kind": "external"})

    assert fsio.read_json("configuration") == "complete"
    assert fsio.read["data"] == {"kind": "configuration"}
    assert fsio.read_json(explicit_file) == "complete"
    assert fsio.read["data"] == {"kind": "external"}


def test_write_json_uses_a_temporary_file_inside_the_database_root(tmp_path, use_database, monkeypatch):
    use_database(tmp_path / "database")
    temporary_directories = []
    make_temporary_file = fsio.tempfile.mkstemp

    def record_temporary_file(*args, **kwargs):
        temporary_directories.append(kwargs["dir"])
        return make_temporary_file(*args, **kwargs)

    monkeypatch.setattr(fsio.tempfile, "mkstemp", record_temporary_file)

    write_json("configuration", {"kind": "configuration"})

    assert temporary_directories == [path("configuration").parent]


def test_write_json_does_not_create_a_temporary_file_outside_the_database_root(tmp_path, use_database, monkeypatch):
    use_database(tmp_path / "database")
    external_file = tmp_path / "guest" / "reply.json"

    def reject_temporary_file(*args, **kwargs):
        raise AssertionError("external write must not create a temporary file")

    monkeypatch.setattr(fsio.tempfile, "mkstemp", reject_temporary_file)

    write_json(external_file, {"kind": "reply"})

    assert json.loads(external_file.read_text(encoding="utf-8")) == {"kind": "reply"}


def test_failed_database_replacement_preserves_the_old_file_and_removes_its_temporary_file(tmp_path, use_database, monkeypatch):
    use_database(tmp_path / "database")
    destination = path("configuration")
    destination.parent.mkdir()
    destination.write_text('{"kind": "old"}\n', encoding="utf-8")

    def reject_replace(source, target):
        raise OSError("replacement failed")

    monkeypatch.setattr(fsio.os, "replace", reject_replace)

    with pytest.raises(OSError, match="replacement failed"):
        write_json(destination, {"kind": "new"})

    assert json.loads(destination.read_text(encoding="utf-8")) == {"kind": "old"}
    assert list(destination.parent.glob(f".{destination.name}.*.tmp")) == []
