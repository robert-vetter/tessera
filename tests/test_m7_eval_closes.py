"""The two Milestone-7 gold cases close through the eval answer path (spec 0065).

Both are recorded **offline misses** the batteries measure (devex gold coverage
0.950, github_actions gold coverage 0.833) and **online closes** the embeddings
record (spec 0066). Proven here at the eval level with seeded stubs — the route
answer surfaces the on-call once checkout-svc resolves; the lookup answer
surfaces the de-diluted 404 chunk once a semantic index groups the synonyms.
Faithfulness stays 1.0 at both the miss and the close.
"""

from __future__ import annotations

from collections.abc import Sequence

from tessera.devex.knowledge import SemanticResolver, build_devex_graph, build_devex_kb
from tessera.er_semantic import propose_semantic_resolutions
from tessera.eval.battery import Battery, GoldCase
from tessera.eval.harness import load_gold_set
from tessera.eval.registry import _devex_answer, devex_battery, github_actions_battery
from tessera.graph import Resolution
from tessera.platform.vectors import InMemoryVectorStore


class _Stub:
    name = "stub"

    def __init__(self, axes: list[tuple[str, ...]]) -> None:
        self._axes = axes

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [
            [1.0 if any(k in t.lower() for k in axis) else 0.0 for axis in self._axes]
            for t in texts
        ]


_ER_AXES: list[tuple[str, ...]] = [
    ("checkout",),
    ("payments",),
    ("auth",),
    ("search",),
    ("notif",),
    ("inventory",),
]


def _er_resolver() -> SemanticResolver:
    def resolve(named: list[tuple[str, str]]) -> list[Resolution]:
        return propose_semantic_resolutions(
            named, _Stub(_ER_AXES), InMemoryVectorStore()
        )

    return resolve


def _case(battery: Battery, case_id: str) -> GoldCase:
    return next(c for c in load_gold_set(battery.gold_dir) if c.id == case_id)


# --- the devex ER ownership case (09): route answer ---------------------------


def test_checkout_oncall_case_misses_offline() -> None:
    case = _case(devex_battery(), "09_checkout_oncall_semantic")
    graph, kb = build_devex_graph(), build_devex_kb()  # offline default
    answer = _devex_answer(case, graph, kb, None)
    cited = {rec.id for claim in answer.claims for rec in claim.support}
    assert "Component:SVC-CHK" in cited
    assert "Owner:checkout-svc" not in cited  # the recorded recall miss
    assert answer.is_grounded  # a faithful partial, not a refusal


def test_checkout_oncall_case_closes_with_embedding_resolver() -> None:
    case = _case(devex_battery(), "09_checkout_oncall_semantic")
    graph = build_devex_graph(semantic_resolver=_er_resolver())
    kb = build_devex_kb()
    answer = _devex_answer(case, graph, kb, None)
    cited = {rec.id for claim in answer.claims for rec in claim.support}
    assert set(case.expected_support) <= cited
    rendered = answer.render()
    assert all(fact in rendered for fact in case.expected_facts)


# --- the de-diluted synonymy case (05): lookup answer -------------------------


def test_synonymy_case_expects_the_de_diluted_error_chunk() -> None:
    """gold-05 now cites the isolated 404 cluster (spec 0064), so its online close
    surfaces the actual failure line — the de-dilution, not the run-status row."""
    case = _case(github_actions_battery(), "05_pages_synonymy_lookup")
    assert list(case.expected_support) == ["27285174461.failed:error1"]
    assert "Ensure GitHub Pages has been enabled" in case.expected_facts
