"""EIDR check character: this repo's implementation against a stock ISO 7064 library.

The stock library is python-stdnum (iso7064.mod_37_36). The corpus test runs over
every distinct identifier in data/wikidata_eidr.jsonl.
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import eidr  # noqa: E402

mod_37_36 = pytest.importorskip("stdnum.iso7064.mod_37_36")


def stock_valid(value):
    payload, check = eidr.parse(value)
    if payload is None:
        return False
    return mod_37_36.is_valid(payload + check, alphabet=eidr.ALPHA)


def test_embedded_vectors():
    for value, expected in eidr.TEST_VECTORS:
        assert eidr.is_valid(value) is expected, value


def test_stock_library_agrees_on_vectors():
    for value, expected in eidr.TEST_VECTORS:
        assert stock_valid(value) is expected, value


def test_stock_library_agrees_on_corpus():
    with (ROOT / "data" / "wikidata_eidr.jsonl").open() as fh:
        values = {json.loads(line)["eidr"] for line in fh}
    assert len(values) > 200_000
    disagree = [v for v in values if eidr.is_valid(v) != stock_valid(v)]
    assert disagree == []
    assert all(stock_valid(v) for v in values)
