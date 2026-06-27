"""Semantic retrieval (spec 0054 / ADR 0015): the embed→KNN→record mechanism
bridges vocabulary BM25 cannot, the fallback stays lexical without embeddings,
and the faithfulness verifier imports no embedding module (the standing
invariant).

The stub embedder is a keyword-axis toy — it proves the *mechanism* and that a
model placing synonyms near each other would retrieve the right evidence. The
honest closure of the synonymy is the recorded online run (spec 0057), not this
test.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence

from tessera.grounding import EvidenceRecord, KnowledgeBase, Locator, Origin
from tessera.platform.config import load_config
from tessera.platform.vectors import InMemoryVectorStore
from tessera.retrieval import retrieve
from tessera.semantic import (
    build_semantic_index,
    semantic_or_lexical,
)


class StubEmbeddings:
    """Deterministic keyword-axis embedder — no network. Each axis is a concept;
    a text's vector marks which concepts it mentions, so synonymous phrasings
    that share no lexical token still land on the same axis."""

    name = "stub"

    def __init__(self, axes: list[tuple[str, ...]]) -> None:
        self._axes = axes

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [
            [
                1.0 if any(keyword in text.lower() for keyword in axis) else 0.0
                for axis in self._axes
            ]
            for text in texts
        ]


_AXES = [
    ("not found", "404", "pages has been enabled", "pages not"),  # Pages-deploy
    ("timeout", "timed out"),  # distractor
    ("permission", "denied", "forbidden"),  # distractor
]


def _rec(rid: str, text: str) -> EvidenceRecord:
    return EvidenceRecord(
        id=rid,
        origin=Origin(
            source=f"specimen/{rid}.log",
            locator=Locator(kind="log-span", parts=(("chunk", "1"),)),
            ingested_at="2026-06-27",
        ),
        text=text,
    )


def _synonymy_records() -> tuple[EvidenceRecord, ...]:
    # a/b/c are three surface forms of ONE root cause that share no lexical token
    # (the real ADR 0010 specimen); d/e are unrelated distractors.
    return (
        _rec("a", "HttpError: Not Found"),
        _rec("b", "status: 404"),
        _rec("c", "Ensure GitHub Pages has been enabled"),
        _rec("d", "Connection timed out after 30s"),
        _rec("e", "Permission denied (publickey)"),
    )


def test_semantic_bridges_synonyms_that_lexical_misses() -> None:
    records = _synonymy_records()
    kb = KnowledgeBase(records=records)
    index = build_semantic_index(
        records,
        config=load_config(env={}),
        provider=StubEmbeddings(_AXES),
        store=InMemoryVectorStore(),
    )
    assert index is not None

    question = "why did the deploy return 404"
    semantic_ids = {r.id for r, _ in index.retrieve(question, k=3)}
    assert semantic_ids == {"a", "b", "c"}  # all three forms surfaced together

    # Lexical BM25 can only reach the form that literally shares the token "404".
    lexical_ids = {r.id for r, score in retrieve(question, kb, k=5) if score > 0}
    assert "b" in lexical_ids
    assert "a" not in lexical_ids and "c" not in lexical_ids


def test_semantic_or_lexical_falls_back_to_bm25_without_index() -> None:
    records = _synonymy_records()
    kb = KnowledgeBase(records=records)
    # No index → identical to the deterministic lexical path (ADR 0003).
    assert semantic_or_lexical("status 404", kb, index=None) == retrieve(
        "status 404", kb, 5
    )


def test_semantic_or_lexical_uses_index_when_present() -> None:
    records = _synonymy_records()
    kb = KnowledgeBase(records=records)
    index = build_semantic_index(
        records,
        config=load_config(env={}),
        provider=StubEmbeddings(_AXES),
        store=InMemoryVectorStore(),
    )
    hits = semantic_or_lexical("not found error", kb, k=3, index=index)
    assert {r.id for r, _ in hits} == {"a", "b", "c"}


def test_build_semantic_index_is_none_in_local_mode() -> None:
    records = (_rec("a", "anything"),)
    assert build_semantic_index(records, config=load_config(env={})) is None


def test_metrics_verifier_imports_no_embedding_module() -> None:
    """Standing invariant: faithfulness is structural. Importing the verifier
    must not pull any embedding/vector/provider module — a 1.0 can never be
    produced by a model. Run in a subprocess so other tests' imports don't
    pollute the check."""
    code = (
        "import sys, tessera.eval.metrics; "
        "banned = {"
        "'tessera.semantic', "
        "'tessera.platform.vectors', "
        "'tessera.platform.providers'"
        "}; "
        "leaked = banned & set(sys.modules); "
        "assert not leaked, sorted(leaked)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
