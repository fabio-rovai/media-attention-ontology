"""Resolve EIDR identifiers through the public EIDR resolution service.

Only structural facets are retained (StructuralType, ReferentType, ResourceName,
ReferentType parentage). Bulk EIDR metadata is not redistributed.
"""
import json, os, re, sys, time, urllib.request, urllib.error
from xml.etree import ElementTree as ET

NS = {"e": "http://www.eidr.org/schema"}
CACHE = "eidr_resolved.jsonl"
UA = "MediaAttentionOntology/0.1 (https://github.com/fabio-rovai; fabio@thetesseractacademy.com)"


def load_cache():
    d = {}
    if os.path.exists(CACHE):
        for line in open(CACHE):
            try:
                r = json.loads(line)
                d[r["id"]] = r
            except Exception:
                pass
    return d


def fetch(eidr, retries=3):
    url = "https://resolve.eidr.org/EIDR/object/" + urllib.parse.quote(eidr, safe="") + "/?type=Full"
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace"), r.status
        except urllib.error.HTTPError as e:
            if e.code in (404, 403):
                return None, e.code
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return None, -1


def parse_xml(xml):
    root = ET.fromstring(xml)
    def txt(tag):
        el = root.find(f".//e:{tag}", NS)
        return el.text if el is not None else None
    rec = {
        "structural_type": txt("StructuralType"),
        "referent_type": txt("ReferentType"),
        "mode": txt("Mode"),
        "name": txt("ResourceName"),
        "status": txt("Status"),
    }
    # parent linkage tells us where in the hierarchy the record sits
    par = root.find(".//e:Parent", NS)
    rec["parent"] = par.text if par is not None else None
    rel = root.find(".//e:RelationshipType", NS)
    rec["relationship"] = rel.text if rel is not None else None
    return rec


import urllib.parse  # noqa: E402

def resolve_many(ids, sleep=0.4):
    cache = load_cache()
    todo = [i for i in ids if i not in cache]
    print(f"to resolve: {len(todo):,} (cached: {len(ids)-len(todo):,})", file=sys.stderr)
    with open(CACHE, "a") as f:
        for n, eidr in enumerate(todo, 1):
            xml, status = fetch(eidr)
            rec = {"id": eidr, "http": status}
            if xml:
                try:
                    rec.update(parse_xml(xml))
                except Exception as e:
                    rec["parse_error"] = str(e)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            cache[eidr] = rec
            if n % 100 == 0:
                print(f"  {n:,}/{len(todo):,}", file=sys.stderr, flush=True)
            time.sleep(sleep)
    return cache
