# Media Attention Ontology (MAO)

An open OWL 2 ontology, SKOS registries, and SHACL governance layer for **content identity, distribution, and measured attention across screens**: what was released, where it could be watched, who observed a viewing of it, by which measurement method, and with what confidence.

Built and validated against the open identifier fabric that cross-screen measurement actually has to stand on:

- **224,710 (work, EIDR identifier) pairs** harvested from Wikidata, covering **224,182 distinct works** and **224,577 distinct EIDR identifiers**, every one check-character validated,
- **1,179 EIDR records resolved** against EIDR's own public resolution service, so that each identifier's declared structural type is a fact in the graph rather than an assumption,
- **2,702,154 triples**, gated by SHACL, with the findings recomputed independently and cross-checked against the SPARQL queries,
- the **first SKOS serialisation of the IAB Tech Lab Content, Audience and Ad Product taxonomies** (2,845 concepts), which have never been published in any RDF form.

This is not a toy schema. It is the question every media measurement team actually lives with: the same programme appears under different identifiers, at different levels of abstraction, in every catalogue it touches, and nothing in the open standards landscape tells you which of those identifiers you are allowed to join on.

## Findings from the first full build (16 August 2026)

All figures from a live Wikidata harvest and same-day EIDR resolution. Both are living systems; a re-fetch moves the totals.

| # | Finding | Number |
|---|---|---|
| 1 | Distinct EIDR identifiers checked, **zero check-character failures**. Reported as a guarded null result: unlike company and fund registers, this data is arithmetically perfect, consistent with machine import rather than hand keying | **0 of 224,577** |
| 2 | EIDR identifiers whose check character is `0`. EIDR runs the ISO 7064 hybrid MOD 37,36 computation but maps the supplementary value to `0` where the standard convention is `*`. **A validator built on a stock ISO 7064 library rejects every one of these as corrupt, and every one is perfectly valid** | **6,252 (2.78%)** |
| 3 | EIDR identifiers each claimed by **two distinct works**, involving 266 works. Every one resolves to an Abstraction record: 69 Movie, 43 Short, 15 TV, 5 Series, 1 Season | **133** |
| 4 | Works carrying **more than one EIDR identifier** (516 carry two, 6 carry three) | **522** |
| 5 | Of those, works holding identifiers at **more than one level of the abstraction hierarchy at once**, a title-level record and a specific cut attached to the same node as though interchangeable. 281 are Abstraction plus Performance, 3 Abstraction plus Digital | **285 (54.6%)** |
| 6 | EIDR coverage of **films** in Wikidata versus **television series**. EIDR is the audiovisual industry's own registry, and in the open graph it is overwhelmingly a film registry | **53.44% vs 1.84%** |
| 7 | IMDb coverage of **television seasons**. IMDb mints no season-level identifier, so a join routed through IMDb cannot express season structure at all, which matters because scheduling, availability and measurement are frequently organised by season | **0.78% (205 of 26,429)** |
| 8 | RDF, SKOS or OWL files in the IAB Tech Lab taxonomy repository. The advertising industry's shared vocabularies ship as 21 tab-separated spreadsheets whose hierarchy every consumer re-implements | **0** |
| 9 | Structural defects found in the source while converting them, including **two concepts in Ad Product Taxonomy 2.0 that declare themselves as their own parent**, a cycle in what is meant to be a tree, plus 8 rows whose name column disagrees with its own tier column | **10** |

Coverage of the open identifier fabric, by work type:

| work type | items in Wikidata | with EIDR | with IMDb |
|---|---|---|---|
| film | 348,231 | 186,079 (53.44%) | 273,283 (78.48%) |
| television series | 87,959 | 1,620 (1.84%) | 50,245 (57.12%) |
| television series episode | 181,418 | 14,277 (7.87%) | 152,758 (84.20%) |
| television series season | 26,429 | 784 (2.97%) | 205 (0.78%) |
| television film | 22,631 | 6,213 (27.45%) | 21,090 (93.19%) |
| short film | 49,639 | 7,998 (16.11%) | 31,704 (63.87%) |

The single most consequential number here is finding 6. A cross-screen measurement graph that assumes a shared content identifier spanning film and television is assuming something the open data does not supply.

