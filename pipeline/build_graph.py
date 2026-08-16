"""Build the MAO instance graph from the Wikidata harvest and the EIDR resolution cache.

Design note. Every EIDR value becomes an IdentifierAssertion node rather than a
literal on the work, carrying the scheme it was minted under, the system it was
observed in (Wikidata, not EIDR), and the computed result of its check-character
arithmetic. Where the identifier has also been resolved against EIDR's public
service, the record's own declared structural type is attached to the assertion,
which is what allows a scope violation to be computed rather than assumed.

Engineering note. The instance graph runs to millions of triples. Holding it in
an in-memory rdflib Graph and serialising Turtle does not survive at that size,
so triples are streamed straight out as N-Triples. N-Triples is line-oriented
and order-independent, so the writer stays flat in memory and the output can be
loaded incrementally by any triplestore. The ontology, registry and shape files
stay in Turtle, where the readability is worth having and the size is trivial.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eidr import is_valid  # noqa: E402

MAO = "https://gov.tesseract.academy/def/media#"
MAOSCH = "https://gov.tesseract.academy/def/media/scheme#"
EX = "https://gov.tesseract.academy/id/media/"
XSD = "http://www.w3.org/2001/XMLSchema#"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

STRUCTURAL_TO_CLASS = {
    "Abstraction": "AbstractWork",
    "Performance": "Edit",
    "Digital": "Manifestation",
    "Composite": "CreativeWork",
}

REFERENT_TO_CLASS = {
    "Movie": "Film",
    "Short": "Film",
    "TV": "Episode",
    "Series": "Series",
    "Season": "Season",
}


def esc(s: str) -> str:
    return (s.replace("\\", "\\\\").replace('"', '\\"')
             .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"))


class NTWriter:
    """Streaming N-Triples writer. Flat memory regardless of graph size."""

    def __init__(self, fh):
        self.fh = fh
        self.count = 0

    def rel(self, s: str, p: str, o: str):
        self.fh.write(f"<{s}> <{p}> <{o}> .\n")
        self.count += 1

    def lit(self, s: str, p: str, value, datatype: str | None = None):
        obj = f'"{esc(str(value))}"'
        if datatype:
            obj += f"^^<{datatype}>"
        self.fh.write(f"<{s}> <{p}> {obj} .\n")
        self.count += 1


def load_jsonl(path: Path):
    with path.open() as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def build(pairs, resolved, out_path: Path) -> dict:
    by_value, by_item = defaultdict(set), defaultdict(set)
    for p in pairs:
        by_value[p["eidr"]].add(p["qid"])
        by_item[p["qid"]].add(p["eidr"])

    stats = {"works": 0, "eidr_assertions": 0, "wikidata_assertions": 0,
             "checksum_failures": 0, "resolved_assertions": 0, "identity_links": 0}

    with out_path.open("w") as fh:
        w = NTWriter(fh)

        for qid, vals in by_item.items():
            work = f"{EX}work/{qid}"
            w.rel(work, RDF_TYPE, f"{MAO}CreativeWork")
            stats["works"] += 1

            wd = f"{EX}id/wikidata/{qid}"
            w.rel(work, f"{MAO}hasIdentifier", wd)
            w.rel(wd, RDF_TYPE, f"{MAO}IdentifierAssertion")
            w.lit(wd, f"{MAO}identifierValue", qid)
            w.rel(wd, f"{MAO}identifierScheme", f"{MAOSCH}WikidataItem")
            w.rel(wd, f"{MAO}identifierSource", f"{MAOSCH}SourceWikidata")
            stats["wikidata_assertions"] += 1

            for val in sorted(vals):
                slug = val.replace("10.5240/", "").replace("/", "_")
                node = f"{EX}id/eidr/{slug}/{qid}"
                w.rel(work, f"{MAO}hasIdentifier", node)
                w.rel(node, RDF_TYPE, f"{MAO}IdentifierAssertion")
                w.lit(node, f"{MAO}identifierValue", val)
                w.rel(node, f"{MAO}identifierScheme", f"{MAOSCH}EIDR")
                w.rel(node, f"{MAO}identifierSource", f"{MAOSCH}SourceWikidata")
                ok = is_valid(val)
                w.lit(node, f"{MAO}checksumValid", "true" if ok else "false",
                      f"{XSD}boolean")
                stats["eidr_assertions"] += 1
                if not ok:
                    stats["checksum_failures"] += 1

                rec = resolved.get(val)
                if rec and rec.get("structural_type"):
                    stats["resolved_assertions"] += 1
                    w.lit(node, f"{MAO}resolvedInRegistry", "true", f"{XSD}boolean")
                    w.lit(node, f"{MAOSCH}eidrStructuralType", rec["structural_type"])
                    if rec.get("referent_type"):
                        w.lit(node, f"{MAOSCH}eidrReferentType", rec["referent_type"])
                    cls = STRUCTURAL_TO_CLASS.get(rec["structural_type"])
                    if cls:
                        w.rel(work, RDF_TYPE, f"{MAO}{cls}")
                    rcls = REFERENT_TO_CLASS.get(rec.get("referent_type"))
                    if rcls:
                        w.rel(work, RDF_TYPE, f"{MAO}{rcls}")
                    if rec.get("name"):
                        w.lit(work, f"{MAO}title", rec["name"])

        # One value on two items is an identity question, so it is recorded as a
        # graded link rather than as owl:sameAs. Nothing here justifies asserting
        # that the two items denote the same thing, only that a registry
        # identifier says they might.
        for val, qids in by_value.items():
            if len(qids) < 2:
                continue
            qs = sorted(qids)
            for a, b in zip(qs, qs[1:]):
                link = f"{EX}link/eidr-collision/{a}-{b}"
                w.rel(link, RDF_TYPE, f"{MAO}IdentityLink")
                w.rel(link, f"{MAO}linkSubject", f"{EX}work/{a}")
                w.rel(link, f"{MAO}linkObject", f"{EX}work/{b}")
                w.rel(link, f"{MAO}linkMethod", f"{MAOSCH}RegistryCrossReference")
                w.lit(link, f"{MAO}linkConfidence", "0.5", f"{XSD}decimal")
                w.lit(link, f"{MAO}linkStatus", "proposed")
                w.rel(link, f"{MAO}linkAssertedBy", f"{MAOSCH}SourceWikidata")
                stats["identity_links"] += 1

        stats["triples"] = w.count

    stats["shared_values"] = sum(1 for v in by_value.values() if len(v) > 1)
    stats["multi_identifier_items"] = sum(1 for v in by_item.values() if len(v) > 1)
    stats["distinct_values"] = len(by_value)
    stats["distinct_items"] = len(by_item)
    return stats


if __name__ == "__main__":
    data = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
    out = data / "build"
    out.mkdir(parents=True, exist_ok=True)

    pairs = list(load_jsonl(data / "wikidata_eidr.jsonl"))
    resolved = {}
    rp = data / "eidr_resolved.jsonl"
    if rp.exists():
        for r in load_jsonl(rp):
            resolved[r["id"]] = r
    print(f"pairs={len(pairs):,} resolved_records={len(resolved):,}", flush=True)

    dest = out / "mao_graph.nt"
    stats = build(pairs, resolved, dest)
    (out / "build_stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
    print(f"wrote {dest} ({dest.stat().st_size/1_048_576:.1f} MiB)")
