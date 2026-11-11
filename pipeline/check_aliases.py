"""Find works whose several EIDR identifiers are one record and its retired alias.

EIDR's public resolver follows a retired identifier to the record it was merged into
and returns that record without saying so. Comparing the ID returned with the ID
asked for is the only way to see it. Only the returned identifier is kept.

    python pipeline/check_aliases.py data
"""
import collections
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from xml.etree import ElementTree as ET

NS = {"e": "http://www.eidr.org/schema"}
UA = "MediaAttentionOntology/0.1 (https://github.com/fabio-rovai/media-attention-ontology)"


def returned_id(eidr, retries=3):
    url = "https://resolve.eidr.org/EIDR/object/" + urllib.parse.quote(eidr, safe="") + "/?type=Full"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                el = ET.fromstring(r.read()).find(".//e:ID", NS)
                return el.text.strip() if el is not None else None
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return None
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def main(data_dir):
    by_item = collections.defaultdict(set)
    with open(os.path.join(data_dir, "wikidata_eidr.jsonl")) as fh:
        for line in fh:
            r = json.loads(line)
            by_item[r["qid"]].add(r["eidr"])
    multi = {q: sorted(ids) for q, ids in by_item.items() if len(ids) > 1}
    wanted = sorted({i for ids in multi.values() for i in ids})

    cache_path = os.path.join(data_dir, "eidr_returned.jsonl")
    seen = {}
    if os.path.exists(cache_path):
        with open(cache_path) as fh:
            for line in fh:
                r = json.loads(line)
                seen[r["id"]] = r["returned"]
    todo = [i for i in wanted if seen.get(i) is None]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, ret in zip(todo, pool.map(returned_id, todo)):
            seen[i] = ret
    with open(cache_path, "w") as fh:
        for i in wanted:
            fh.write(json.dumps({"id": i, "returned": seen.get(i)}) + "\n")

    unresolved = [i for i in wanted if seen.get(i) is None]
    redirected = [i for i in wanted if seen.get(i) and seen[i] != i]
    one_record = [q for q, ids in multi.items()
                  if all(seen.get(i) for i in ids) and len({seen[i] for i in ids}) == 1]
    summary = {
        "works_with_more_than_one_eidr": len(multi),
        "identifiers_checked": len(wanted),
        "identifiers_unresolved": len(unresolved),
        "identifiers_redirected_to_another_record": len(redirected),
        "works_whose_identifiers_are_one_record": len(one_record),
    }
    os.makedirs("reports", exist_ok=True)
    with open(os.path.join("reports", "aliases.json"), "w") as fh:
        json.dump({"summary": summary, "works": sorted(one_record)}, fh, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data")
