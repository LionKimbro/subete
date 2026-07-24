import json

import pytest

from subete.fsio import read_json, write_json
from subete.paths import path
from subete.setup import setup_database


def test_read_json_accepts_a_named_territory_or_explicit_path(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()

    identity = read_json("identity")

    explicit_file = tmp_path / "external.json"
    explicit_file.write_text(json.dumps({"kind": "external"}), encoding="utf-8")

    assert identity == read_json(path("identity"))
    assert read_json(explicit_file) == {"kind": "external"}


def test_read_json_verify_file_rejects_a_missing_named_territory(tmp_path, use_database):
    use_database(tmp_path / "database")

    with pytest.raises(ValueError, match="existing database is missing identity.json"):
        read_json("identity", ["verify-file"])


def test_write_json_accepts_a_named_territory_or_explicit_path(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()

    write_json("configuration", {"kind": "configuration"})

    explicit_file = tmp_path / "external.json"
    write_json(explicit_file, {"kind": "external"})

    assert read_json("configuration") == {"kind": "configuration"}
    assert read_json(explicit_file) == {"kind": "external"}
