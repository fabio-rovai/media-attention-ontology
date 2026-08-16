"""Every layer-3 rule must fire against the probe graph.

This is the test that stops the shapes rotting. A SHACL rule that silently stops
matching is worse than no rule at all, because the validation run still passes
and the gate still looks green. The probe graph contains exactly one violation
of each rule, so a rule that stops firing fails this test loudly.
"""
from __future__ import annotations

import collections
import re
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
RULES = [f"R{i}" for i in range(1, 9)]


@pytest.fixture(scope="module")
def report_text() -> str:
    data = Graph()
    for f in ("examples/rule-probe.ttl", "ontology/mao-core.ttl", "skos/registries.ttl"):
        data.parse(ROOT / f, format="turtle")
    shapes = Graph().parse(ROOT / "shapes/mao-shapes.ttl", format="turtle")
    _, _, text = validate(data, shacl_graph=shapes, advanced=True, inference="none")
    return text


@pytest.fixture(scope="module")
def fired(report_text) -> collections.Counter:
    return collections.Counter(re.findall(r"\b(R[1-8]):", report_text))


@pytest.mark.parametrize("rule", RULES)
def test_rule_fires(rule, fired):
    assert fired[rule] > 0, f"{rule} did not fire against the probe graph"


def test_probe_graph_does_not_conform():
    data = Graph()
    for f in ("examples/rule-probe.ttl", "ontology/mao-core.ttl", "skos/registries.ttl"):
        data.parse(ROOT / f, format="turtle")
    shapes = Graph().parse(ROOT / "shapes/mao-shapes.ttl", format="turtle")
    conforms, _, _ = validate(data, shacl_graph=shapes, advanced=True, inference="none")
    assert conforms is False


@pytest.mark.parametrize("path", [
    "ontology/mao-core.ttl",
    "skos/registries.ttl",
    "shapes/mao-shapes.ttl",
])
def test_turtle_parses(path):
    g = Graph().parse(ROOT / path, format="turtle")
    assert len(g) > 0


def test_r3_requires_subclass_traversal():
    """R3 must catch a subclass of AbstractWork, not only AbstractWork itself.

    Regression guard: written with a bare `?content a mao:AbstractWork`, the rule
    matched nothing, because rdf:type inside a SPARQL constraint does not walk
    the subclass hierarchy the way sh:targetClass does.
    """
    src = (ROOT / "shapes/mao-shapes.ttl").read_text()
    r3 = src.split("mao:R3_UnwatchableAbstraction")[1].split("mao:R4_")[0]
    assert "subClassOf*" in r3
