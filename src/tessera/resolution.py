"""Deterministic, explainable name matching for entity resolution.

No embeddings or ML (consistent with ADR 0003 / ADR 0004): names are normalized
(umlaut-fold, casefold, reduced to alphanumerics) and compared with a
deterministic similarity ratio. The score is used directly as a **confidence
proxy** — it is not a calibrated probability.

Matching is **name-only** by deliberate slice simplification (see ADR 0004);
multi-field matching (name + address) is future work, not built here.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# The similarity at/above which two names are asserted to refer to the same
# entity. Named, documented, and tunable on purpose (ADR 0004): the Unit 6
# coverage/ER metric is the revisit trigger for changing it. At 0.85 it merges the
# known typo/umlaut variants while keeping distinct firms that merely share a
# generic token (e.g. "... Logistik GmbH") apart.
DEFAULT_RESOLUTION_THRESHOLD = 0.85


def normalize(name: str) -> str:
    """Fold a name to a comparison key: lowercase, umlaut-fold, diacritic-fold,
    alphanumeric only.

    Order matters: German umlauts fold to their conventional digraphs FIRST
    (``ü``→``ue`` — the data's Müller/Mueller variants depend on it); all other
    diacritics then fold to their base letter via NFKD (``è``→``e``), instead
    of being deleted by the alphanumeric filter — deletion is how
    ``"Lumière"`` failed to match ``"Lumiere"`` (spec 0024)."""
    folded = (
        name.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    decomposed = unicodedata.normalize("NFKD", folded)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", stripped)


# Legal-form suffixes (normalized forms), longest first so e.g. "incorporated"
# wins over "inc". Used by document-mention linking to tolerate references that
# drop the legal form ("Lumière Énergie" for "Lumière Énergie S.A.R.L.").
LEGAL_SUFFIXES = (
    "incorporated",
    "limited",
    "gmbh",
    "sarl",
    "corp",
    "inc",
    "ltd",
    "ohg",
    "plc",
    "spa",
    "ag",
    "as",
    "sa",
)

# A suffix-stripped key must keep at least this many characters to count as a
# usable reference (guards against generic stems matching everywhere).
MIN_STRIPPED_LENGTH = 8


def strip_legal_suffix(name: str) -> str | None:
    """The normalized name with its trailing legal form removed, when that
    leaves a usably long key; ``None`` otherwise."""
    norm = normalize(name)
    for suffix in LEGAL_SUFFIXES:
        if norm.endswith(suffix):
            stem = norm[: -len(suffix)]
            if len(stem) >= MIN_STRIPPED_LENGTH:
                return stem
            return None
    return None


def similarity(a: str, b: str) -> float:
    """A deterministic similarity in [0, 1] between two names, over their
    normalized forms. 1.0 means identical once normalized."""
    norm_a, norm_b = normalize(a), normalize(b)
    if not norm_a or not norm_b:
        return 0.0
    return SequenceMatcher(None, norm_a, norm_b).ratio()
