import pytest

from subete.entities import write_entity
from subete.reads import execute_reads
from subete.searches import BASIC_ASPECT, execute_searches
from subete.setup import setup_database


def test_reads_distinguish_found_entities_and_missing_aspects(tmp_path, use_database):
    paths = prepared_paths(tmp_path, use_database)
    person = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    write_entity(paths, person, {"revision": 1, "aspects": {BASIC_ASPECT: {"title": "Alice"}}})

    result = execute_reads(paths, [{"entity": person, "aspects": [BASIC_ASPECT, "tag:example.net,2026:aspect/missing"]}])

    assert result == [{"entity": person, "status": "found", "revision": 1, "aspects": {BASIC_ASPECT: {"title": "Alice"}}}]


def test_searches_casefold_predicates_and_orders_ids(tmp_path, use_database):
    paths = prepared_paths(tmp_path, use_database)
    first = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    second = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    for entity_id, name in ((second, "Bob"), (first, "ALICE")):
        write_entity(paths, entity_id, {"revision": 1, "aspects": {BASIC_ASPECT: {"typehint": "Person", "name": name, "tags": ["Seattle", "friend"]}}})

    result = execute_searches(paths, [{"typehint": "person", "tags": ["seattle"], "name-contains": "a"}])

    assert result == [{"index": 0, "entities": [first]}]


def test_search_rejects_empty_and_unknown_predicates(tmp_path, use_database):
    paths = prepared_paths(tmp_path, use_database)
    with pytest.raises(ValueError, match="nonempty"):
        execute_searches(paths, [{}])
    with pytest.raises(ValueError, match="unsupported"):
        execute_searches(paths, [{"all": True}])


def prepared_paths(tmp_path, use_database):
    paths = use_database(tmp_path / "database")
    setup_database()
    return paths
