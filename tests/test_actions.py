"""Tests for the grounded-action layer (Milestone 12 Unit 3, spec 0089, ADR 0023).

These pin the propose-and-approve contract an MCP server (Unit 4) will transport: an
action is drafted *only* from a verifier-checked grounding; every field traces to a
verifier-passing claim and is itself re-verified (and the check is *provably failable*);
an incompatible or refused grounding is carried as a refusal, never a fabricated action;
the propose-and-approve contract (requires_approval / executed) is explicit; and the
serialized proposal round-trips through JSON deterministically.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from tessera.agent.actions import (
    ActionProposal,
    available_action_names,
    available_actions,
    draft_action,
)
from tessera.agent.grounded import ground
from tessera.devex.knowledge import build_github_actions_graph


def test_available_actions_describe_domains_and_route() -> None:
    names = available_action_names()
    assert names == ("incident", "pr_summary")
    catalog = {a["name"]: a for a in available_actions()}
    assert catalog["incident"]["from_route"] == "rca"
    assert catalog["incident"]["domains"] == ["devex", "github_actions"]
    assert catalog["pr_summary"]["from_route"] == "summary"
    assert catalog["pr_summary"]["domains"] == ["devex"]
    for action in available_actions():
        assert len(str(action["description"])) > 40


def test_unknown_action_raises() -> None:
    with pytest.raises(ValueError, match="unknown action"):
        draft_action("delete_everything", "devex", "anything")


def test_incident_from_rca_is_fully_grounded() -> None:
    """An incident drafted from a failed run's RCA: every field verified, the
    propose-and-approve contract set, and the action's facts mirror the grounding."""
    proposal = draft_action(
        "incident", "devex", "Why did run R-1042 fail, and has this happened before?"
    )
    assert isinstance(proposal, ActionProposal)
    assert proposal.grounded and not proposal.refused
    assert proposal.route_kind == "rca"
    assert proposal.all_grounded  # every field passed the boundary verifier
    assert proposal.requires_approval is True
    assert proposal.executed is False
    roles = {f.name for f in proposal.fields}
    # The full action skeleton, role-labeled from the engine's claim grammar — every
    # specific role pinned, so a _role regression that silently demotes one to the
    # catch-all "log" fails HERE (the verifier only checks faithfulness, never the
    # role name).
    assert {
        "failing_run",
        "log",
        "prior_occurrence",
        "documented_incident",
        "referenced_ticket",
        "resolving_change",
        "referenced_pull_request",
        "code_change",
    } <= roles
    # Spot-check one added role: its value carries the engine's grammar marker verbatim.
    resolving = next(f for f in proposal.fields if f.name == "resolving_change")
    assert resolving.value.startswith("Resolved by:")
    # The title is the specific error signature, lifted verbatim from the log.
    title = next(f for f in proposal.fields if f.name == "title")
    assert title.value == "TimeoutError: connection to payments-db timed out after 30s"
    assert title.verified
    for field in proposal.fields:
        assert field.verified
        assert field.support  # every field carries inline provenance


def test_every_field_value_traces_to_a_verified_claim() -> None:
    """Field-grounding reduces to claim-faithfulness: each field's value is either a
    grounded claim's exact text or a verbatim fragment of its evidence — never an
    introduced token. Checked against the engine grounding directly."""
    question = "Why did run R-1042 fail, and has this happened before?"
    grounding = ground("devex", question)
    claim_texts = {c.text for c in grounding.claims}
    evidence_texts = [e.text for c in grounding.claims for e in c.support]
    proposal = draft_action("incident", "devex", question)
    for field in proposal.fields:
        is_claim = field.value in claim_texts
        is_fragment = any(field.value in text for text in evidence_texts)
        assert is_claim or is_fragment, f"{field.name}: {field.value!r} not grounded"


def test_pr_summary_from_change_is_fully_grounded() -> None:
    proposal = draft_action("pr_summary", "devex", "What does PR-201 change?")
    assert proposal.grounded and proposal.all_grounded
    assert proposal.route_kind == "summary"
    roles = [f.name for f in proposal.fields]
    assert "pull_request" in roles
    assert roles.count("code_change") >= 1  # the diff hunks
    assert "motivating_ticket" in roles
    title = next(f for f in proposal.fields if f.name == "title")
    assert title.value == "Add retry with backoff to payments-db client"
    assert title.verified


