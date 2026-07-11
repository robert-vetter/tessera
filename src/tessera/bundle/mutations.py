"""Deterministic tamper generators for the Auditability Floor (spec 0137).

Each generator takes a sealed bundle dict and returns a *mutant* — a bundle
tampered in exactly one way — together with the verdict class and a substring
the verifier's report must name. Where re-sealing is the realistic attack (a
content edit whose hashes are recomputed), the generator re-seals, so the
mutation exercises the SEMANTIC layer, not merely the hash. Where the attack
is on the envelope itself (a stale root), it does not.

These are the one source of truth for "what a tamper looks like": both
:mod:`tessera.eval.auditability` (the floor runner) and the tests consume
them, so the battery and its pins can never drift apart. The deep JSON
manipulation is done on an ``Any``-typed working copy — the bundle is a
dynamically-shaped JSON document, and the round-trip is what the floor
measures.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tessera.bundle.format import seal

# Verdict classes (mirror tessera.bundle.verify): the exit code a mutant must
# produce. 4 = envelope broken, 2 = semantic failure, 3 = visible degradation.
TAMPERED = 4
FAIL = 2
DEGRADED = 3


@dataclass(frozen=True)
class Mutation:
    """One tamper: its name, the mutated bundle, the exit code it must produce,
    and a substring the verifier's named cause must contain."""

    name: str
    bundle: dict[str, object]
    expected_exit: int
    expected_cause: str


def _working_copy(bundle: dict[str, object]) -> Any:
    """A deep copy typed ``Any`` for the deep, dynamically-shaped edits below."""
    return copy.deepcopy(bundle)


def _reseal(mutant: Any) -> dict[str, object]:
    resealed: dict[str, object] = seal(
        {k: v for k, v in mutant.items() if k != "integrity"}
    )
    return resealed


def _first_cited_node(mutant: Any) -> Any:
    cited = mutant["result"]["claims"][0]["support"][0]["id"]
    for node in mutant["evidence_closure"]["graph"]["nodes"]:
        if node["record"]["id"] == cited:
            return node
    raise AssertionError("no cited node found")


# --- the generators (each: sealed bundle -> Mutation) -------------------------------


def evidence_value_edit(b: dict[str, object]) -> Mutation:
    """Flip a cited amount + re-seal: the dependent claim no longer re-derives."""
    m = _working_copy(b)
    node = _first_cited_node(m)
    old = dict(node["attributes"]).get("net_amount")
    if isinstance(old, str):
        new = str(int(float(old)) + 30000) + ".00"
        node["attributes"] = [
            [k, new if k == "net_amount" else v] for k, v in node["attributes"]
        ]
        node["record"]["text"] = str(node["record"]["text"]).replace(old, new)
    return Mutation("evidence_value_edit", _reseal(m), FAIL, "re-derive")


def evidence_record_omission(b: dict[str, object]) -> Mutation:
    """Delete a cited node + re-seal: a dangling reference, caught not crashed."""
    m = _working_copy(b)
    cited = m["result"]["claims"][0]["support"][0]["id"]
    graph = m["evidence_closure"]["graph"]
    graph["nodes"] = [n for n in graph["nodes"] if n["record"]["id"] != cited]
    return Mutation("evidence_record_omission", _reseal(m), FAIL, "absent")


def claim_text_edit(b: dict[str, object]) -> Mutation:
    """Rewrite a claim's text + re-seal: it no longer matches the corpus answer."""
    m = _working_copy(b)
    m["result"]["claims"][0]["text"] = "A fabricated claim not from the evidence."
    return Mutation("claim_text_edit", _reseal(m), FAIL, "diverge")


def verdict_flip(b: dict[str, object]) -> Mutation:
    """Flip a recorded verified flag + re-seal: it disagrees with re-derivation."""
    m = _working_copy(b)
    m["result"]["claims"][0]["verified"] = not m["result"]["claims"][0]["verified"]
    return Mutation("verdict_flip", _reseal(m), FAIL, "altered")


