from subete.entities import write_entity
from subete.link_cache import LINK_ASPECT, rebuild
from subete.paths import path
from subete.setup import setup_database

def test_cache_rebuild_indexes_link_in_both_directions(tmp_path, use_database):
    use_database(tmp_path/'db'); setup_database()
    identity=__import__('json').loads(path("identity").read_text())['database-id']
    a='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'; b='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'; link='cccccccc-cccc-4ccc-8ccc-cccccccccccc'
    for item in (a,b): write_entity(item,{'revision':1,'aspects':{}})
    write_entity(link,{'revision':1,'aspects':{LINK_ASPECT:{'from':a,'to':b}}})
    rebuild(identity,0)
    assert link in __import__('json').loads(next((path("link_cache")/'outgoing').glob('*.json')).read_text())['links']
