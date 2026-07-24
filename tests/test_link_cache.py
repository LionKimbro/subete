from subete.entities import write_entity
from subete.link_cache import LINK_ASPECT, rebuild
from subete.paths import build_paths
from subete.setup import setup_database

def test_cache_rebuild_indexes_link_in_both_directions(tmp_path):
    paths=build_paths(tmp_path/'db'); setup_database(paths['root'])
    identity=__import__('json').loads(paths['identity'].read_text())['database-id']
    a='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'; b='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'; link='cccccccc-cccc-4ccc-8ccc-cccccccccccc'
    for item in (a,b): write_entity(paths,item,{'revision':1,'aspects':{}})
    write_entity(paths,link,{'revision':1,'aspects':{LINK_ASPECT:{'from':a,'to':b}}})
    rebuild(paths,identity,0)
    assert link in __import__('json').loads(next((paths['link_cache']/'outgoing').glob('*.json')).read_text())['links']