def question_swap(b: dict[str, object]) -> Mutation:
    """Swap the question for one the corpus answers DIFFERENTLY + re-seal: the
    packaged corpus no longer re-yields the recorded answer."""
    m = _working_copy(b)
    m["result"]["question"] = "What is the total net order value for Müller Logistik?"
    return Mutation("question_swap", _reseal(m), FAIL, "packaged corpus")


def fabricated_render(b: dict[str, object]) -> Mutation:
    """Fabricate a provenance render string + re-seal: a derived-field lie."""
    m = _working_copy(b)
    for claim in m["result"]["claims"]:
        for evidence in claim["support"]:
            evidence["locator"]["render"] = "table PAYROLL_SECRETS, row 7"
    return Mutation("fabricated_render", _reseal(m), FAIL, "provenance")


def closure_kind_downgrade(b: dict[str, object]) -> Mutation:
    """Relabel the closure to a partial kind while packaging a full graph +
    re-seal: the label cannot suppress re-execution."""
    m = _working_copy(b)
    m["evidence_closure"]["kind"] = "cited-records-only"
    return Mutation("closure_kind_downgrade", _reseal(m), FAIL, "cannot suppress")


def leaf_tamper(b: dict[str, object]) -> Mutation:
    """Corrupt one manifest leaf WITHOUT re-sealing: the root no longer
    recomputes and the leaf is named."""
    m = _working_copy(b)
    leaves = m["integrity"]["leaves"]
    key = next(iter(leaves))
    leaves[key] = "sha256:" + "0" * 64
    return Mutation("leaf_tamper", m, TAMPERED, key)


def root_mismatch(b: dict[str, object]) -> Mutation:
    """Corrupt the stored root: the envelope is broken."""
    m = _working_copy(b)
    m["integrity"]["root"] = "sha256:" + "0" * 64
    return Mutation("root_mismatch", m, TAMPERED, "root")


def engine_version_spoof(b: dict[str, object]) -> Mutation:
    """Claim a different engine version + re-seal: NOT-EVALUABLE, visible."""
    m = _working_copy(b)
    m["engine"]["tessera_version"] = "9.9.9"
    return Mutation("engine_version_spoof", _reseal(m), DEGRADED, "9.9.9")


# --- action mutations (only reachable when the bundle carries an action) -------------


def wire_body_injection(b: dict[str, object]) -> Mutation:
    """Inject an extra wire-body key (labels) + re-seal: the request no longer
    matches the one the evidence re-derives."""
    m = _working_copy(b)
    body = m["action"]["request"]["body"]
    body["labels"] = ["incident", "auto-merge", "P0"]
    body["assignees"] = ["victim"]
    return Mutation("wire_body_injection", _reseal(m), FAIL, "wire body")


def wire_method_repoint(b: dict[str, object]) -> Mutation:
    """Repoint the wire method + path + re-seal: it must match the frozen target."""
    m = _working_copy(b)
    m["action"]["request"]["method"] = "PATCH"
    m["action"]["request"]["path"] = "/repos/{owner}/{repo}/issues/1/comments"
    return Mutation("wire_method_repoint", _reseal(m), FAIL, "method/path")


def wire_slot_edit(b: dict[str, object]) -> Mutation:
    """Edit a wire slot value + re-seal: the slots diverge from the re-derived."""
    m = _working_copy(b)
    for slot in m["action"]["slots"]:
        if slot["part"] == "body":
            slot["value"] = str(slot["value"]) + " INJECTED"
            break
    return Mutation("wire_slot_edit", _reseal(m), FAIL, "wire")


# The battery, split by which bundle it applies to. Answer mutations run on a
# business answer bundle; action mutations on a devex incident action bundle.
AnswerMutation = Callable[[dict[str, object]], Mutation]

ANSWER_MUTATIONS: tuple[AnswerMutation, ...] = (
    evidence_value_edit,
    evidence_record_omission,
    claim_text_edit,
    verdict_flip,
    question_swap,
    fabricated_render,
    closure_kind_downgrade,
    leaf_tamper,
    root_mismatch,
    engine_version_spoof,
)

ACTION_MUTATIONS: tuple[AnswerMutation, ...] = (
    wire_body_injection,
    wire_method_repoint,
    wire_slot_edit,
)
