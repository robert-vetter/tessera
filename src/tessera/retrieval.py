"""Lexical retrieval over ingested evidence, and the answer it produces.

Replaces the Phase-0 hand-authored question-to-claim map with a real retriever:
given a question, score every :class:`~tessera.grounding.EvidenceRecord` in the
knowledge base by lexical relevance (Okapi BM25) and build the answer **from** the
top matches — across both modalities, since structured rows and document chunks
are just records here. When nothing is relevant enough, refuse.

It is **lexical-first and deterministic** — pure stdlib, no model, no network (see
``docs/adr/0003-*``). A surfaced claim's text *is* the evidence snippet; the
system retrieves and sources evidence, it does not synthesise prose or compute
aggregates (that is multi-step reasoning, Phase 2). Resolving entity *variants*
("Müller" vs "Mueller") to one identity is likewise not the retriever's job — it
belongs to the graph / entity-resolution layer (Unit 4).
"""

from __future__ import annotations

import math
import re
from collections import Counter

from tessera.grounding import (
    REFUSAL_MESSAGE,
    Answer,
    Claim,
    EvidenceRecord,
    KnowledgeBase,
)

# A small, deliberately minimal stop list — enough to stop common words from
# creating spurious matches, without a heavyweight NLP dependency.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "do",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "was",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
    }
)

# BM25 parameters (Okapi defaults).
_K1 = 1.5
_B = 0.75


def _tokenize(text: str) -> list[str]:
    """Casefold, umlaut-fold, split to alphanumeric tokens, drop stop words, and
    crudely fold a trailing plural/verb ``s`` (``orders``->``order``,
    ``renews``->``renew``). This is intentionally *not* a real stemmer — just
    enough morphology to bridge obvious surface variants."""
    folded = (
        text.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    tokens: list[str] = []
    for token in re.findall(r"[a-z0-9]+", folded):
        if len(token) < 2 or token in _STOPWORDS:
            # Drop single characters (e.g. the "s" from "Acme's" or "A/S"); they
            # carry no retrieval signal and create spurious matches.
            continue
        if len(token) > 3 and token.endswith("s"):
            token = token[:-1]
        tokens.append(token)
    return tokens


def retrieve(
    question: str, kb: KnowledgeBase, k: int = 5
) -> list[tuple[EvidenceRecord, float]]:
    """Return up to ``k`` records most relevant to ``question``, by BM25 score.

    Only records that actually share a content token with the question (score > 0)
    are returned, so an unrelated question yields nothing. Deterministic: ties
    break by record id.
    """
    query = _tokenize(question)
    if not query:
        return []

    tokenized = [_tokenize(record.text) for record in kb.records]
    n_docs = len(tokenized)
    avg_len = sum(len(doc) for doc in tokenized) / n_docs if n_docs else 0.0
    if avg_len == 0.0:
        return []

    doc_freq: dict[str, int] = {}
    for doc in tokenized:
        for term in set(doc):
            doc_freq[term] = doc_freq.get(term, 0) + 1

    def idf(term: str) -> float:
        n = doc_freq.get(term, 0)
        # +1 keeps idf non-negative even for very common terms.
        return math.log(1 + (n_docs - n + 0.5) / (n + 0.5))

    scored: list[tuple[EvidenceRecord, float]] = []
    for record, doc in zip(kb.records, tokenized, strict=True):
        if not doc:
            scored.append((record, 0.0))
            continue
        freqs = Counter(doc)
        length = len(doc)
        score = 0.0
        for term in query:
            freq = freqs.get(term, 0)
            if not freq:
                continue
            denom = freq + _K1 * (1 - _B + _B * length / avg_len)
            score += idf(term) * (freq * (_K1 + 1)) / denom
        scored.append((record, score))

    scored.sort(key=lambda pair: (-pair[1], pair[0].id))
    return [(record, score) for record, score in scored if score > 0][:k]


def answer_over(question: str, hits: list[tuple[EvidenceRecord, float]]) -> Answer:
    """Build a grounded answer from already-retrieved ``(record, score)`` hits.

    One claim per record (its snippet, traced to its origin); a principled
    refusal if nothing was retrieved. Factored out so the same claim-building +
    refusal logic serves both the lexical path (below) and the semantic path
    (``tessera.semantic.semantic_or_lexical``) — the *retrieval* differs, the
    answer shape and its provenance do not.
    """
    if not hits:
        return Answer(question=question, claims=(), refusal=REFUSAL_MESSAGE)
    claims = tuple(Claim(text=record.text, support=(record,)) for record, _ in hits)
    return Answer(question=question, claims=claims, refusal=None)


def answer(question: str, kb: KnowledgeBase, *, k: int = 5) -> Answer:
    """Answer ``question`` by surfacing the lexically retrieved evidence, sourced.

    The deterministic, offline default (ADR 0003): retrieve by BM25, then build
    the grounded answer. Behaviour-identical to before the ``answer_over`` split.
    """
    return answer_over(question, retrieve(question, kb, k))
