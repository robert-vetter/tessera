"""The recorded measurement: the trust contract survives the *execution* boundary.

Milestone 14 Unit 4 (spec 0101). The execution-level analogue of ``tests/test_boundary``
(M11), ``tests/test_actions_boundary`` (M12), and ``tests/test_payloads_boundary``
(M13): over cases derived from the data (every failed run yields an incident execution;
every PR a pr_summary execution — anti-tautology, ADR 0007), the execution trust
contract is gated in CI.

1. Every **simulated** execution consumed an ``all_grounded`` payload, and its receipt
   is a **lossless** record of it: the receipt's request equals the M13 rendered
   payload's request (method, path, body), and each non-path content slot mirrors
   exactly one of the grounding's claims (same value, same support ids, and the *same*
   verifier verdict, recomputed independently from the grounding — not read from the
   receipt). The default actuator is the simulated one; ``sent`` is false, nothing left.
2. **Faithfulness is 1.0 across the execution boundary**: every slot of every derived
   execution's receipt is verifier-passing — an actuator that recorded a fabricated or
   over-claimed value would fail it.
3. **Nothing executes over ungrounded ground**: a passed/unknown run, an out-of-scope
   question, an incompatible route, and a wrong domain each yield a **withheld** receipt
   — no request, nothing executed, nothing sent.
4. The opt-in **real** path is *earned*: against an injected fake transport,
   ``GithubActuator`` performs a POST **iff** approved and credentialed, and never
   otherwise — ``sent=True`` is provably earned, and the real network is never touched.

Offline and pure-stdlib (it drives the execution layer's simulated actuator + an
injected fake transport, no SDK, no network), so it runs in the gate. Faithfulness stays
the single hard floor; this property is *pinned*, not a new gated metric (the
M11/M12/M13 pattern).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from tessera.agent.execution import (
    GithubActuator,
    execute_action,
    execute_payload,
)
from tessera.agent.grounded import ground
from tessera.agent.payloads import preview_payload
from tessera.devex.knowledge import build_devex_graph, build_github_actions_graph
from tessera.graph import KnowledgeGraph

BuildGraph = Callable[[], KnowledgeGraph]


@dataclass
class _FakeTransport:
    """A recording HTTP stand-in — replicated here (not imported from another test) so
    the boundary check stays independent; the real network is never touched."""

    status: int = 201
    response: dict[str, object] = field(default_factory=lambda: {"number": 1})
    calls: list[str] = field(default_factory=list)

    def post(
        self, url: str, *, headers: dict[str, str], body: dict[str, object]
    ) -> tuple[int, dict[str, object]]:
        self.calls.append(url)
        return self.status, self.response


def _failed_runs(build: BuildGraph) -> list[str]:
    return sorted(
        node.record.id.removeprefix("Run:")
        for node in build().nodes
        if node.kind == "Run" and node.attr("status") == "failed"
    )


def _prs(build: BuildGraph) -> list[str]:
    return sorted(
        node.record.id.removeprefix("PR:")
        for node in build().nodes
        if node.kind == "PR"
    )


def _execution_cases() -> Iterator[tuple[str, str, str]]:
    """(action_kind, domain, question) for every execution the corpus supports: an
    incident per failed run (devex + the real github_actions connector), a PR summary
    per devex PR. Derived from the graphs, so the measurement widens with the data."""
    for run_id in _failed_runs(build_devex_graph):
        yield "incident", "devex", f"Why did run {run_id} fail?"
    for run_id in _failed_runs(build_github_actions_graph):
        yield "incident", "github_actions", f"Why did run {run_id} fail?"
    for pr_id in _prs(build_devex_graph):
        yield "pr_summary", "devex", f"What does {pr_id} change?"


def test_every_simulated_execution_is_grounded_and_a_lossless_receipt() -> None:
    """For every derived case the simulated execution is grounded and sends nothing; the
    receipt's request equals the rendered payload (lossless), its non-path slots project
    the grounding's claims one-for-one (value, support, and the verdict recomputed from
    the grounding), and the {pr} resource traces to the PR record."""
    cases = list(_execution_cases())
    assert cases  # the corpus supports at least one execution
    for kind, domain, question in cases:
        receipt = execute_action(kind, domain, question)
        payload = preview_payload(kind, domain, question)
        grounding = ground(domain, question)
        tag = f"{kind}/{domain}: {question}"

        assert receipt.all_grounded and receipt.simulated, tag
        assert receipt.executed and receipt.sent is False, tag
        assert receipt.actuator == "simulated" and receipt.requires_approval is True, (
            tag
        )

        # Lossless wrt the M13 payload: same wire request, same grounded slots.
        assert (receipt.method, receipt.path, receipt.body) == (
            payload.method,
            payload.path,
            payload.body,
        ), tag
        assert receipt.slots == payload.slots, tag

        # The non-title content slots project the grounding's claims one-for-one, in
        # order (value, support, and the verdict recomputed from the grounding).
        content = [s for s in receipt.slots if s.part in ("title", "body")]
        non_title = [s for s in content if s.role != "title"]
        assert len(non_title) == len(grounding.claims), tag
        for slot, claim in zip(non_title, grounding.claims, strict=True):
            assert slot.value == claim.text, tag
            assert {e.id for e in slot.support} == {e.id for e in claim.support}, tag
            assert slot.verified == claim.verified is True, tag

        # The optional title slot is a verified fragment of grounded evidence.
        claim_texts = {c.text for c in grounding.claims}
        evidence_texts = [e.text for c in grounding.claims for e in c.support]
        for title in (s for s in content if s.role == "title"):
            assert title.value in claim_texts or any(
                title.value in ev for ev in evidence_texts
            ), tag
            assert title.verified, tag

        # The {pr} resource (pr_summary) traces to the subject's PR record.
        for resource in (s for s in receipt.slots if s.part == "path"):
            assert resource.verified, tag
            assert all(e.id.startswith("PR:") for e in resource.support), tag


def test_faithfulness_is_one_across_the_execution_boundary() -> None:
    """The headline gated property: counted over every slot of every derived execution's
    receipt, every slot is verifier-passing — faithfulness 1.0 across the execution
    boundary. An actuator that fabricated or over-claimed a value fails this."""
    total = 0
    verified = 0
    for kind, domain, question in _execution_cases():
        receipt = execute_action(kind, domain, question)
        assert receipt.all_grounded, f"{kind}/{domain}: {question}"
        for slot in receipt.slots:
            total += 1
            verified += 1 if slot.verified else 0
    assert total > 0
    assert verified == total  # faithfulness == 1.0 across the execution boundary


def test_nothing_executes_over_ungrounded_ground() -> None:
    """No action is ever executed on ungrounded ground: a run that passed, an unknown
    run (synthetic and real), an out-of-scope question, an incompatible route, and a
    wrong domain each yield a withheld receipt with no request and nothing sent."""
    passed_run = next(
        node.record.id.removeprefix("Run:")
        for node in build_devex_graph().nodes
        if node.kind == "Run" and node.attr("status") == "passed"
    )
    cases = [
        ("incident", "devex", f"Why did run {passed_run} fail?"),  # it passed
        ("incident", "devex", "Why did run R-9999 fail?"),  # unknown synthetic run
        ("incident", "devex", "What is the capital of France?"),  # out of scope
        (
            "incident",
            "github_actions",
            "Why did run 99999999 fail?",
        ),  # unknown real run
        ("incident", "devex", "What does PR-201 change?"),  # incompatible route
        ("pr_summary", "github_actions", "What does PR-201 change?"),  # wrong domain
    ]
    for kind, domain, question in cases:
        receipt = execute_action(kind, domain, question)
        tag = f"{kind}/{domain}: {question}"
        assert receipt.withheld and not receipt.executed, tag
        assert receipt.sent is False and receipt.simulated is False, tag
        assert not receipt.all_grounded, tag
        assert receipt.slots == (), tag
        assert (receipt.method, receipt.path, receipt.body) == ("", "", {}), tag
        assert receipt.withheld_reason, tag


def test_the_real_path_sends_iff_approved_and_credentialed() -> None:
    """Across the boundary, the opt-in real actuator sends a POST for a grounded payload
    exactly when approved AND credentialed, and never otherwise — the earned, provably-
    failable send. Driven against an injected fake transport; the real network is never
    touched (and this whole property is measured without the SDK)."""
    payload = preview_payload("incident", "devex", "Why did run R-1042 fail?")
    assert payload.all_grounded

    # approved + credentialed -> exactly one send, sent=True is earned.
    sent = _FakeTransport()
    receipt = execute_payload(
        payload,
        actuator=GithubActuator(owner="o", repo="r", token="t", transport=sent),
        approve=True,
    )
    assert receipt.sent and receipt.outcome == "created"
    assert len(sent.calls) == 1

    # missing approval, and missing credential -> no send in either case.
    for approve, token in ((False, "t"), (True, None)):
        fake = _FakeTransport()
        blocked = execute_payload(
            payload,
            actuator=GithubActuator(owner="o", repo="r", token=token, transport=fake),
            approve=approve,
        )
        assert blocked.sent is False and blocked.outcome == "blocked"
        assert fake.calls == []


def test_adr_0005_0006_not_forced_at_the_execution_boundary() -> None:
    """ADR 0005 (LLM-judge) / 0006 (semantic routing) re-examined at the execution
    boundary and recorded NOT forced: every receipt slot's verdict is the same
    structural ``is_supported`` check the eval gates on (no semantic judge crossed the
    boundary), and executing is deterministic dispatch over verifier-passing fields plus
    the ungrounded gate — not LLM generation, not semantic routing. A documentation pin,
    revisited if a measured case forces a trigger."""
    receipt = execute_action("incident", "devex", "Why did run R-1042 fail?")
    assert receipt.all_grounded  # the structural verifier sufficed across the boundary
    assert receipt.simulated and receipt.sent is False