Full numbers, method and caveats: [BUILD_REPORT.md](BUILD_REPORT.md) and [reports/GOVERNANCE_REPORT.md](reports/GOVERNANCE_REPORT.md).

## Why this exists

Media is unusually well served for *supply-side* metadata and unusually badly served for *attention*. The gap is verifiable rather than asserted:

- **schema.org** ships 2,987 labelled terms, of which 25 cover broadcast and television distribution: `TVSeries`, `TVEpisode`, `TVSeason`, `BroadcastEvent`, `BroadcastService`, `CableOrSatelliteService` and their properties. It contains **no term for viewership, impressions, exposure or reach**. Its `Audience` class and subclasses (`PeopleAudience`, `BusinessAudience`, `EducationalAudience`) describe who content is *intended for*, not who watched it. `WatchAction` and `ConsumeAction` exist as consumer-action markup with no measurement method, no observing party and no confidence. (Verified by parsing the current schema.org vocabulary, not from memory.)
- **EIDR** solves content identity properly, including the abstraction hierarchy, and its public resolution service is genuinely open. But it is a registry, not an ontology, and as finding 6 shows, its open reach into television is negligible.
- **The IAB Tech Lab taxonomies** are the advertising industry's shared vocabulary for content, audience and ad product, and they exist only as TSV. There is no RDF, no SKOS, no OWL, no URIs, and therefore no way to state that one taxonomy's concept is broader than another's without writing bespoke code.

So the open landscape gives you a way to say what a programme *is*, and no way at all to say that somebody watched it, how you know, or how much you should believe it. That is the gap MAO fills.

### Design commitments