def test_incident_from_real_github_actions() -> None:
    """The same incident drafter serves the real connector — GitHub Actions data is
    CI data (ADR 0014), so a failed real run drafts a grounded incident too."""
    graph = build_github_actions_graph()
    run_id = next(
        node.record.id.removeprefix("Run:")
        for node in graph.nodes
        if node.kind == "Run" and node.attr("status") == "failed"
    )
    proposal = draft_action("incident", "github_actions", f"Why did run {run_id} fail?")
    assert proposal.grounded and proposal.all_grounded
    assert {f.name for f in proposal.fields} >= {"failing_run", "log"}


def test_refused_grounding_is_carried_not_drafted() -> None:
    """A run that passed / an unknown run / an out-of-scope question grounds to a
    refusal; the action carries it and proposes nothing (ADR 0023) — over the
    synthetic devex corpus AND the real github_actions connector (a distinct
    GroundedDomain with its own snapshot build, so the property is pinned there too)."""
    for domain, question in (
        ("devex", "Why did run R-9999 fail?"),  # unknown synthetic run
        ("devex", "What is the capital of France?"),  # out of scope
        ("github_actions", "Why did run 99999999 fail?"),  # unknown real run
        ("github_actions", "What is the capital of France?"),  # out of scope (real)
    ):
        proposal = draft_action("incident", domain, question)
        assert proposal.refused and not proposal.grounded, (domain, question)
        assert proposal.refusal
        assert proposal.fields == ()
        assert not proposal.all_grounded


def test_incompatible_route_is_refused_not_drafted() -> None:
    """Asking for an incident from a PR question (a 'summary' route, not 'rca') is
    refused with a precise reason — never a mis-drafted action."""
    proposal = draft_action("incident", "devex", "What does PR-201 change?")
    assert proposal.refused and not proposal.grounded
    assert "routed to 'summary'" in (proposal.refusal or "")
    assert proposal.fields == ()


def test_wrong_domain_is_refused() -> None:
    proposal = draft_action("pr_summary", "github_actions", "What does PR-201 change?")
    assert proposal.refused
    assert "applies to domain(s)" in (proposal.refusal or "")
    assert proposal.fields == ()


def test_unsupported_field_is_caught_provably_failable() -> None:
    """The field verifier is provably able to fail: a field whose value introduces a
    token absent from its (verifier-passing) source claim's evidence reads
    verified=False. This is the action-level analogue of ADR 0005's injected
    unfaithful claim — a fully-grounded proposal is earned, not tautological."""
    from tessera.agent.actions import _field

    grounding = ground("devex", "Why did run R-1042 fail?")
    real_claim = grounding.claims[0]  # a verified claim
    # An honest field (value == the claim's text) verifies.
    assert _field("failing_run", real_claim.text, real_claim).verified
    # A field that fabricates content its evidence does not support does NOT.
    tampered = _field(
        "failing_run", real_claim.text + " and the database was deleted", real_claim
    )
    assert not tampered.verified


def test_field_verifier_is_per_record_not_concatenated() -> None:
    """The field's containment check mirrors the engine's ``is_supported`` exactly —
    per cited record, not over a concatenation of all of them. A value that exists in
    NO single cited record but only spans the *seam* between two reads verified=False
    (a joined-evidence check would have let it through — the closed gap); and a value
    empty after normalization reads False too (the bool(normalize) guard)."""
    from tessera.agent.actions import _field
    from tessera.agent.grounded import GroundedClaim, GroundedEvidence

    a = GroundedEvidence("A", "s", "k", (), "t", "alpha beta")
    b = GroundedEvidence("B", "s", "k", (), "t", "gamma delta")
    claim = GroundedClaim(text="alpha beta\ngamma delta", verified=True, support=(a, b))
    # A fragment contained in one cited record verifies.
    assert _field("x", "beta", claim).verified
    assert _field("x", "gamma", claim).verified
    # A value spanning the seam between two records (a fragment of NEITHER) does not:
    # normalize("beta gamma") == "betagamma" is a substring of the concatenation but of
    # neither record alone — the old joined check passed it, the per-record check fails.
    assert not _field("x", "beta gamma", claim).verified
    # A value empty after normalization (punctuation/whitespace only) does not.
    assert not _field("x", "   ", claim).verified
    assert not _field("x", "...", claim).verified


