"""The recorded measurement: the trust contract survives the *payload* boundary.

Milestone 13 Unit 4 (spec 0096). The payload-level analogue of ``tests/test_boundary``
(M11) and ``tests/test_actions_boundary`` (M12): over cases derived from the data (every
failed run yields an incident payload; every PR a pr_summary payload — anti-tautology,
ADR 0007), three properties are gated in CI.

1. Every rendered payload is **field-grounded and lossless**: each non-path content slot
   mirrors exactly one of the proposal's verified fields (same value, same support ids,
   and the *same* verifier verdict, recomputed independently from the grounding — not
   read from the payload); the ``{pr}`` resource slot traces to the subject's PR record.
2. **Faithfulness is 1.0 across the payload boundary**: every content slot of every
   derived payload is verifier-passing, and the wire request is **byte-reconstructable**
   from the verified fields plus the declared scaffolding — an independent rebuild, so a
   fabricated, over-claimed, or smuggled value fails it.
3. A withheld payload — passed/unknown run, out-of-scope, incompatible route, wrong
   domain — carries **no request**: a payload is never rendered over ungrounded ground.

Offline and pure-stdlib (it drives ``draft_action`` + ``render_payload``, no SDK), so it
runs in the gate. Faithfulness stays the single hard floor; this property is *pinned*,
not a new gated metric (the M11/M12 pattern).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator

from tessera.agent.actions import ActionProposal, draft_action
from tessera.agent.grounded import ground
from tessera.agent.payloads import preview_payload, render_payload
from tessera.devex.knowledge import build_devex_graph, build_github_actions_graph
from tessera.graph import KnowledgeGraph

BuildGraph = Callable[[], KnowledgeGraph]

# An INDEPENDENT copy of the renderer's declared body scaffolding (as in
# tests/test_payloads); the boundary rebuilds the wire request from the verified field
# VALUES alone, so any token added beyond grounded values + this declared scaffolding
# makes the rebuild differ. Replicated, not imported, so the check stays independent.
# The scaffolding includes the fence rule (spec 0109, audit B4): a fence is strictly
# longer than any backtick run inside the value, minimum 3.
_LABELS = {
    "title": "Summary",
    "failing_run": "Failing run",
    "log": "Error log",
    "prior_occurrence": "Prior occurrence",
    "documented_incident": "Documented incident",
    "referenced_ticket": "Referenced ticket",
    "resolving_change": "Resolved by",
    "referenced_pull_request": "Pull request",
    "pull_request": "Pull request",
    "code_change": "Code change",
    "motivating_ticket": "Motivating ticket",
}
_FENCED = {"log", "code_change"}


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


def _payload_cases() -> Iterator[tuple[str, str, str]]:
    """(action_kind, domain, question) for every payload the corpus supports: an
    incident per failed run (devex + the real github_actions connector), a PR summary
    per devex PR. Derived from the graphs, so the measurement widens with the data."""
    for run_id in _failed_runs(build_devex_graph):
        yield "incident", "devex", f"Why did run {run_id} fail?"
    for run_id in _failed_runs(build_github_actions_graph):
        yield "incident", "github_actions", f"Why did run {run_id} fail?"
    for pr_id in _prs(build_devex_graph):
        yield "pr_summary", "devex", f"What does {pr_id} change?"


def _expected_request(proposal: ActionProposal) -> tuple[str, str, dict[str, object]]:
    """Rebuild the exact wire (method, path, body) from the proposal's verified fields +
    the declared scaffolding, independently of the renderer's own assembly."""

    def fence(value: str) -> str:
        # Independent copy of the declared fence rule; the non-degenerate pin (a value
        # actually carrying backtick runs) lives in tests/test_payloads.py's
        # hostile-content test — today's corpus values are backtick-free, so this
        # degenerates to ``` for every derived case.
        longest = max((len(run) for run in re.findall(r"`+", value)), default=0)
        return "`" * max(3, longest + 1)

    def section(name: str, value: str) -> str:
        label = _LABELS[name]
        if name in _FENCED:
            mark = fence(value)
            return f"## {label}\n{mark}\n{value}\n{mark}"
        return f"## {label}\n{value}"

    if proposal.kind == "incident":
        title = next(f for f in proposal.fields if f.name == "title").value
        body_sections = [
            section(f.name, f.value) for f in proposal.fields if f.name != "title"
        ]
        body: dict[str, object] = {
            "title": title,
            "body": "\n\n".join(body_sections),
            "labels": ["incident"],
        }
        return "POST", "/repos/{owner}/{repo}/issues", body
    pr_field = next(f for f in proposal.fields if f.name == "pull_request")
    pr = next(e.id for e in pr_field.support if e.id.startswith("PR:")).removeprefix(
        "PR:"
    )
    body_sections = [section(f.name, f.value) for f in proposal.fields]
    return (
        "POST",
        f"/repos/{{owner}}/{{repo}}/issues/{pr}/comments",
        {"body": "\n\n".join(body_sections)},
    )


