"""Harvest media identifier assertions from Wikidata.

Wikidata is used here as a *source system*, not as an authority. Every value it
holds for EIDR, ISAN or IMDb is a third-party claim about someone else's
registry, and the whole point of the exercise is to measure how well those
claims hold up. That framing is why the graph reifies identifiers rather than
attaching them as literals.

The query service enforces a wall-clock limit, so the EIDR harvest is
partitioned by the leading hexadecimal digit of the identifier payload. The
partitions are disjoint and exhaustive by construction.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from wikidata import rows, scalar_row

HEX = "0123456789ABCDEF"

TYPES = {
    "film": "Q11424",
    "television series": "Q5398426",
    "television series episode": "Q21191270",
    "television series season": "Q3464665",
    "television film": "Q506240",
    "short film": "Q24862",
}

PROPERTIES = {
    "eidr_content": "P2704",
    "eidr_party": "P12142",
    "isan": "P3212",
    "imdb": "P345",
}


def property_totals() -> dict:
    """Statement, distinct-item and distinct-value counts for each property.

    The gap between statements and distinct values is the collision signal; the
    gap between statements and distinct items is the multi-identifier signal.
    Both are computed here so the harvest can be checked against them.
    """
    out = {}
    for name, pid in PROPERTIES.items():
        r = scalar_row(
            f"SELECT (COUNT(*) AS ?statements) (COUNT(DISTINCT ?i) AS ?items) "
            f"(COUNT(DISTINCT ?v) AS ?values) WHERE {{ ?i wdt:{pid} ?v }}"
        )
        out[name] = {k: int(v) for k, v in r.items()} | {"property": pid}
        print(f"{name:<14} {pid:<8} statements={out[name]['statements']:>9,} "
              f"items={out[name]['items']:>9,} values={out[name]['values']:>9,}",
              flush=True)
        time.sleep(1)
    return out


def _bucket_rows(prefix: str) -> list[dict]:
    q = (f'SELECT ?i ?v WHERE {{ ?i wdt:P2704 ?v . '
         f'FILTER(STRSTARTS(?v, "10.5240/{prefix}")) }}')
    return rows(q)


def harvest_eidr(max_depth: int = 3) -> tuple[list[dict], dict]:
    """Every (item, EIDR content identifier) pair, partitioned to fit the timeout.

    The query service occasionally truncates a large response mid-stream, and
    retrying the identical query tends to reproduce the truncation. Splitting the
    partition is what actually recovers, so a failing prefix is subdivided by the
    next hexadecimal character rather than retried indefinitely.
    """
    out, per_bucket = [], {}

    def walk(prefix: str, depth: int):
        t0 = time.time()
        try:
            r = _bucket_rows(prefix)
        except Exception as e:
            if depth >= max_depth:
                raise
            print(f"  bucket {prefix}: {type(e).__name__}, subdividing", flush=True)
            for c in HEX:
                walk(prefix + c, depth + 1)
            return
        per_bucket[prefix] = len(r)
        out.extend({"qid": x["i"].rsplit("/", 1)[-1], "eidr": x["v"]} for x in r)
        print(f"  bucket {prefix}: {len(r):>7,} rows in {time.time()-t0:5.1f}s", flush=True)
        time.sleep(1)

    for b in HEX:
        walk(b, 1)
    return out, per_bucket


def coverage_by_type() -> dict:
    """EIDR and IMDb coverage for each work type.

    This is the measurement that matters for a media-measurement graph: not how
    many identifiers exist, but which *kinds* of work the open identifier fabric
    actually reaches.
    """
    out = {}
    for name, qid in TYPES.items():
        tot = int(scalar_row(f"SELECT (COUNT(DISTINCT ?i) AS ?n) WHERE {{ ?i wdt:P31 wd:{qid} }}")["n"])
        eidr = int(scalar_row(f"SELECT (COUNT(DISTINCT ?i) AS ?n) WHERE {{ ?i wdt:P31 wd:{qid} ; wdt:P2704 ?v }}")["n"])
        imdb = int(scalar_row(f"SELECT (COUNT(DISTINCT ?i) AS ?n) WHERE {{ ?i wdt:P31 wd:{qid} ; wdt:P345 ?v }}")["n"])
        out[name] = {
            "wikidata_class": qid, "total": tot,
            "with_eidr": eidr, "eidr_pct": round(100 * eidr / tot, 2) if tot else None,
            "with_imdb": imdb, "imdb_pct": round(100 * imdb / tot, 2) if tot else None,
        }
        print(f"{name:<28} total={tot:>8,}  EIDR={eidr:>7,} "
              f"({out[name]['eidr_pct']:5.2f}%)  IMDb={imdb:>7,} ({out[name]['imdb_pct']:5.2f}%)",
              flush=True)
        time.sleep(1)
    return out


if __name__ == "__main__":
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("== property totals ==")
    totals = property_totals()

    print("\n== EIDR harvest ==")
    pairs, buckets = harvest_eidr()
    with (out_dir / "wikidata_eidr.jsonl").open("w") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")
    print(f"  harvested {len(pairs):,} pairs")

    print("\n== coverage by work type ==")
    cov = coverage_by_type()

    (out_dir / "wikidata_totals.json").write_text(json.dumps(
        {"property_totals": totals, "buckets": buckets,
         "harvested_pairs": len(pairs), "coverage_by_type": cov}, indent=2))
    print(f"\nwrote {out_dir/'wikidata_totals.json'}")
