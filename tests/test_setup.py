import json

import pytest

from subete import init
from subete.paths import path, paths, required_directories
from subete.setup import setup_database
from subete.state import configuration, g


def test_setup_creates_complete_generation_zero_database(tmp_path, use_database):
    dbroot = tmp_path / "database"

    use_database(dbroot)
    result = setup_database()

    assert result == "created"
    assert all(path.is_dir() for path in required_directories())
    identity = load(path("identity"))
    configuration_record = load(path("configuration"))
    generation = load(path("generation"))
    assert identity["database-id"] == g["database-id"]
    assert configuration == configuration_record
    assert configuration_record["configuration-version"] == 1
    assert configuration_record["filetalk"]["allowed-reply-paths"] == []
    assert generation["database-id"] == g["database-id"]
    assert generation["generation"] == 0
    assert generation["journal-sequence"] == 0


def test_path_declarations_describe_the_current_database_territory(tmp_path, use_database):
    dbroot = tmp_path / "database"

    use_database(dbroot)

    assert paths["root"] == {
        "path": dbroot.resolve(),
        "kind": "directory",
        "required": True,
    }
    assert paths["identity"] == {
        "path": dbroot / "identity.json",
        "kind": "file",
        "required": True,
    }
    assert path("entities") == dbroot / "entities"


def test_setup_validates_instead_of_replacing_existing_identity(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    first = setup_database()
    first_database_id = g["database-id"]

    second = setup_database()

    assert first == "created"
    assert second == "existing"
    assert g["database-id"] == first_database_id


def test_system_initialization_loads_an_existing_database_id(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    created = setup_database()

    g["database-id"] = None
    init.init_system()

    assert created == "created"
    assert g["database-id"] == load(path("identity"))["database-id"]


def test_existing_database_requires_a_complete_configuration_file(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    path("configuration").unlink()

    with pytest.raises(ValueError, match="missing configuration.json"):
        init.init_system()


def test_existing_database_rejects_incomplete_configuration(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    path("configuration").write_text('{"configuration-version": 1}', encoding="utf-8")

    with pytest.raises(ValueError, match="missing or unknown"):
        init.init_system()


def test_setup_refuses_partial_root_metadata(tmp_path, use_database):
    dbroot = tmp_path / "database"
    dbroot.mkdir()
    (dbroot / "generation.json").write_text("{}", encoding="utf-8")
    use_database(dbroot)

    with pytest.raises(ValueError, match="no identity"):
        setup_database()


def test_setup_rejects_mismatched_existing_generation_identity(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    generation_path = dbroot / "generation.json"
    generation = load(generation_path)
    generation["database-id"] = "00000000-0000-4000-8000-000000000000"
    generation_path.write_text(json.dumps(generation), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        setup_database()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))
