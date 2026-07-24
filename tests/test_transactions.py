from subete.entities import write_entity
from subete.setup import setup_database
from subete.transactions import plan_transaction

def test_planner_changes_two_aspects_once_and_keeps_store_unchanged(tmp_path, use_database):
    use_database(tmp_path / "db"); setup_database()
    entity = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    write_entity(entity, {"revision": 1, "aspects": {"tag:example.net,2026:aspect/a": 1}})
    plan = plan_transaction([{"operation":"set-aspect","entity":entity,"expected-revision":1,"aspect":"tag:example.net,2026:aspect/a","value":2},{"operation":"set-aspect","entity":entity,"expected-revision":1,"aspect":"tag:example.net,2026:aspect/b","value":None}])
    assert plan[entity]["before"]["revision"] == 1
    assert plan[entity]["after"] == {"revision":2,"aspects":{"tag:example.net,2026:aspect/a":2,"tag:example.net,2026:aspect/b":None}}
