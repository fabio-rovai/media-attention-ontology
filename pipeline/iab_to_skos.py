"""Convert the IAB Tech Lab taxonomies from their published TSV form into SKOS.

The IAB Tech Lab publishes the Content, Audience and Ad Product taxonomies as
tab-separated files in github.com/InteractiveAdvertisingBureau/Taxonomies. Those
files already encode a concept scheme: every row carries a unique identifier, a
parent identifier, a preferred name, and the tier path that name sits on. What
they do not carry is any machine-readable semantics, so every consumer of the
advertising industry's controlled vocabularies re-implements the hierarchy walk,
and no two implementations agree about the defects.

This module performs a faithful, lossless conversion to SKOS and, in the same
pass, records the structural defects it finds rather than silently repairing
them. A converter that quietly fixes its input is how a defect survives for
years in every downstream copy.

Source licence: Creative Commons Attribution 3.0 (see the repository README of
the upstream project). Derived SKOS files carry the attribution forward.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, SKOS, XSD

BASE = "https://gov.tesseract.academy/def/media/iab/"
MAOSCH = Namespace("https://gov.tesseract.academy/def/media/scheme#")

# Scheme slug -> (relative path within the upstream repo, human title, version)
SCHEMES = {
    "content-3.1": ("Content Taxonomies/Content Taxonomy 3.1.tsv",
                    "IAB Tech Lab Content Taxonomy", "3.1"),
    "audience-1.1": ("Audience Taxonomies/Audience Taxonomy 1.1.tsv",
                     "IAB Tech Lab Audience Taxonomy", "1.1"),
    "adproduct-2.0": ("Ad Product Taxonomies/Ad Product Taxonomy 2.0.tsv",
                      "IAB Tech Lab Ad Product Taxonomy", "2.0"),
}

TIER_RE = re.compile(r"^Tier ?\d+$", re.I)


@dataclass
class Row:
    uid: str
    parent: str
    name: str
    tiers: list[str]
    condensed_name: bool = False
    """True where the source's name column is a concatenated tier path rather
    than a plain label. The Audience Taxonomy publishes 'Condensed Name (1st,
    2nd, Last Tier)'; comparing that against the deepest tier would report the
    entire file as inconsistent, which is a defect in the checker, not the data."""


@dataclass
class Defects:
    self_parent: list[str] = field(default_factory=list)
    dangling_parent: list[tuple[str, str]] = field(default_factory=list)
    duplicate_id: list[str] = field(default_factory=list)
    empty_name: list[str] = field(default_factory=list)
    name_tier_mismatch: list[tuple[str, str, str]] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)

    def as_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    def total(self):
        return sum(len(v) for v in self.__dict__.values())


def _locate_header(rows: list[list[str]]) -> int:
    """Return the index of the real header row.

    Content Taxonomy 3.1 carries a decorative group-header line above the
    column names; the Audience and Ad Product files do not. Detect the header
    by looking for the row that names the identifier column.
    """
    for i, r in enumerate(rows[:4]):
        cells = [c.strip().lower() for c in r]
        if any(c.startswith("unique id") for c in cells):
            return i
    raise ValueError("could not locate a header row naming 'Unique ID'")


def read_tsv(path: Path) -> list[Row]:
    raw = list(csv.reader(path.open(encoding="utf-8-sig"), delimiter="\t"))
    h = _locate_header(raw)
    header = [c.strip() for c in raw[h]]
    idx = {c.lower(): i for i, c in enumerate(header)}

    def col(*names):
        for n in names:
            if n in idx:
                return idx[n]
        return None

    i_uid = col("unique id")
    i_par = col("parent", "parent id")
    i_name = col("name", "condensed name (1st, 2nd, last tier)")
    condensed = i_name is not None and header[i_name].strip().lower().startswith("condensed name")
    tier_cols = [i for i, c in enumerate(header) if TIER_RE.match(c.strip())]

    out = []
    for r in raw[h + 1:]:
        if not any(c.strip() for c in r):
            continue
        def get(i):
            return r[i].strip() if i is not None and i < len(r) else ""
        tiers = [r[i].strip() for i in tier_cols if i < len(r) and r[i].strip()]
        out.append(Row(get(i_uid), get(i_par), get(i_name), tiers, condensed))
    return out


def analyse(rows: list[Row]) -> Defects:
    d = Defects()
    seen = set()
    ids = {r.uid for r in rows}
    for r in rows:
        if r.uid in seen:
            d.duplicate_id.append(r.uid)
        seen.add(r.uid)
        if not r.name:
            d.empty_name.append(r.uid)
        if r.parent and r.parent == r.uid:
            d.self_parent.append(r.uid)
        elif r.parent and r.parent not in ids:
            d.dangling_parent.append((r.uid, r.parent))
        # A plain Name column should equal the deepest populated tier. Where the
        # source publishes a condensed tier path instead, the equivalent check is
        # that the path's final segment matches the deepest tier.
        if r.tiers and r.name:
            observed = (r.name.split("|")[-1].strip() if r.condensed_name else r.name)
            if observed and observed != r.tiers[-1]:
                d.name_tier_mismatch.append((r.uid, r.name, r.tiers[-1]))

    # cycle detection over parent edges, excluding self-parents already recorded
    parent = {r.uid: r.parent for r in rows if r.parent and r.parent != r.uid}
    for start in parent:
        slow, fast, path = start, start, []
        seen_local = set()
        cur = start
        while cur in parent and cur not in seen_local:
            seen_local.add(cur)
            path.append(cur)
            cur = parent[cur]
        if cur in seen_local:
            d.cycles.append(path[path.index(cur):] if cur in path else path)
    return d


def to_skos(slug: str, rows: list[Row], title: str, version: str) -> Graph:
    g = Graph()
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)
    g.bind("maosch", MAOSCH)
    ns = Namespace(f"{BASE}{slug}/")
    g.bind(slug.replace(".", "_").replace("-", "_"), ns)

    scheme = URIRef(f"{BASE}{slug}")
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, DCTERMS.title, Literal(f"{title} {version}", lang="en")))
    g.add((scheme, DCTERMS.hasVersion, Literal(version)))
    g.add((scheme, DCTERMS.source,
           URIRef("https://github.com/InteractiveAdvertisingBureau/Taxonomies")))
    g.add((scheme, DCTERMS.license,
           URIRef("https://creativecommons.org/licenses/by/3.0/")))
    g.add((scheme, DCTERMS.publisher, Literal("IAB Technology Laboratory")))
    g.add((scheme, SKOS.note, Literal(
        "Converted from the upstream tab-separated publication without repair. "
        "Structural defects present in the source are reported alongside this "
        "file rather than corrected, so that the SKOS and the TSV remain "
        "comparable row for row.", lang="en")))

    ids = {r.uid for r in rows}
    for r in rows:
        c = ns[r.uid]
        g.add((c, RDF.type, SKOS.Concept))
        g.add((c, SKOS.inScheme, scheme))
        g.add((c, SKOS.notation, Literal(r.uid)))
        if r.name:
            g.add((c, SKOS.prefLabel, Literal(r.name, lang="en")))
        for depth, t in enumerate(r.tiers, start=1):
            g.add((c, MAOSCH[f"tier{depth}"], Literal(t, lang="en")))
        if r.tiers:
            g.add((c, MAOSCH.tierPath, Literal(" | ".join(r.tiers), lang="en")))
            g.add((c, MAOSCH.tierDepth, Literal(len(r.tiers), datatype=XSD.integer)))
        # broader only where the parent genuinely exists and is not the node itself
        if r.parent and r.parent != r.uid and r.parent in ids:
            g.add((c, SKOS.broader, ns[r.parent]))
        else:
            g.add((c, SKOS.topConceptOf, scheme))
            g.add((scheme, SKOS.hasTopConcept, c))
    return g


def convert_all(src_root: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for slug, (rel, title, version) in SCHEMES.items():
        path = src_root / rel
        if not path.exists():
            report[slug] = {"error": f"missing source file {rel}"}
            continue
        rows = read_tsv(path)
        defects = analyse(rows)
        g = to_skos(slug, rows, title, version)
        dest = out_dir / f"iab-{slug}.ttl"
        g.serialize(destination=str(dest), format="turtle")
        report[slug] = {
            "source_file": rel,
            "concepts": len(rows),
            "triples": len(g),
            "output": dest.name,
            "defects": defects.as_dict(),
            "defect_total": defects.total(),
        }
        print(f"{slug:<16} {len(rows):>5} concepts -> {len(g):>6} triples, "
              f"{defects.total()} structural defects", flush=True)
    return report


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="clone of the IAB Taxonomies repo")
    ap.add_argument("--out", default="skos", help="output directory")
    ap.add_argument("--report", default="reports/iab_conversion.json")
    a = ap.parse_args()

    rep = convert_all(Path(a.src), Path(a.out))
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(json.dumps(rep, indent=2))
    print(f"\nreport written to {a.report}")