def test_partial_grounding_surfaces_unverified_field_not_dropped() -> None:
    """The honest partial state: if a grounding carried a claim the boundary verifier
    rejected, the field is surfaced with verified=False (not dropped, not refused over),
    ``grounded`` stays True, and ``all_grounded`` — the earned action-level guarantee —
    is False. Pins that 'every field traces to a verifier-passing claim' is enforced by
    ``all_grounded``, not by withholding the proposal."""
    from tessera.agent.actions import _CATALOG, ActionProposal, _draft_fields
    from tessera.agent.grounded import GroundedClaim, GroundedEvidence, GroundedResult

    ev = GroundedEvidence(
        "Run:R-1", "runs", "table_row", (), "2026-01-01", "Run R-1 failed."
    )
    good = GroundedClaim(text="Run R-1 failed.", verified=True, support=(ev,))
    # A claim the live verifier rejected (verified=False) but the grounding kept.
    bad = GroundedClaim(
        text="Recurring failure: \"X\" appears in 'a' and 'b'.",
        verified=False,
        support=(ev,),
    )
    result = GroundedResult(
        domain="devex",
        question="q",
        route_kind="rca",
        route_reason="r",
        grounded=True,
        refused=False,
        refusal=None,
        claims=(good, bad),
    )
    fields = _draft_fields(_CATALOG["incident"], result)
    flags = {f.name: f.verified for f in fields}
    assert flags["failing_run"] is True
    assert flags["prior_occurrence"] is False  # surfaced, not dropped
    proposal = ActionProposal(
        kind="incident",
        domain="devex",
        question="q",
        route_kind="rca",
        route_reason="r",
        grounded=True,
        refused=False,
        refusal=None,
        fields=tuple(fields),
    )
    assert proposal.grounded and not proposal.refused
    assert proposal.all_grounded is False
    assert proposal.to_dict()["all_grounded"] is False


def test_all_grounded_false_when_grounded_but_no_fields() -> None:
    """The all_grounded guard's bool(self.fields) term: a grounded proposal with zero
    fields is not 'fully grounded' — guarding the vacuous ``all([]) is True`` trap that
    an MCP consumer (Unit 4) would otherwise read as a clean draft."""
    from tessera.agent.actions import ActionProposal

    proposal = ActionProposal(
        kind="incident",
        domain="devex",
        question="q",
        route_kind="rca",
        route_reason="r",
        grounded=True,
        refused=False,
        refusal=None,
        fields=(),
    )
    assert proposal.all_grounded is False
    assert proposal.to_dict()["all_grounded"] is False


def test_to_dict_round_trips_through_json() -> None:
    payload = draft_action("incident", "devex", "Why did run R-1042 fail?").to_dict()
    restored = json.loads(json.dumps(payload))
    assert restored == payload
    assert restored["requires_approval"] is True
    assert restored["executed"] is False
    assert restored["all_grounded"] is True
    field0 = restored["fields"][0]
    assert {"name", "value", "verified", "support"} <= set(field0)


def test_refusal_to_dict_carries_reason_and_no_fields() -> None:
    payload = draft_action("incident", "devex", "Why did run R-9999 fail?").to_dict()
    assert payload["refused"] is True
    assert payload["grounded"] is False
    assert payload["all_grounded"] is False
    assert payload["refusal"]
    assert payload["fields"] == []


def test_draft_action_is_deterministic_across_hash_seeds() -> None:
    """The serialized proposal must be byte-stable regardless of PYTHONHASHSEED — for
    EVERY drafting shape: incident over synthetic devex AND the real github_actions
    connector, and pr_summary. A claim's co-supporting records are a set sorted at the
    grounding boundary, and field order is the deterministic claim order. Run in
    subprocesses to vary the seed."""
    gh_run = next(
        node.record.id.removeprefix("Run:")
        for node in build_github_actions_graph().nodes
        if node.kind == "Run" and node.attr("status") == "failed"
    )
    cases = (
        ("incident", "devex", "Why did run R-1042 fail, and has this happened before?"),
        ("pr_summary", "devex", "What does PR-201 change?"),
        ("incident", "github_actions", f"Why did run {gh_run} fail?"),
    )

    def run(kind: str, dom: str, question: str, seed: str) -> str:
        code = (
            "import json; from tessera.agent.actions import draft_action;"
            f"print(json.dumps(draft_action({kind!r}, {dom!r}, {question!r}).to_dict(),"
            " sort_keys=True))"
        )
        env = {**os.environ, "PYTHONHASHSEED": seed}
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, env=env
        )
        assert result.returncode == 0, result.stderr
        return result.stdout

    for kind, dom, question in cases:
        outputs = {run(kind, dom, question, seed) for seed in ("0", "1", "2026")}
        assert len(outputs) == 1, f"{kind}/{dom} not deterministic across hash seeds"
