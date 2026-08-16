"""Minimal, polite Wikidata SPARQL client with retry. Used for feasibility probing."""
import json
import sys
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://query.wikidata.org/sparql"
UA = "MediaAttentionOntology/0.1 (https://github.com/fabio-rovai; fabio@thetesseractacademy.com)"


def query(q, retries=4, timeout=300):
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(
            ENDPOINT + "?" + urllib.parse.urlencode({"query": q}),
            headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001 - probing script, report and back off
            last = e
            body = ""
            if hasattr(e, "read"):
                try:
                    body = e.read().decode()[:300]
                except Exception:
                    pass
            print(f"  [retry {attempt+1}/{retries}] {type(e).__name__}: {e} {body}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"query failed after {retries} attempts: {last}")


def rows(q, **kw):
    d = query(q, **kw)
    cols = d["head"]["vars"]
    return [{c: b[c]["value"] for c in cols if c in b} for b in d["results"]["bindings"]]


def scalar_row(q, **kw):
    r = rows(q, **kw)
    return r[0] if r else {}


if __name__ == "__main__":
    print(json.dumps(rows(sys.stdin.read()), indent=2)[:4000])
