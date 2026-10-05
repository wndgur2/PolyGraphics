"""Specimen cards: a small thing (or a little scene of them) as a throwaway document, for `scripts/bits.ts` to draw.

    from specimen import card
    card(outdir, "padlock", (24, 24), parts)

A spec script is run as `python3 <spec.py> <outdir>` and writes one card per
specimen there. The id is `ss.bits.<name>`, and nothing written here goes
into the library: the cards live in a scratch folder and are drawn against
the ss app's tokens and documents only to be looked at
(docs/small-things.md).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import write_doc  # noqa: E402


def card(outdir, name, size, parts, animations=None):
    ids = [p["id"] for p in parts]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    assert not dup, f"{name}: duplicate part ids {dup}"
    slug = name.replace("_", "-")
    d = {
        "id": f"ss.bits.{slug}",
        "name": name,
        "description": name,
        "tags": ["base"],
        "size": list(size),
        "parts": parts,
        "animations": animations or {},
    }
    os.makedirs(outdir, exist_ok=True)
    write_doc(d, os.path.join(outdir, f"ss-bits-{slug}.json"))
