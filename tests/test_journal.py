from subete.entities import read_entity
from subete.journal import apply_pending, commit_pending, write_pending
from subete.paths import path
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
