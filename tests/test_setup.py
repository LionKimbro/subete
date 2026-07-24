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

    with pytest.raises(ValueError, match="missing: configuration.json"):
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


@pytest.mark.parametrize(
    "database_id",
    [
        "8B797903-EDCE-4B2A-96EB-B1C3845C6455",
        "8b797903edce4b2a96ebb1c3845c6455",
        "{8b797903-edce-4b2a-96eb-b1c3845c6455}",
    ],
)
def test_setup_requires_canonical_database_uuid(tmp_path, use_database, database_id):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    identity = load(path("identity"))
    identity["database-id"] = database_id
    path("identity").write_text(json.dumps(identity), encoding="utf-8")

    with pytest.raises(ValueError, match="UUID string"):
        setup_database()


def test_setup_requires_real_utc_z_metadata_timestamps(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    identity = load(path("identity"))
    identity["created"] = "2026-02-30T12:00:00Z"
    path("identity").write_text(json.dumps(identity), encoding="utf-8")

    with pytest.raises(ValueError, match="UTC Z timestamp"):
        setup_database()


def test_setup_rejects_unknown_identity_metadata(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    identity = load(path("identity"))
    identity["unrecognized"] = True
    path("identity").write_text(json.dumps(identity), encoding="utf-8")

    with pytest.raises(ValueError, match="missing or unknown"):
        setup_database()


def test_setup_accepts_documented_optional_identity_metadata(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    identity = load(path("identity"))
    identity["name"] = "lion_subete"
    identity["title"] = "Lion's Subete"
    save(path("identity"), identity)

    assert setup_database() == "existing"


def test_setup_rejects_an_invalid_identity_name(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    identity = load(path("identity"))
    identity["name"] = "Lion Subete"
    save(path("identity"), identity)

    with pytest.raises(ValueError, match="lowercase identifier"):
        setup_database()


def test_setup_rejects_a_non_string_identity_title(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    identity = load(path("identity"))
    identity["title"] = 1
    save(path("identity"), identity)

    with pytest.raises(ValueError, match="title must be a string"):
        setup_database()


def test_setup_rejects_missing_or_unknown_generation_fields(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    generation = load(path("generation"))
    generation.pop("updated")
    generation["unrecognized"] = True
    save(path("generation"), generation)

    with pytest.raises(ValueError, match="missing or unknown"):
        setup_database()


def test_setup_rejects_an_invalid_generation_number(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    generation = load(path("generation"))
    generation["generation"] = -1
    save(path("generation"), generation)

    with pytest.raises(ValueError, match="non-negative integer"):
        setup_database()


def test_setup_rejects_invalid_polling_configuration(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    configuration_record = load(path("configuration"))
    configuration_record["polling"]["stale-inbox-file-action"] = "guess"
    save(path("configuration"), configuration_record)

    with pytest.raises(ValueError, match="stale-inbox-file-action"):
        init.init_system()


def test_setup_rejects_relative_filetalk_reply_paths(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    configuration_record = load(path("configuration"))
    configuration_record["filetalk"]["allowed-reply-paths"] = ["relative"]
    save(path("configuration"), configuration_record)

    with pytest.raises(ValueError, match="absolute paths"):
        init.init_system()


def test_setup_rejects_incomplete_durable_configuration_json(tmp_path, use_database):
    dbroot = tmp_path / "database"
    use_database(dbroot)
    setup_database()
    path("configuration").write_text('{"configuration-version":', encoding="utf-8")

    with pytest.raises(ValueError, match="incomplete: configuration.json"):
        init.init_system()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
