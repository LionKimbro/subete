from subete.entities import read_entity
from subete.journal import apply_pending, commit_pending, write_pending
from subete.setup import setup_database
from subete.requests import execute_request

def test_pending_journal_authorizes_idempotent_creation_then_commit(tmp_path, use_database):
    paths = use_database(tmp_path / "db"); setup_database()
    identity = __import__('json').loads(paths["identity"].read_text())["database-id"]
    entity = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"; request = {"request-id":"11111111-1111-4111-8111-111111111111"}
    pending = write_pending(paths, identity, request, {entity:{"before":None,"after":{"revision":1,"aspects":{}}}})
    assert read_entity(paths, entity) is None
    apply_pending(paths, pending); apply_pending(paths, pending)
    assert read_entity(paths, entity)["revision"] == 1
    commit_pending(paths, pending, identity)
    assert (paths["journal_committed"] / pending.name).is_file()

def test_transaction_request_journals_before_publishing_generation(tmp_path, use_database):
    paths = use_database(tmp_path / "db"); setup_database()
    identity = __import__('json').loads(paths["identity"].read_text())["database-id"]
    entity = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    message = {"request-id":"22222222-2222-4222-8222-222222222222","request-type":"transaction","reply":{},"request":{"operations":[{"operation":"create-entity","entity":entity,"aspects":{}}]}}
    response = execute_request(paths, identity, message)
    assert response["generation"] == 1
    assert read_entity(paths, entity)["revision"] == 1