def test_every_rendered_payload_is_field_grounded_and_lossless() -> None:
    """For every derived case the payload is rendered + all_grounded, every non-path
    slot projects exactly one grounded claim one-for-one (value, support, and the
    verdict recomputed from the grounding), the {pr} resource traces to the PR record,
    and the wire request is byte-identical to an independent rebuild — nothing added."""
    cases = list(_payload_cases())
    assert cases  # the corpus supports at least one payload
    for kind, domain, question in cases:
        proposal = draft_action(kind, domain, question)
        grounding = ground(domain, question)
        payload = render_payload(proposal)
        tag = f"{kind}/{domain}: {question}"

        assert payload.rendered and payload.all_grounded, tag
        assert payload.sent is False and payload.requires_approval is True, tag

        # Every content slot mirrors a proposal field (payload lossless wrt proposal).
        content = [s for s in payload.slots if s.part in ("title", "body")]
        assert len(content) == len(proposal.fields), tag

        # The non-title content slots project the grounding's claims one-for-one, in
        # order (value, support, and the verdict recomputed from the grounding).
        non_title = [s for s in content if s.role != "title"]
        assert len(non_title) == len(grounding.claims), tag
        for slot, claim in zip(non_title, grounding.claims, strict=True):
            assert slot.value == claim.text, tag
            assert {e.id for e in slot.support} == {e.id for e in claim.support}, tag
            assert slot.verified == claim.verified is True, tag

        # The optional title slot is a verified fragment of grounded evidence (a lifted
        # error line / the PR's quoted title) — the M12 title property, carried through.
        claim_texts = {c.text for c in grounding.claims}
        evidence_texts = [e.text for c in grounding.claims for e in c.support]
        for title in (s for s in content if s.role == "title"):
            assert title.value in claim_texts or any(
                title.value in ev for ev in evidence_texts
            ), tag
            assert title.verified, tag

        # The {pr} resource (pr_summary) is grounded in the subject's PR record.
        for resource in (s for s in payload.slots if s.part == "path"):
            assert resource.verified, tag
            assert resource.value in payload.path, tag
            assert all(e.id.startswith("PR:") for e in resource.support), tag

        # The whole wire request adds nothing beyond the verified fields + scaffolding.
        method, path, body = _expected_request(proposal)
        assert (payload.method, payload.path, payload.body) == (method, path, body), tag


def test_faithfulness_is_one_across_the_payload_boundary() -> None:
    """The headline gated property: counted over every content slot of every derived
    payload, every slot is verifier-passing — faithfulness 1.0 across the payload
    boundary. A renderer that fabricated or over-claimed a value fails this."""
    total = 0
    verified = 0
    for kind, domain, question in _payload_cases():
        payload = render_payload(draft_action(kind, domain, question))
        assert payload.rendered, f"{kind}/{domain}: {question}"
        for slot in payload.slots:
            total += 1
            verified += 1 if slot.verified else 0
    assert total > 0
    assert verified == total  # faithfulness == 1.0 across the payload boundary


def test_a_withheld_payload_carries_no_request_across_the_boundary() -> None:
    """No payload is ever rendered on ungrounded ground: a run that passed, an unknown
    run (synthetic and real), an out-of-scope question, an incompatible route, and a
    wrong domain each yield a withheld payload with no request."""
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
        payload = preview_payload(kind, domain, question)
        tag = f"{kind}/{domain}: {question}"
        assert not payload.rendered and not payload.all_grounded, tag
        assert payload.sent is False, tag
        assert payload.slots == (), tag
        assert (payload.method, payload.path, payload.body) == ("", "", {}), tag
        assert payload.withheld_reason, tag


def test_adr_0005_0006_not_forced_at_the_payload_boundary() -> None:
    """ADR 0005 (LLM-judge) / 0006 (semantic routing) re-examined at the payload
    boundary and recorded NOT forced: every slot's verdict is the same structural
    ``is_supported`` check the eval gates on (no semantic judge crossed the boundary),
    and rendering is deterministic templating over verifier-passing fields — not LLM
    generation, not semantic routing. A documentation pin — revisited if a measured
    case forces a trigger."""
    payload = render_payload(
        draft_action("incident", "devex", "Why did run R-1042 fail?")
    )
    assert payload.all_grounded  # the structural verifier sufficed across the boundary
