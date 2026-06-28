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


# The difflib ratio at/above which two *distinctive stems* count as the same firm
# modulo typos/abbreviations. Named and tunable like
# :data:`DEFAULT_RESOLUTION_THRESHOLD`; the ER precision/recall measurement
# (``tests/test_er_metrics.py``) is its revisit trigger. Spec 0070 / ADR 0018.
DEFAULT_DISTINCTIVE_STEM_THRESHOLD = 0.85

# The maximum character edit distance between two distinctive stems for them to
# still count as a spelling variant of the same firm. The ``stem_threshold`` ratio
# above penalizes a fixed typo more on a SHORT stem ("stein"~"stien" = 0.800), so a
# small absolute bound rescues a single typo in a short head while still vetoing two
# genuinely different heads ("granite"~"pyrite" = 4 edits, "cobalt"~"basalt" = 3).
DEFAULT_MAX_STEM_EDITS = 2

# Tokens generic regardless of corpus: organizational descriptors ∪ legal forms.
# :func:`corpus_generic_tokens` adds the corpus-derived ones on top.
_STATIC_GENERIC = ORG_DESCRIPTORS | frozenset(LEGAL_SUFFIXES)


def significant_tokens(name: str) -> list[str]:
    """Tokenize, dropping single-character tokens (spec 0070).

    A punctuated legal form abbreviates into single-letter tokens — ``G.m.b.H`` →
    ``[g, m, b, h]``, ``A/S`` → ``[a, s]``, ``S.A.R.L`` → ``[s, a, r, l]``. These
    carry no firm identity, but left in they pollute a distinctive stem (so
    ``"Nordwind G.m.b.H"`` would not match its ``"Nordwind Log GmbH"`` variant). The
    gate works over the length-≥ 2 tokens; the full-name `normalize` still folds the
    abbreviation to its legal form elsewhere.
    """
    return [tok for tok in tokenize(name) if len(tok) >= 2]


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance between two short strings (stdlib, deterministic)."""
    if a == b:
        return 0
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb))
            )
        previous = current
    return previous[-1]


def corpus_generic_tokens(
    names: Sequence[str],
    *,
    min_df: int = DEFAULT_MIN_GENERIC_DF,
    threshold: float = DEFAULT_RESOLUTION_THRESHOLD,
) -> frozenset[str]:
    """Tokens that are generic *in this corpus* — the gate's stoplist (spec 0070).

    The static generics (:data:`_STATIC_GENERIC`) plus any token that spans at
    least ``min_df`` **distinct firms**: ``>= min_df`` of the names containing it
    stay mutually dissimilar (below ``threshold``) once that token **and all tokens
    already known to be generic** are removed from each.

    Removing the token before judging similarity is the crux. A shared generic
    suffix makes the firms that share it look similar — ``Granite/Pyrite/Cobalt
    Logistik GmbH`` are pairwise ``>= threshold`` *because of* ``logistik``, so a
    naive document-frequency count would still see ``logistik`` as firm-specific
    (or, worse, mark the genuinely distinctive ``Bayerische`` generic because it
    repeats across one firm's four records). With ``logistik`` removed,
    ``granite`` / ``pyrite`` / … are dissimilar → ``logistik`` spans distinct firms
    → generic. With ``Bayerische`` removed, the four ``Stahlwerke AG`` records are
    still similar → it spans **one** firm → kept distinctive.

    **Iterated to a fixpoint, removing the known generics too.** A *multi-token*
    generic suffix would otherwise defeat a one-token-at-a-time pass: removing
    ``logistik`` from ``Granite Trade Logistik GmbH`` leaves ``trade`` still propping
    similarity, so ``trade`` never reaches ``min_df`` distinct firms. Re-scanning
    with ``logistik`` (and ``gmbh``) already stripped exposes ``granite`` vs
    ``pyrite`` and flags ``trade`` too. The static generics seed the set, and tokens
    are visited in sorted order over a canonicalized name list, so the result is
    independent of ingestion order (a property pinned by test).
    """
    containing: dict[str, list[str]] = {}
    for name in names:
        for token in dict.fromkeys(significant_tokens(name)):
            containing.setdefault(token, []).append(name)
    # Canonical, order-independent traversal (the greedy distinct-firm count below
    # is otherwise sensitive to the order names arrive in).
    for token in containing:
        containing[token] = sorted(containing[token], key=normalize)

    generic = set(_STATIC_GENERIC)
    changed = True
    while changed:  # fixpoint: a newly-generic token can expose another (multi-word)
        changed = False
        for token in sorted(containing):
            if token in generic or len(containing[token]) < min_df:
                continue
            firms: list[str] = []  # representatives of distinct firms (generics gone)
            for name in containing[token]:
                reduced = " ".join(
                    t
                    for t in significant_tokens(name)
                    if t != token and t not in generic
                )
                if all(similarity(reduced, firm) < threshold for firm in firms):
                    firms.append(reduced)
                    if len(firms) >= min_df:
                        generic.add(token)
                        changed = True
                        break
    return frozenset(generic)


def confirm_name_match(
    a: str,
    b: str,
    generic: frozenset[str],
    *,
    stem_threshold: float = DEFAULT_DISTINCTIVE_STEM_THRESHOLD,
    max_stem_edits: int = DEFAULT_MAX_STEM_EDITS,
) -> str | None:
    """Confirm a difflib name match rests on a shared **distinctive** signal, not on
    generic tokens alone — the stem gate that cures the generic-suffix over-merge
    (spec 0070, ADR 0018).

    Called only for pairs the character similarity already accepts
    (``similarity(a, b) >= DEFAULT_RESOLUTION_THRESHOLD``); ``generic`` is the
    corpus stoplist from :func:`corpus_generic_tokens`. Returns a short reason
    fragment to append to the assertion, or ``None`` to **veto** the merge (the
    high full-name similarity was carried by a shared generic suffix → an
    over-merge such as ``Granite`` vs ``Pyrite Logistik GmbH``).

    1. **Shared distinctive token** → confirm. If the two names share any
       non-generic token (the firm's identity head, e.g. ``maple``/``timber``/
       ``schaefer``), they co-refer — robust to a typo or abbreviation elsewhere
       in the name.
    2. **Both distinctive stems empty** → confirm. Both names are made up entirely
       of generic tokens; the character match (already ``>=`` the threshold) rests
       on identical/near-identical generic forms (e.g. ``"Service GmbH"`` twice) —
       a fully-generic variant merge, confirmed rather than silently dropped.
    3. Otherwise compare the **distinctive stems** (names minus generic tokens):
       confirm when their similarity is ``>= stem_threshold`` OR their character
       edit distance is ``<= max_stem_edits``. The edit-distance fallback rescues a
       single typo in a short head (``stein``~``stien``: ratio 0.800 but 2 edits)
       that stripping the shared generic context would otherwise amplify below the
       ratio threshold; two genuinely different heads still veto (``granite``~
       ``pyrite``: 4 edits; ``cobalt``~``basalt``: 3 edits).
    """
    ta, tb = significant_tokens(a), significant_tokens(b)
    shared_distinctive = [t for t in ta if t in set(tb) and t not in generic]
    if shared_distinctive:
        return f"shared distinctive token {shared_distinctive[0]!r}"

    stem_a = " ".join(t for t in ta if t not in generic)
    stem_b = " ".join(t for t in tb if t not in generic)
    if not stem_a and not stem_b:
        return "fully-generic names (no distinctive signal)"
    if not stem_a or not stem_b:
        return None

    stem_sim = similarity(stem_a, stem_b)
    if stem_sim >= stem_threshold:
        return (
            f"near-identical distinctive stems {stem_a!r} ~ {stem_b!r} "
            f"(similarity {stem_sim:.3f})"
        )
    edits = _edit_distance(stem_a, stem_b)
    if edits <= max_stem_edits:
        return f"distinctive stems {stem_a!r} ~ {stem_b!r} ({edits} edit(s) apart)"
    return None
