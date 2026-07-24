import pytest

from subete import entities
from subete.entities import (
    apply_entity_transitions,
    entity_filename,
    list_ids,
    read_entity,
    read_aspects,
)
from subete.paths import path
from subete.setup import setup_database


def test_entity_filename_encodes_tag_uri_and_round_trips():
    entity_id = "tag:m1lattice.net,2026:example/a"

    filename = entity_filename(entity_id)

    assert filename == "tag%3Am1lattice.net%2C2026%3Aexample%2Fa.json"
    assert entities._entity_id_from_filename(filename) == entity_id


def test_entity_store_writes_reads_and_orders_entities(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()
    alpha = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    beta = "tag:example.net,2026:entity/beta"
    entities._write_complete_entity_state(beta, {"revision": 1, "aspects": {}})
    entities._write_complete_entity_state(alpha, {"revision": 2, "aspects": {"tag:example.net,2026:aspect/a": {"x": 1}}})

    assert read_entity(alpha) == {"revision": 2, "aspects": {"tag:example.net,2026:aspect/a": {"x": 1}}}
    assert list_ids() == [alpha, beta]
    assert read_entity("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb") is None


def test_entity_store_rejects_filename_record_mismatch(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()
    entity_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    entity_file = path("entities") / entity_filename(entity_id)
    entity_file.write_text('{"entity":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb","revision":1,"aspects":{}}', encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        read_entity(entity_id)


def test_uppercase_uuid_is_canonicalized_at_storage_and_lookup(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()
    uppercase = "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"
    canonical = uppercase.lower()

    entities._write_complete_entity_state(uppercase, {"revision": 1, "aspects": {"BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB": None}})

    assert (path("entities") / f"{canonical}.json").is_file()
    assert read_entity(uppercase) == {"revision": 1, "aspects": {"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb": None}}


@pytest.mark.parametrize("value", ["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "{aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa}", "urn:uuid:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"])
def test_entity_store_rejects_alternate_uuid_spellings(value):
    with pytest.raises(ValueError):
        entity_filename(value)


def test_entity_store_preserves_every_json_aspect_value_kind(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()
    entity_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    values = {"tag:example.net,2026:aspect/object": {}, "tag:example.net,2026:aspect/array": [], "tag:example.net,2026:aspect/string": "text", "tag:example.net,2026:aspect/number": 4.5, "tag:example.net,2026:aspect/bool": True, "tag:example.net,2026:aspect/null": None}

    entities._write_complete_entity_state(entity_id, {"revision": 1, "aspects": values})

    assert read_entity(entity_id)["aspects"] == values


def test_selected_aspect_reads_preserve_present_null_and_omit_absent_aspects(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()
    entity_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    null_aspect = "tag:example.net,2026:aspect/null"
    missing_aspect = "tag:example.net,2026:aspect/missing"
    entities._write_complete_entity_state(entity_id, {"revision": 1, "aspects": {null_aspect: None}})

    selected = read_aspects(entity_id, [null_aspect, missing_aspect])

    assert selected == {"revision": 1, "aspects": {null_aspect: None}}


def test_empty_aspect_entity_remains_present_after_complete_replacement(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()
    entity_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    entities._write_complete_entity_state(
        entity_id,
        {"revision": 1, "aspects": {"tag:example.net,2026:aspect/basic": {}}},
    )

    entities._write_complete_entity_state(entity_id, {"revision": 2, "aspects": {}})

    assert read_entity(entity_id) == {"revision": 2, "aspects": {}}
    assert entity_id in list_ids()


def test_delete_entity_removes_the_authoritative_file(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()
    entity_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    entities._write_complete_entity_state(entity_id, {"revision": 1, "aspects": {}})

    entities._delete_entity_file(entity_id)

    assert read_entity(entity_id) is None
    assert not entities._entity_path(entity_id).exists()


def test_entity_file_rejects_unknown_fields_and_invalid_revisions(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()
    entity_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    entity_file = path("entities") / entity_filename(entity_id)
    entity_file.write_text(
        '{"entity":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","revision":0,"aspects":{},"extra":true}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing or unknown"):
        read_entity(entity_id)


def test_entity_transition_distinguishes_entity_absence_from_a_null_aspect(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()
    entity_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    after = {
        "revision": 1,
        "aspects": {"tag:example.net,2026:aspect/null": None},
    }

    apply_entity_transitions({entity_id: {"before": None, "after": after}})
    apply_entity_transitions({entity_id: {"before": None, "after": after}})

    assert read_entity(entity_id) == after

    apply_entity_transitions({entity_id: {"before": after, "after": None}})

    assert read_entity(entity_id) is None


def test_entity_transition_comparison_is_exact_about_json_value_types(tmp_path, use_database):
    use_database(tmp_path / "database")
    setup_database()
    entity_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    actual = {"revision": 1, "aspects": {"tag:example.net,2026:aspect/value": True}}
    mismatched_before = {"revision": 1, "aspects": {"tag:example.net,2026:aspect/value": 1}}
    after = {"revision": 2, "aspects": {"tag:example.net,2026:aspect/value": False}}
    entities._write_complete_entity_state(entity_id, actual)

    with pytest.raises(ValueError, match="before-state"):
        apply_entity_transitions({entity_id: {"before": mismatched_before, "after": after}})


def test_entity_transitions_apply_in_decoded_entity_id_order(monkeypatch):
    applied = []

    def record(entity_id, transition):
        applied.append(entity_id)

    monkeypatch.setattr(entities, "_apply_entity_transition", record)

    apply_entity_transitions(
        {
            "tag:example.net,2026:entity/beta": {"before": None, "after": None},
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {"before": None, "after": None},
        }
    )

    assert applied == [
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "tag:example.net,2026:entity/beta",
    ]
