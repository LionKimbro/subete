from subete.entities import read_entity
import json

import pytest

from subete.journal import (
    apply_pending,
    commit_pending,
    journal_filename,
    parse_journal_filename,
    read_validated_journal_entry,
    write_pending,
)
from subete.paths import path
from subete.recovery import recover_pending
from subete.setup import setup_database
from subete.requests import execute_request

def test_pending_journal_authorizes_idempotent_creation_then_commit(tmp_path, use_database):
    use_database(tmp_path / "db"); setup_database()
    identity = __import__('json').loads(path("identity").read_text())["database-id"]
    entity = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"; request = {"request-id":"11111111-1111-4111-8111-111111111111"}
    pending = write_pending(identity, request, {entity:{"before":None,"after":{"revision":1,"aspects":{}}}})
    assert read_entity(entity) is None
    apply_pending(pending); apply_pending(pending)
    assert read_entity(entity)["revision"] == 1
    commit_pending(pending, identity)
    assert (path("journal_committed") / pending.name).is_file()

def test_transaction_request_journals_before_publishing_generation(tmp_path, use_database):
    use_database(tmp_path / "db"); setup_database()
    identity = __import__('json').loads(path("identity").read_text())["database-id"]
    entity = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    message = {"request-id":"22222222-2222-4222-8222-222222222222","request-type":"transaction","reply":{},"request":{"operations":[{"operation":"create-entity","entity":entity,"aspects":{}}]}}
    response = execute_request(identity, message)
    assert response["generation"] == 1
    assert read_entity(entity)["revision"] == 1


def test_journal_filename_round_trips_its_sequence_and_request_id():
    request_id = "11111111-1111-4111-8111-111111111111"

    filename = journal_filename(42, request_id)

    assert filename == "00000000000000000042__11111111-1111-4111-8111-111111111111.json"
    assert parse_journal_filename(filename) == {
        "sequence": 42,
        "request-id": request_id,
    }


def test_recovery_rejects_a_journal_filename_that_disagrees_with_its_entry(tmp_path, use_database):
    use_database(tmp_path / "db")
    setup_database()
    database_id = json.loads(path("identity").read_text())["database-id"]
    request = {"request-id": "11111111-1111-4111-8111-111111111111"}
    entity_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    pending = write_pending(
        database_id,
        request,
        {entity_id: {"before": None, "after": {"revision": 1, "aspects": {}}}},
    )
    entry = json.loads(pending.read_text())
    entry["sequence"] = 2
    pending.write_text(json.dumps(entry), encoding="utf-8")

    with pytest.raises(ValueError, match="filename sequence"):
        recover_pending(database_id)


def test_journal_read_rejects_a_noncanonical_entity_id(tmp_path, use_database):
    use_database(tmp_path / "db")
    setup_database()
    database_id = json.loads(path("identity").read_text())["database-id"]
    request = {"request-id": "11111111-1111-4111-8111-111111111111"}
    entity_id = "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"
    pending = write_pending(
        database_id,
        request,
        {entity_id: {"before": None, "after": {"revision": 1, "aspects": {}}}},
    )

    with pytest.raises(ValueError, match="canonical lowercase"):
        read_validated_journal_entry(pending)


def test_journal_read_rejects_a_noncanonical_aspect_id(tmp_path, use_database):
    use_database(tmp_path / "db")
    setup_database()
    database_id = json.loads(path("identity").read_text())["database-id"]
    request = {"request-id": "11111111-1111-4111-8111-111111111111"}
    entity_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    aspect_id = "BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB"
    pending = write_pending(
        database_id,
        request,
        {
            entity_id: {
                "before": None,
                "after": {"revision": 1, "aspects": {aspect_id: {"value": True}}},
            }
        },
    )

    with pytest.raises(ValueError, match="journal aspect IDs"):
        read_validated_journal_entry(pending)


def test_journal_stores_canonical_entity_and_aspect_ids_from_a_transaction_request(tmp_path, use_database):
    use_database(tmp_path / "db")
    setup_database()
    database_id = json.loads(path("identity").read_text())["database-id"]
    entity_id = "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"
    aspect_id = "BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB"
    message = {
        "request-id": "22222222-2222-4222-8222-222222222222",
        "request-type": "transaction",
        "reply": {},
        "request": {
            "operations": [
                {
                    "operation": "create-entity",
                    "entity": entity_id,
                    "aspects": {aspect_id: {"value": True}},
                }
            ]
        },
    }

    execute_request(database_id, message)
    journal_file = next(path("journal_committed").glob("*.json"))
    entry = json.loads(journal_file.read_text())
    operation = entry["transaction-request"]["request"]["operations"][0]

    assert list(entry["entities"]) == [entity_id.lower()]
    assert operation["entity"] == entity_id.lower()
    assert list(operation["aspects"]) == [aspect_id.lower()]
