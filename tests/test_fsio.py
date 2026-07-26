import json

import pytest

from subete import fsio
from subete.fsio import write_json
from subete.paths import path
from subete.setup import setup_database


def test_read_file_accepts_a_named_territory_or_explicit_path(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()

    assert fsio.read_file("identity", ["json", "stat"]) == "complete"
    identity = fsio.read["value"]
    assert fsio.read["source"] == path("identity")
    assert fsio.read["raw"]
    assert fsio.read["stat"]["size"] == path("identity").stat().st_size

    explicit_file = tmp_path / "external.json"
    explicit_file.write_text(json.dumps({"kind": "external"}), encoding="utf-8")

    assert fsio.read_file(path("identity"), ["json"]) == "complete"
    assert identity == fsio.read["value"]
    assert fsio.read_file(explicit_file, ["json"]) == "complete"
    assert fsio.read["value"] == {"kind": "external"}


def test_required_read_rejects_a_missing_named_territory(tmp_path, use_database):
    use_database(tmp_path / "database")

    with pytest.raises(ValueError, match="required file read failed: missing:"):
        fsio.read_file("identity", ["required", "json"])

    assert fsio.read == {
        "source": path("identity"),
        "status": "missing",
        "stat": None,
        "raw": None,
        "value": None,
        "error": "missing",
    }


def test_read_file_records_an_invalid_document(tmp_path, use_database):
    use_database(tmp_path / "database")
    incomplete_file = tmp_path / "incomplete.json"
    incomplete_file.write_text('{"kind":', encoding="utf-8")

    assert fsio.read_file(incomplete_file, ["json"]) == "invalid"
    assert fsio.read == {
        "status": "invalid",
        "source": incomplete_file,
        "stat": None,
        "raw": b'{"kind":',
        "value": None,
        "error": "invalid-json",
    }


def test_read_file_records_an_unreadable_file(tmp_path, use_database, monkeypatch):
    use_database(tmp_path / "database")
    unreadable_file = tmp_path / "unreadable.json"
    unreadable_file.write_text("{}", encoding="utf-8")

    def reject_open(self, *args, **kwargs):
        raise PermissionError("permission denied")

    monkeypatch.setattr(fsio.Path, "open", reject_open)

    assert fsio.read_file(unreadable_file, ["json"]) == "unreadable"
    assert fsio.read == {
        "source": unreadable_file,
        "status": "unreadable",
        "stat": None,
        "raw": None,
        "value": None,
        "error": "unreadable",
    }


def test_read_file_records_complete_json_null(tmp_path, use_database):
    use_database(tmp_path / "database")
    null_file = tmp_path / "null.json"
    null_file.write_text("null", encoding="utf-8")

    assert fsio.read_file(null_file, ["json"]) == "complete"
    assert fsio.read == {
        "source": null_file,
        "status": "complete",
        "stat": None,
        "raw": b"null",
        "value": None,
        "error": None,
    }


def test_write_json_accepts_a_named_territory_or_explicit_path(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()

    write_json("configuration", {"kind": "configuration"})

    explicit_file = tmp_path / "external.json"
    write_json(explicit_file, {"kind": "external"})

    assert fsio.read_file("configuration", ["json"]) == "complete"
    assert fsio.read["value"] == {"kind": "configuration"}
    assert fsio.read_file(explicit_file, ["json"]) == "complete"
    assert fsio.read["value"] == {"kind": "external"}


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
