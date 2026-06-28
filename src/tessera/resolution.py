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
from collections import Counter
from collections.abc import Sequence
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


# --- distinctive-stem tokenization -------------------------------------------
#
# A name's *distinctive stem* is the name with its **generic** tokens removed —
# legal forms, universal organizational descriptors, and tokens that are simply
# corpus-frequent. These primitives are shared by two regimes:
#
#   - the deterministic difflib pass (``KnowledgeGraph.resolve_entities``), which
#     gates a merge on a shared distinctive token so a long shared *generic*
#     suffix can no longer collapse distinct firms (spec 0070, ADR 0018), and
#   - the embedding-assisted regime (:mod:`tessera.er_semantic`), which embeds the
#     distinctive stem so abbreviation/synonym variants can still merge (ADR 0016).
#
# They live here (not in ``er_semantic``) precisely because the verifier-reachable
# engine imports them: this module is stdlib-only and embedding-free, so importing
# it never pulls a vector/provider module into the faithfulness verifier's closure
# (the standing leak-guard, ``tests/test_semantic.py``).

# Universal organizational descriptors — generic regardless of corpus frequency,
# because they describe *kind*, not *identity* (unlike a per-entity alias, ADR
# 0010). Kept small and explicit; legal forms are folded in from
# :data:`LEGAL_SUFFIXES`.
ORG_DESCRIPTORS = frozenset(
    {"service", "services", "svc", "svcs", "system", "systems", "platform", "app"}
)

# A token shared across at least this many names is treated as generic (a
# corpus-frequency stoplist, so "Logistik" across four firms becomes generic
# without anyone naming it). Tunable; small by design so single-occurrence
# distinctive stems are never stripped.
DEFAULT_MIN_GENERIC_DF = 3

_TOKEN_SPLIT = re.compile(r"[\s\-_/.,&]+")


def tokenize(name: str) -> list[str]:
    """Split a name into normalized tokens (lowercased, umlaut/diacritic-folded).

    Each token is run through :func:`normalize` so ``"Müller"`` and ``"Mueller"``
    tokenize identically, and empty tokens are dropped. Splitting happens on
    whitespace and the common name separators before normalization collapses each
    token to ``[a-z0-9]``.
    """
    return [tok for raw in _TOKEN_SPLIT.split(name) if (tok := normalize(raw))]


def generic_tokens(
    names: Sequence[str],
    *,
    min_df: int = DEFAULT_MIN_GENERIC_DF,
    descriptors: frozenset[str] = ORG_DESCRIPTORS,
) -> frozenset[str]:
    """The generic-token set for a name corpus: descriptors ∪ legal forms ∪
    tokens whose document frequency across ``names`` is ``>= min_df``.

    Document frequency counts each name once per distinct token (so a token
    repeated within one name is not double-counted). The result is what
    :func:`distinctive_stem` strips away.
    """
    document_frequency: Counter[str] = Counter()
    for name in names:
        document_frequency.update(set(tokenize(name)))
    frequent = {tok for tok, df in document_frequency.items() if df >= min_df}
    return frozenset(descriptors) | frozenset(LEGAL_SUFFIXES) | frozenset(frequent)


def distinctive_stem(name: str, generic: frozenset[str]) -> str:
    """The name reduced to its non-generic tokens, space-joined in order.

    ``""`` when every token is generic — such a name carries no distinctive
    signal and is never proposed for a merge.
    """
    return " ".join(tok for tok in tokenize(name) if tok not in generic)
