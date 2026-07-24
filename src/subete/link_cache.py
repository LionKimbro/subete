"""Rebuildable Version 1 link-cache helpers."""
from .entities import entity_filename, list_entity_ids, read_entity
from .fsio import write_json_replace
from .setup import utc_now

LINK_ASPECT = "tag:m1lattice.net,2026:aspect/link"

def rebuild(paths, database_id, generation):
    outgoing = {}; incoming = {}
    for link_id in list_entity_ids(paths):
        entity = read_entity(paths, link_id); link = entity["aspects"].get(LINK_ASPECT)
        if not isinstance(link, dict) or not isinstance(link.get("from"), str) or not isinstance(link.get("to"), str): continue
        outgoing.setdefault(link["from"], set()).add(link_id); incoming.setdefault(link["to"], set()).add(link_id)
    for direction, entries in (("outgoing", outgoing), ("incoming", incoming)):
        directory = paths["link_cache"] / direction; directory.mkdir(exist_ok=True)
        for endpoint, links in entries.items():
            write_json_replace(directory / entity_filename(endpoint), {"link-cache-entry-format-version":1,"database-id":database_id,"generation":generation,"entity":endpoint,"direction":direction,"links":sorted(links)})
    publish_current(paths, database_id, generation)

def publish_updating(paths, database_id, generation, target):
    write_json_replace(paths["link_cache"] / "generation.json", {"link-cache-format-version":1,"database-id":database_id,"generation":generation,"target-generation":target,"updated":utc_now(),"state":"updating"})

def publish_current(paths, database_id, generation):
    write_json_replace(paths["link_cache"] / "generation.json", {"link-cache-format-version":1,"database-id":database_id,"generation":generation,"updated":utc_now(),"state":"current"})