Shared with its siblings, the [Investment Fund Ontology](https://github.com/fabio-rovai/investment-fund-ontology) and the [Insurance Register Ontology](https://github.com/fabio-rovai/insurance-register-ontology), of which this is the third vertical instantiation:

1. **The abstraction hierarchy is explicit.** Work, edit, manifestation, clip. A viewing event attaches to a manifestation on a service and never to an abstract work. Finding 5 is what happens when that distinction is not modelled: 285 works in the open graph already hold identifiers at two levels at once, and no schema that stores identifiers as literals can even express the problem.
2. **Identifiers are reified assertions**, carrying scheme, source system, scope level, and computed validation state. An EIDR identifier observed in Wikidata is Wikidata's claim about EIDR, and keeping that distinct from EIDR's own record is what makes third-party coverage measurable at all.
3. **Scope is declared on the scheme, as data.** The registry states that IMDb title identifiers are work-scoped, that Ad-ID is creative-scoped, and that EIDR is multi-level, meaning a bare EIDR identifier does not tell you what it denotes until you resolve it. "Can I join these two datasets on this column?" is answered in the registry rather than assumed by each consumer.
4. **Observation is separated from the thing observed.** An `AttentionEvent` is something that happened; an `Observation` is a record produced by a measurement method that purports to be evidence of it. Automatic content recognition, a panel meter, return-path data and a server-side ad log observing the same household in the same hour produce four observations that will disagree. The ontology holds all four with their methods and operators rather than forcing a single number that erases the disagreement.
5. **Identity links are graded, never `owl:sameAs`.** A probabilistic or embedding match is evidence about identity, not identity. The 133 registry collisions in finding 3 are loaded as `IdentityLink` nodes with status `proposed` and a recorded method, because a shared registry identifier is a reason to look, not a licence to merge.
6. **Derived attributes are auditable by construction.** A genre, brand or topic affinity carries its window, its method, its version and the number of observations it rests on. An affinity score without those is an unauditable number, and once such numbers are loaded and used for targeting there is no way to answer why a household carries one.
7. **Consent is modelled at party level and is queryable.** In a domain governed by video privacy statutes, "which derived attributes depend on a consent that has been withdrawn" has to be one traversal, and rule R7 makes it a validation failure rather than an investigation.

## Repository layout

```
ontology/mao-core.ttl        Core OWL 2: the work abstraction hierarchy, the reified
                             identifier fabric, graded identity links, distribution and
                             availability, devices and households, attention events and
                             their observations, the derived-attribute layer
skos/registries.ttl          SKOS: scope levels, identifier schemes (with check algorithms
                             and syntax patterns), source systems, measurement methods,
                             content identification methods, link methods, consent bases
skos/iab-*.ttl               The IAB Content 3.1, Audience 1.1 and Ad Product 2.0
                             taxonomies as SKOS, 2,845 concepts, CC BY 3.0 attribution
                             carried forward
shapes/mao-shapes.ttl        SHACL layers 1 to 3: structural completeness, checksum
                             policy, and eight cross-entity rules R1 to R8
pipeline/eidr.py             EIDR check character, ISO 7064 MOD 37,36 with EIDR's own
                             symbol mapping, with embedded test vectors
pipeline/wikidata.py         Polite Wikidata SPARQL client with retry
pipeline/harvest_wikidata.py Partitioned harvest, subdividing any partition the query
                             service truncates
pipeline/resolve_eidr.py     Public EIDR resolution, cached and resumable
pipeline/iab_to_skos.py      IAB TSV to SKOS, reporting source defects rather than
                             silently repairing them
pipeline/build_graph.py      Streaming N-Triples builder
pipeline/governance_report.py Set-based recomputation of every finding
queries/                     5 SPARQL queries; Q1 and Q2 reproduce the report exactly
examples/rule-probe.ttl      One deliberate violation of each rule R1 to R8
tests/                       13 tests, including a guard that every rule still fires
```

## Reproduce

```bash
pip install -r requirements.txt

python pipeline/harvest_wikidata.py data      # ~10 min, partitioned SPARQL
python pipeline/resolve_eidr.py               # public EIDR resolution, resumable
python pipeline/iab_to_skos.py --src <clone of IAB Taxonomies> --out skos
python pipeline/build_graph.py data           # 2.7M triples in under 3 seconds
python pipeline/governance_report.py data     # regenerates the findings
pytest -q                                     # 13 tests
```

Two engineering notes worth knowing before you run it.

**The check character.** EIDR's is the ISO 7064 hybrid MOD 37,36 computation, but where the standard maps the supplementary value to `*`, EIDR maps it to `0`. Implemented from the standard alone, a validator rejects 2.78% of all valid EIDR identifiers. `pipeline/eidr.py` carries embedded test vectors including that case, and the algorithm validates 224,577 real identifiers at 100%.

**Scale.** Holding 2.7 million triples in an in-memory rdflib graph and serialising Turtle does not survive; streaming N-Triples writes the same graph in under three seconds and stays flat in memory. The ontology, registry and shape files remain Turtle, where readability is worth having and the size is trivial.

## Validation

The shapes are not decorative. `examples/rule-probe.ttl` contains exactly one violation of each rule, and `tests/test_shapes.py` fails if any rule stops firing, because a SHACL rule that silently stops matching is worse than no rule: the run still passes and the gate still looks green.

The findings are computed twice, once set-based in `governance_report.py` and once as SPARQL over the built graph. Q1 returns 285 cross-level works and Q2 returns 133 contested identifiers, matching the report exactly. Where the two disagree, one of them is wrong, and it is much better to find that here than in a slide.

## Licence

Ontology, SKOS registries, shapes and documentation: **CC BY 4.0**. Pipeline code: **MIT**.

The IAB SKOS files are derived from the IAB Tech Lab taxonomies, published under **Creative Commons Attribution 3.0**; the attribution and licence are carried in each file's concept scheme. EIDR metadata is resolved through EIDR's public resolution service. Only structural facets for the 1,179 identifiers involved in the findings are retained and committed, so the findings reproduce without a re-resolution run. No bulk EIDR extract is taken or redistributed.

## Contributing, and one open question

Corrections are more welcome than additions, particularly from anyone closer to EIDR, the IAB Tech Lab taxonomy working group, or a measurement JIC than I am.

The open question I would most like help with: findings 3 and 5 count identifier collisions and level conflations **as they appear in Wikidata**, which is a third-party mirror. How much of that is Wikidata's editing artefact and how much reflects the state of the registries themselves is not something the open data can settle, and I have deliberately not guessed. If you can resolve it, please open an issue.

---

Built by [Fabio Rovai](https://fabiorovai.com) at [The Tesseract Academy](https://gov.tesseract.academy). If you are working on a knowledge graph for media measurement, content identity or audience data and want to talk about any of this, the contact route is on the site.
