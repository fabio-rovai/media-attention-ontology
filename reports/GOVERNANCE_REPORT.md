# Media Attention Ontology: governance report

Generated 2026-08-16 from a live Wikidata harvest and same-day EIDR public resolution. Both are living systems; a re-run moves the totals.

## Corpus

| quantity | value |
|---|---|
| (item, EIDR identifier) pairs harvested | 224,710 |
| distinct Wikidata items | 224,182 |
| distinct EIDR identifier values | 224,577 |
| EIDR records resolved against the public registry | 1,179 |

## Finding 1: check-character arithmetic

**224,577 distinct EIDR identifiers, zero check-character failures.** This is a guarded null result and it is reported as one. Unlike company and fund identifier registers, where hand-keyed values routinely fail their own arithmetic, the EIDR values mirrored into Wikidata are arithmetically perfect, which is consistent with their having been machine-imported rather than typed.

EIDR's check character is the ISO 7064 hybrid system MOD 37,36 exactly as published, and a stock library (python-stdnum `iso7064.mod_37_36`) agrees with `pipeline/eidr.py` on every identifier (`tests/test_eidr.py`). **6,252 identifiers, 2.78% of the total**, carry the check character `0`, almost exactly the one-in-thirty-six a uniformly distributed check character predicts.

## Finding 2: one identifier, two works

**133 EIDR identifiers are each claimed by two distinct Wikidata items**, involving 266 items in total. Either the catalogue holds the same work twice, or two genuinely different works have been given the same registry identifier. Both are entity-resolution defects, and neither is visible to a schema that stores identifiers as literals.

Levels of the contested identifiers:

| EIDR structural type / referent type | count |
|---|---|
| Abstraction / Movie | 69 |
| Abstraction / Short | 43 |
| Abstraction / TV | 15 |
| Abstraction / Series | 5 |
| Abstraction / Season | 1 |

## Finding 3: one work, several identifiers at different levels

**522 Wikidata items carry more than one EIDR identifier** (516 of them carry 2, 6 of them carry 3). Resolving those identifiers against EIDR's own registry shows what they actually denote:

| structural types held by one item | count |
|---|---|
| Abstraction + Performance | 281 |
| Abstraction + Abstraction | 232 |
| Abstraction + Abstraction + Abstraction | 5 |
| Abstraction + Digital | 3 |
| Abstraction + Abstraction + Performance | 1 |

**285 of the resolved items hold identifiers at more than one level of the abstraction hierarchy at once**, a title-level abstraction and a specific cut, for instance, attached to the same node as though they were interchangeable. This is the scope conflation the ontology's registry is designed to make impossible to state silently: the identifiers are not synonyms, they denote different things, and a join on either one produces a different answer.

## Finding 4: what the open identifier fabric actually reaches

Coverage of each work type in Wikidata, by identifier scheme:

| work type | items | with EIDR | with IMDb |
|---|---|---|---|
| film | 348,231 | 186,079 (53.44%) | 273,283 (78.48%) |
| television series | 87,959 | 1,620 (1.84%) | 50,245 (57.12%) |
| television series episode | 181,418 | 14,277 (7.87%) | 152,758 (84.2%) |
| television series season | 26,429 | 784 (2.97%) | 205 (0.78%) |
| television film | 22,631 | 6,213 (27.45%) | 21,090 (93.19%) |
| short film | 49,639 | 7,998 (16.11%) | 31,704 (63.87%) |

This is the result that matters most for anyone building measurement on open identifiers. EIDR is the audiovisual industry's own registry, and in the open graph it is overwhelmingly a *film* registry. Television, the thing television measurement measures, is close to absent. A cross-screen graph that assumes a shared content identifier across film and television is assuming something the open data does not supply.

## Finding 5: the advertising vocabularies have no semantics

The IAB Tech Lab publishes the Content, Audience and Ad Product taxonomies as tab-separated files. The repository contains no RDF, no SKOS and no OWL of any kind: the advertising industry's shared vocabularies ship as spreadsheets whose hierarchy every consumer re-implements. Converted faithfully to SKOS here:

| scheme | concepts | triples | structural defects in source |
|---|---|---|---|
| content-3.1 | 704 | 6,756 | 0 |
| audience-1.1 | 1,558 | 17,104 | 0 |
| adproduct-2.0 | 583 | 5,460 | 10 |

The Ad Product Taxonomy 2.0 contains concepts that declare themselves as their own parent (`1000`, `1037`), which is a cycle in what is meant to be a tree, plus 8 rows whose name column disagrees with its own tier column. The conversion records these rather than repairing them, so the SKOS and the published TSV stay comparable row for row.
