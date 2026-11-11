"""EIDR content-ID check character: the ISO 7064 hybrid system MOD 37,36.

Verified against real EIDR identifiers harvested from Wikidata and against a stock
library: python-stdnum's iso7064.mod_37_36 agrees with this module on all 224,577
(tests/test_eidr.py).

The check alphabet is the ten digits and the twenty-six capital letters. The hybrid
system closes its computation modulo 36, so there is no supplementary character; '*'
belongs to the pure system MOD 37-2.

A previous version of this note described the '0' check character as EIDR's own
mapping of a supplementary value. Thanks to Richard W. Kroon at EIDR that behaviour
is explained: '0' is the check character MOD 37,36 itself gives.
"""
import re

ALPHA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
PAT = re.compile(r"^10\.5240/([0-9A-F]{4}(?:-[0-9A-F]{4}){4})-([0-9A-Z])$")


def parse(eidr):
    """Return (payload_without_hyphens, check_char) or (None, None) if malformed."""
    m = PAT.match(eidr.strip().upper())
    if not m:
        return None, None
    return m.group(1).replace("-", ""), m.group(2)


def check_character(payload):
    """Compute the EIDR check character for a 20-symbol payload."""
    p = 36
    for c in payload:
        s = (p + ALPHA.index(c)) % 36 or 36
        p = (s * 2) % 37
    return ALPHA[((37 - p) % 37) % 36]


def is_valid(eidr):
    payload, chk = parse(eidr)
    if payload is None:
        return False
    return check_character(payload) == chk


# Test vectors: real EIDR identifiers, including two whose check character is '0'.
TEST_VECTORS = [
    ("10.5240/1735-1DDC-D724-F42E-BE7A-7", True),
    ("10.5240/12CE-96C8-D806-F79D-3DAC-G", True),
    ("10.5240/8233-E6F9-F524-2826-0F71-O", True),
    ("10.5240/524F-9B57-5289-D954-B2F6-0", True),   # check character '0'
    ("10.5240/7DA3-5D43-8684-1686-8F10-0", True),   # check character '0'
    ("10.5240/1735-1DDC-D724-F42E-BE7A-8", False),  # check char altered
    ("10.5240/1735-1DDC-D724-F42E-BE7B-7", False),  # payload altered
]

if __name__ == "__main__":
    for v, expected in TEST_VECTORS:
        got = is_valid(v)
        assert got == expected, f"{v}: expected {expected}, got {got}"
    print(f"all {len(TEST_VECTORS)} embedded test vectors pass")
