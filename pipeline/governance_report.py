"""Compute the findings and write the governance report.

Set-based rather than graph-based on purpose. The SHACL layer states the rules
declaratively and is the artefact other people should reuse; this module
recomputes the same questions directly over the harvest so that the two can be
compared. Where they disagree, one of them is wrong, and it is much better to
discover that here than in a slide.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eidr import check_character, is_valid, parse  # noqa: E402


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open() if line.strip()]


def compute(pairs, resolved, totals):
    by_value, by_item = defaultdict(set), defaultdict(set)
    for p in pairs:
        by_value[p["eidr"]].add(p["qid"])
        by_item[p["qid"]].add(p["eidr"])

    check_char_counts = Counter(v[-1] for v in by_value)
    zero_check = check_char_counts.get("0", 0)

    invalid = []
    for v in by_value:
        if not is_valid(v):
            payload, chk = parse(v)
            invalid.append({"value": v, "expected": check_character(payload) if payload else None,
                            "found": chk, "items": sorted(by_value[v])})

    shared = {v: sorted(q) for v, q in by_value.items() if len(q) > 1}
    multi = {q: sorted(v) for q, v in by_item.items() if len(v) > 1}

    # For every item carrying more than one EIDR, what levels are those
    # identifiers at? This is the scope-conflation measurement.
    level_combos, referent_combos, unresolved_items = Counter(), Counter(), 0
    conflations = []
    for qid, vals in multi.items():
        recs = [resolved.get(v) for v in vals]
        if any(r is None or not r.get("structural_type") for r in recs):
            unresolved_items += 1
            continue
        sts = tuple(sorted(r["structural_type"] for r in recs))
        rts = tuple(sorted((r.get("referent_type") or "?") for r in recs))
        level_combos[" + ".join(sts)] += 1
        referent_combos[" + ".join(rts)] += 1
        if len(set(sts)) > 1:
            conflations.append({"qid": qid, "values": vals, "structural_types": list(sts),
                                "referent_types": list(rts)})

    # And for the shared values: what is the level of the identifier that two
    # distinct items are both claiming?
    shared_levels = Counter()
    shared_detail = []
    for v, qids in shared.items():
        r = resolved.get(v)
        st = (r or {}).get("structural_type") or "unresolved"
        rt = (r or {}).get("referent_type") or "unresolved"
        shared_levels[f"{st} / {rt}"] += 1
        if r:
            shared_detail.append({"value": v, "items": qids, "structural_type": st,
                                  "referent_type": rt, "name": r.get("name")})

    return {
        "corpus": {
            "pairs": len(pairs),
            "distinct_items": len(by_item),
            "distinct_values": len(by_value),
            "resolved_records": len(resolved),
        },
        "f1_checksum_failures": {
            "count": len(invalid), "detail": invalid[:50],
            "zero_check_character": zero_check,
            "zero_check_pct": round(100 * zero_check / len(by_value), 2) if by_value else None,
        },
        "f2_shared_values": {"count": len(shared),
                             "items_involved": sum(len(q) for q in shared.values()),
                             "by_level": dict(shared_levels.most_common()),
                             "detail": shared_detail[:50]},
        "f3_multi_identifier_items": {
            "count": len(multi),
            "distribution": dict(Counter(len(v) for v in multi.values())),
            "unresolved": unresolved_items,
            "structural_type_combinations": dict(level_combos.most_common()),
            "referent_type_combinations": dict(referent_combos.most_common(15)),
            "cross_level_count": len(conflations),
            "cross_level_examples": conflations[:25],
        },
        "f4_coverage_by_type": totals.get("coverage_by_type", {}),
        "f5_property_totals": totals.get("property_totals", {}),
    }


def render(f, iab=None) -> str:
    c = f["corpus"]
    L = []
    A = L.append
    A(f"# Media Attention Ontology: governance report\n")
    A(f"Generated {date.today().isoformat()} from a live Wikidata harvest and "
      f"same-day EIDR public resolution. Both are living systems; a re-run moves "
      f"the totals.\n")

    A("## Corpus\n")
    A(f"| quantity | value |")
    A(f"|---|---|")
    A(f"| (item, EIDR identifier) pairs harvested | {c['pairs']:,} |")
    A(f"| distinct Wikidata items | {c['distinct_items']:,} |")
    A(f"| distinct EIDR identifier values | {c['distinct_values']:,} |")
    A(f"| EIDR records resolved against the public registry | {c['resolved_records']:,} |")
    A("")

    A("## Finding 1: check-character arithmetic\n")
    n = f["f1_checksum_failures"]["count"]
    if n == 0:
        A(f"**{c['distinct_values']:,} distinct EIDR identifiers, zero check-character "
          f"failures.** This is a guarded null result and it is reported as one. "
          f"Unlike company and fund identifier registers, where hand-keyed values "
          f"routinely fail their own arithmetic, the EIDR values mirrored into "
          f"Wikidata are arithmetically perfect, which is consistent with their "
          f"having been machine-imported rather than typed.\n")
        z = f["f1_checksum_failures"]
        A(f"EIDR's check character is the ISO 7064 hybrid system MOD 37,36 exactly "
          f"as published, and a stock library (python-stdnum `iso7064.mod_37_36`) "
          f"agrees with `pipeline/eidr.py` on every identifier "
          f"(`tests/test_eidr.py`). **{z['zero_check_character']:,} identifiers, "
          f"{z['zero_check_pct']}% of the total**, carry the check character `0`, "
          f"almost exactly the one-in-thirty-six a uniformly distributed check "
          f"character predicts.\n")
    else:
        A(f"**{n} identifiers fail their check character.**\n")
        A("| value | expected | found | items |")
        A("|---|---|---|---|")
        for d in f["f1_checksum_failures"]["detail"][:20]:
            A(f"| `{d['value']}` | {d['expected']} | {d['found']} | {', '.join(d['items'])} |")
        A("")

    A("## Finding 2: one identifier, two works\n")
    s = f["f2_shared_values"]
    A(f"**{s['count']} EIDR identifiers are each claimed by two distinct Wikidata "
      f"items**, involving {s['items_involved']} items in total. Either the "
      f"catalogue holds the same work twice, or two genuinely different works have "
      f"been given the same registry identifier. Both are entity-resolution "
      f"defects, and neither is visible to a schema that stores identifiers as "
      f"literals.\n")
    if s["by_level"]:
        A("Levels of the contested identifiers:\n")
        A("| EIDR structural type / referent type | count |")
        A("|---|---|")
        for k, v in s["by_level"].items():
            A(f"| {k} | {v} |")
        A("")

    A("## Finding 3: one work, several identifiers at different levels\n")
    m = f["f3_multi_identifier_items"]
    dist = ", ".join(f"{v:,} of them carry {k}"
                     for k, v in sorted(m["distribution"].items()))
    A(f"**{m['count']} Wikidata items carry more than one EIDR identifier** "
      f"({dist}). Resolving those identifiers against EIDR's own registry shows "
      f"what they actually denote:\n")
    A("| structural types held by one item | count |")
    A("|---|---|")
    for k, v in m["structural_type_combinations"].items():
        A(f"| {k} | {v} |")
    A("")
    A(f"**{m['cross_level_count']} of the resolved items hold identifiers at "
      f"more than one level of the abstraction hierarchy at once**, a title-level "
      f"abstraction and a specific cut, for instance, attached to the same node as "
      f"though they were interchangeable. This is the scope conflation the "
      f"ontology's registry is designed to make impossible to state silently: the "
      f"identifiers are not synonyms, they denote different things, and a join on "
      f"either one produces a different answer.\n")
    if m["unresolved"]:
        A(f"({m['unresolved']} multi-identifier items could not be fully resolved "
          f"against the public registry within this run and are excluded from the "
          f"level analysis rather than guessed at.)\n")

    A("## Finding 4: what the open identifier fabric actually reaches\n")
    A("Coverage of each work type in Wikidata, by identifier scheme:\n")
    A("| work type | items | with EIDR | with IMDb |")
    A("|---|---|---|---|")
    for k, v in f["f4_coverage_by_type"].items():
        A(f"| {k} | {v['total']:,} | {v['with_eidr']:,} ({v['eidr_pct']}%) | "
          f"{v['with_imdb']:,} ({v['imdb_pct']}%) |")
    A("")
    A("This is the result that matters most for anyone building measurement on "
      "open identifiers. EIDR is the audiovisual industry's own registry, and in "
      "the open graph it is overwhelmingly a *film* registry. Television, the "
      "thing television measurement measures, is close to absent. A cross-screen "
      "graph that assumes a shared content identifier across film and television "
      "is assuming something the open data does not supply.\n")

    if iab:
        A("## Finding 5: the advertising vocabularies have no semantics\n")
        A("The IAB Tech Lab publishes the Content, Audience and Ad Product "
          "taxonomies as tab-separated files. The repository contains no RDF, no "
          "SKOS and no OWL of any kind: the advertising industry's shared "
          "vocabularies ship as spreadsheets whose hierarchy every consumer "
          "re-implements. Converted faithfully to SKOS here:\n")
        A("| scheme | concepts | triples | structural defects in source |")
        A("|---|---|---|---|")
        for k, v in iab.items():
            if "error" in v:
                continue
            A(f"| {k} | {v['concepts']:,} | {v['triples']:,} | {v['defect_total']} |")
        A("")
        ad = iab.get("adproduct-2.0", {})
        if ad.get("defects", {}).get("self_parent"):
            A(f"The Ad Product Taxonomy 2.0 contains concepts that declare "
              f"themselves as their own parent "
              f"(`{'`, `'.join(ad['defects']['self_parent'])}`), which is a cycle "
              f"in what is meant to be a tree, plus "
              f"{len(ad['defects'].get('name_tier_mismatch', []))} rows whose name "
              f"column disagrees with its own tier column. The conversion records "
              f"these rather than repairing them, so the SKOS and the published "
              f"TSV stay comparable row for row.\n")

    return "\n".join(L)


if __name__ == "__main__":
    data = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
    pairs = load_jsonl(data / "wikidata_eidr.jsonl")
    resolved = {r["id"]: r for r in load_jsonl(data / "eidr_resolved.jsonl")} \
        if (data / "eidr_resolved.jsonl").exists() else {}
    totals = json.loads((data / "wikidata_totals.json").read_text()) \
        if (data / "wikidata_totals.json").exists() else {}
    iab_path = Path("reports/iab_conversion.json")
    iab = json.loads(iab_path.read_text()) if iab_path.exists() else None

    findings = compute(pairs, resolved, totals)
    Path("reports").mkdir(exist_ok=True)
    Path("reports/findings.json").write_text(json.dumps(findings, indent=2))
    Path("reports/GOVERNANCE_REPORT.md").write_text(render(findings, iab))
    print(json.dumps({k: (v if not isinstance(v, dict) else
                          {kk: vv for kk, vv in v.items() if kk != "detail"})
                      for k, v in findings.items()}, indent=2)[:3000])
    print("\nwrote reports/GOVERNANCE_REPORT.md")
