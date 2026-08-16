# Build report

Everything below was fetched or computed on 15 to 16 August 2026. It records what was obtained, what was not, and which claims rest on which evidence. Where a number could not be verified, it is not stated.

## What was fetched

| source | access | what was taken | volume |
|---|---|---|---|
| Wikidata Query Service | public SPARQL, no key, descriptive User-Agent | every `P2704` (EIDR content ID) statement; statement, item and value counts for `P2704`, `P12142`, `P3212`, `P345`; per work-type coverage counts | 224,710 (item, identifier) pairs |
| EIDR public resolution service | `resolve.eidr.org`, no authentication, HTTP 200 on every request | `StructuralType`, `ReferentType`, `Mode`, `ResourceName` for identifiers involved in the collision and multi-identifier findings | 1,179 records |
| IAB Tech Lab Taxonomies | public GitHub clone | Content 3.1, Audience 1.1, Ad Product 2.0 | 2,845 concepts from 21 TSV files |
| schema.org | `schema.org/version/latest/schemaorg-current-https.ttl` | full current vocabulary, parsed to enumerate terms | 17,949 triples, 2,987 labelled terms |

## Method, and the checks applied to it

**EIDR check character.** Derived empirically rather than assumed. Four candidate closing formulas for the ISO 7064 hybrid MOD 37,36 computation were tested against 2,000 real identifiers. The standard formula matched 97.05%, and the 59 failures were not random: they were exactly the cases where the computation yields the supplementary value, and the recorded check character was `0` where the standard convention is `*`. With that single mapping corrected, the algorithm validates **224,577 of 224,577 distinct identifiers, 100%**. The check characters are near-uniformly distributed across the 36 symbols (most common `V` at 6,373, least common `X` at 5,999), which is independent evidence the algorithm is right rather than coincidentally permissive. `pipeline/eidr.py` carries seven embedded test vectors including two `0`-check-character cases and two deliberate corruptions.

**Findings computed twice.** Every finding is computed set-based in `governance_report.py` and again as SPARQL over the built graph. Q1 (cross-level conflation) returns 285 and Q2 (identifier collisions) returns 133, matching the set-based report exactly. This is the cross-check that caught nothing this time and is the reason to trust the numbers.

**SHACL rules proven to fire.** `examples/rule-probe.ttl` contains exactly one violation of each rule R1 to R8. All eight fire. R3 initially did not, because `?content a mao:AbstractWork` inside a SPARQL constraint matches only direct types, unlike `sh:targetClass`, which walks `rdfs:subClassOf`. The rule was rewritten with an explicit `rdf:type/rdfs:subClassOf*` path and a regression test now guards it.

**A checker bug found and fixed before it became a finding.** The first IAB conversion run reported 1,555 structural defects in Audience Taxonomy 1.1. That was wrong. The Audience file's name column is `Condensed Name (1st, 2nd, Last Tier)`, a deliberate concatenation, and comparing it against the deepest tier flags the entire file. Corrected, Audience 1.1 has zero defects. The 10 defects reported in Ad Product 2.0 survive the correction and were verified by hand against the source TSV.

## What was NOT obtained, and what therefore is not claimed

**The wider landscape research did not complete.** Parallel research agents covering the media semantics standards landscape (MovieLabs Ontology for Media Creation, EBUCore, PBCore, W3C Media Annotations, TV-Anytime, DDEX), the ad tech identity landscape (UID2, RampID, ID5, device graphs, Privacy Sandbox), the hiring signal, the reachable network, and venues were terminated part-way by an API session limit. Fragments they emitted before dying are **not** used anywhere in this repository, because they were not verified. Consequently this build makes **no claim** about MovieLabs OMC, EBUCore, the job market, or who works where. Those sections of the context dossier remain to be done.

The single exception is a completed, separately sourced dossier on cross-media measurement ventures (ANA's Aquila and the WFA Halo framework), which is not relied upon for any number in this repository.

**Wikidata query service replica lag.** The aggregate count query consistently reports 224,725 `P2704` statements while the partitioned harvest consistently returns 224,710 pairs, a gap of 15. Both figures reproduce across repeated runs, and a regex probe for values not matching the EIDR pattern returns zero, so the gap is not malformed data. The most likely explanation is that the query service is a cluster whose replicas carry independent update lag, so different queries hit differently-lagged servers. The gap is 0.007% and is not chased further. It is recorded here rather than smoothed over.

**Findings 3 and 5 measure a mirror, not a registry.** The 133 contested identifiers and the 285 cross-level works are counted **as they appear in Wikidata**. Wikidata is a third-party mirror maintained by editors and bots. How much of this is a Wikidata editing artefact and how much reflects the state of EIDR itself cannot be settled from open data, and has deliberately not been guessed at. It is the repository's open question.

**Coverage figures measure the open graph, not EIDR.** Finding 6 says EIDR reaches 53.44% of films and 1.84% of television series **in Wikidata**. It does not say EIDR's own registry has that composition. The operationally relevant claim, and the one made, is about what an organisation can obtain without a commercial EIDR membership.

**No audience or viewership data was used.** No panel data, no automatic content recognition data, no impression logs. None is openly available, and the attention layer of the ontology is therefore modelled and shape-validated against a synthetic probe graph rather than instantiated against real measurement data. This is stated plainly because the ontology's most novel classes are the ones with no real data behind them yet.

## Licensing and redistribution

- **Wikidata** content is CC0. `data/wikidata_eidr.jsonl` is committed.
- **EIDR** records are resolved through the public resolution service. Only structural facets (`StructuralType`, `ReferentType`, `Mode`, `ResourceName`) for the 1,179 identifiers involved in the findings are retained and committed, so the findings can be reproduced without a re-resolution run. No bulk EIDR extract is taken or redistributed; the registry holds orders of magnitude more than this.
- **IAB Tech Lab taxonomies**: the upstream repository has no `LICENSE` file, but its `README.md` states a Creative Commons Attribution 3.0 licence covering the specification and the applicable taxonomies. That attribution and licence are carried into every generated SKOS concept scheme via `dcterms:license` and `dcterms:source`. The ambiguity of a licence asserted in a README rather than a licence file is noted rather than resolved.
- **The built graph** (`data/build/mao_graph.nt`, 2,702,154 triples, 474 MiB) is regenerated in under three seconds and is not committed.

## Reproducibility notes

Re-running moves the totals. Wikidata is edited continuously and EIDR registers new records daily. The pipeline is deterministic given fixed inputs; the inputs are not fixed.

Two things will bite anyone reimplementing this:

1. **The check character.** Implemented from ISO 7064 alone, a validator rejects 6,252 identifiers (2.78%) that are perfectly valid. This is not a rounding concern; it is a silent 1-in-36 false-positive rate in a data quality gate.
2. **Scale.** An in-memory rdflib graph serialising Turtle did not complete for 2.7 million triples in twelve minutes and was abandoned. Streaming N-Triples writes the same graph in 2.7 seconds with flat memory. Turtle is kept for the ontology, registries and shapes, where it is small and worth reading.
