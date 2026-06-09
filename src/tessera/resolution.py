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
from difflib import SequenceMatcher

# The similarity at/above which two names are asserted to refer to the same
# entity. Named, documented, and tunable on purpose (ADR 0004): the Unit 6
# coverage/ER metric is the revisit trigger for changing it. At 0.85 it merges the
# known typo/umlaut variants while keeping distinct firms that merely share a
# generic token (e.g. "... Logistik GmbH") apart.
DEFAULT_RESOLUTION_THRESHOLD = 0.85


def normalize(name: str) -> str:
    """Fold a name to a comparison key: lowercase, umlaut-fold, alphanumeric only."""
    folded = (
        name.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    return re.sub(r"[^a-z0-9]", "", folded)


def similarity(a: str, b: str) -> float:
    """A deterministic similarity in [0, 1] between two names, over their
    normalized forms. 1.0 means identical once normalized."""
    norm_a, norm_b = normalize(a), normalize(b)
    if not norm_a or not norm_b:
        return 0.0
    return SequenceMatcher(None, norm_a, norm_b).ratio()
