import pytest

from subete.entities import (
    entity_filename,
    entity_id_from_filename,
    list_entity_ids,
    read_entity,
    write_entity,
)
from subete.paths import build_paths
from subete.setup import setup_database


def test_entity_filename_encodes_tag_uri_and_round_trips():
    entity_id = "tag:m1lattice.net,2026:example/a"

    filename = entity_filename(entity_id)

    assert filename == "tag%3Am1lattice.net%2C2026%3Aexample%2Fa.json"
    assert entity_id_from_filename(filename) == entity_id


def test_entity_store_writes_reads_and_orders_entities(tmp_path):
    paths = build_paths(tmp_path / "database")
    setup_database(paths["root"])
    alpha = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    beta = "tag:example.net,2026:entity/beta"
    write_entity(paths, beta, {"revision": 1, "aspects": {}})
    write_entity(paths, alpha, {"revision": 2, "aspects": {"tag:example.net,2026:aspect/a": {"x": 1}}})

    assert read_entity(paths, alpha) == {"revision": 2, "aspects": {"tag:example.net,2026:aspect/a": {"x": 1}}}
    assert list_entity_ids(paths) == [alpha, beta]
    assert read_entity(paths, "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb") is None


def test_entity_store_rejects_filename_record_mismatch(tmp_path):
    paths = build_paths(tmp_path / "database")
    setup_database(paths["root"])
    entity_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    path = paths["entities"] / entity_filename(entity_id)
    path.write_text('{"entity":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb","revision":1,"aspects":{}}', encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        read_entity(paths, entity_id)


def test_uppercase_uuid_is_canonicalized_at_storage_and_lookup(tmp_path):
    paths = build_paths(tmp_path / "database")
    setup_database(paths["root"])
    uppercase = "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"
    canonical = uppercase.lower()

    write_entity(paths, uppercase, {"revision": 1, "aspects": {"BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB": None}})

    assert (paths["entities"] / f"{canonical}.json").is_file()
    assert read_entity(paths, uppercase) == {"revision": 1, "aspects": {"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb": None}}


@pytest.mark.parametrize("value", ["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "{aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa}", "urn:uuid:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"])
def test_entity_store_rejects_alternate_uuid_spellings(value):
    with pytest.raises(ValueError):
        entity_filename(value)


def test_entity_store_preserves_every_json_aspect_value_kind(tmp_path):
    paths = build_paths(tmp_path / "database")
    setup_database(paths["root"])
    entity_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    values = {"tag:example.net,2026:aspect/object": {}, "tag:example.net,2026:aspect/array": [], "tag:example.net,2026:aspect/string": "text", "tag:example.net,2026:aspect/number": 4.5, "tag:example.net,2026:aspect/bool": True, "tag:example.net,2026:aspect/null": None}

    write_entity(paths, entity_id, {"revision": 1, "aspects": values})

    assert read_entity(paths, entity_id)["aspects"] == values
