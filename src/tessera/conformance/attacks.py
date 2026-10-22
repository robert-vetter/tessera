"""The attack battery for the Verification Gap benchmark (spec 0146).

Five families, each a deterministic function from an honest base bundle to
a forged one. Where the CI-pinned mutation battery (spec 0137) already
implements an attack, it is reused rather than re-written, so the
benchmark and the Auditability Floor can never drift apart.

Family key:

- ``envelope`` — byte-level tampering **without** re-sealing. Every honest
  verification method must detect these; they exist in the table to prove
  the baselines were not built to lose.
- ``semantic`` — content forgery, **re-sealed**: the claims say something
  the packaged evidence does not support, and every hash is consistent.
- ``action`` — the wire request / execution receipt forged, re-sealed.
- ``chain`` — forgery inside a multi-agent chain, re-sealed at every level.
- ``declaration`` — attacks on what a receipt *declares* about its own
  governance (the policy it ran under) or its own dependency envelope.

Every attack is deterministic: no clock, no randomness, so the scorecard
is byte-stable.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from tessera.bundle import mutations
from tessera.bundle.canonical import digest
from tessera.bundle.format import seal
from tessera.conformance.methods import envelope_hash

REPO = Path(__file__).resolve().parents[3]
HONEST = REPO / "data" / "challenge" / "honest.tsb"
CHAIN_BRIEF = REPO / "data" / "chain" / "brief.tsb"

ENVELOPE = "envelope"
SEMANTIC = "semantic"
ACTION = "action"
CHAIN = "chain"
DECLARATION = "declaration"
AUTHORIZATION = "authorization"

FAMILIES = (ENVELOPE, SEMANTIC, ACTION, CHAIN, DECLARATION, AUTHORIZATION)

#: Which base bundle an attack needs.
BASE_ANSWER = "answer"
BASE_ACTION = "action"
BASE_CHAIN = "chain"
BASE_DECLARED = "declared"


@dataclass(frozen=True)
class Attack:
    """One attack: its id, family, the base bundle it needs, the forging
    function, and the methods for which it is structurally meaningless."""

    key: str
    family: str
    base: str
    forge: Callable[[dict[str, object]], dict[str, object]]
    description: str = ""
    not_applicable_to: tuple[str, ...] = field(default=())

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "family": self.family,
            "description": self.description,
            "not_applicable_to": list(self.not_applicable_to),
        }


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _copy(bundle: dict[str, object]) -> Any:
    return copy.deepcopy(bundle)


def _reseal(bundle: Any) -> dict[str, object]:
    return seal({k: v for k, v in bundle.items() if k != "integrity"})


# --- base bundles -----------------------------------------------------------------


HONEST_POLICY = {"policy": "read-only-agent", "version": 1}
#: A contract window that is still open at the benchmark's fixed date.
LIVE_CONTRACT = "2027-01-01"
#: A contract window that expired before it — used by the replay attack.
EXPIRED_CONTRACT = "2026-01-01"


def _declared_receipt(
    bundle: dict[str, object], *, not_after: str = LIVE_CONTRACT
) -> dict[str, object]:
    """An honest bundle as a *declaring* design would emit it: carrying a
    governing-policy ("covenant") hash, a contract validity window, and a
    dependency-envelope hash (spec 0146). Modelling those designs fairly
    requires their artifacts to carry the fields their verifiers check."""
    working = _copy(bundle)
    engine = working["engine"]
    engine["covenant_hash"] = digest(HONEST_POLICY)
    engine["contract_not_after"] = not_after
    engine["envelope_hash"] = envelope_hash(working)
    return _reseal(working)


@lru_cache(maxsize=1)
def _cached_bases() -> tuple[tuple[str, str], ...]:
    """The base bundles as canonical JSON text, built once per process.

    Cached as *text* so every caller gets a fresh, independently mutable
    structure: the attack generators mutate deep copies, and a shared dict
    handed out twice would let one attack's edits leak into another's base.
    """
    from tessera.bundle.emit import build_action_bundle, bundle_bytes

    honest = HONEST.read_text(encoding="utf-8")
    action = bundle_bytes(
        build_action_bundle(
            "incident",
            "devex",
            "Why did run R-1042 fail, and has this happened before?",
        )
    ).decode("utf-8")
    chain = CHAIN_BRIEF.read_text(encoding="utf-8")
    declared = json.dumps(_declared_receipt(json.loads(honest)))
    return (
        (BASE_ANSWER, honest),
        (BASE_ACTION, action),
        (BASE_CHAIN, chain),
        (BASE_DECLARED, declared),
    )


def base_bundles() -> dict[str, dict[str, object]]:
    """The four honest base bundles. Deterministic: the answer and chain
    bases are committed artifacts; the action base is built from the frozen
    action chain (byte-stable emission, spec 0133)."""
    return {name: json.loads(text) for name, text in _cached_bases()}


# --- reused mutation generators (spec 0137) ---------------------------------------


def _from_mutation(
    generator: Callable[[dict[str, object]], mutations.Mutation],
) -> Callable[[dict[str, object]], dict[str, object]]:
    def forge(bundle: dict[str, object]) -> dict[str, object]:
        return generator(bundle).bundle

    return forge


# --- chain attacks ----------------------------------------------------------------


def _chain_upstreams(bundle: Any) -> Any:
    return bundle["evidence_closure"]["upstream"]


def chain_deep_forge(bundle: dict[str, object]) -> dict[str, object]:
    """Forge a claim *inside* an embedded upstream, re-seal the upstream,
    rewrite the chain-level copies of that text so the chain is internally
    consistent, and re-seal the chain. Every hash checks out at every
    level; only re-executing the upstream's own evidence exposes it."""
    working = _copy(bundle)
    upstreams = _chain_upstreams(working)
    victim = upstreams[0]
    claims = victim["result"]["claims"]
    original_text = str(claims[0]["text"])
    forged_text = original_text.replace("failed", "succeeded")
    if forged_text == original_text:
        forged_text = original_text + " (per the approved summary)"
    claims[0]["text"] = forged_text
    upstreams[0] = _reseal(victim)

    # Keep the chain level consistent with the forged upstream: the derived
    # record, the graph node and the recorded claim all carry the text.
    text = json.dumps({k: v for k, v in working.items() if k != "integrity"})
    text = text.replace(json.dumps(original_text)[1:-1], json.dumps(forged_text)[1:-1])
    return _reseal(json.loads(text))


def chain_cited_text_tamper(bundle: dict[str, object]) -> dict[str, object]:
    """Alter a derived record's text at the chain level only, leaving the
    embedded upstreams byte-intact, and re-seal."""
    working = _copy(bundle)
    saved = working["evidence_closure"]["upstream"]
    working["evidence_closure"]["upstream"] = []
    records = working["evidence_closure"]["kb"]["records"]
    original_text = str(records[0]["text"])
    forged_text = original_text + " [reviewed and approved]"
    text = json.dumps({k: v for k, v in working.items() if k != "integrity"})
    text = text.replace(json.dumps(original_text)[1:-1], json.dumps(forged_text)[1:-1])
    rebuilt = json.loads(text)
    rebuilt["evidence_closure"]["upstream"] = saved
    return _reseal(rebuilt)


def chain_upstream_drop(bundle: dict[str, object]) -> dict[str, object]:
    """Remove an embedded upstream and re-seal: the chain still cites its
    claims, but the evidence for them no longer travels with the file."""
    working = _copy(bundle)
    working["evidence_closure"]["upstream"] = _chain_upstreams(working)[:1]
    return _reseal(working)


# --- declaration attacks ----------------------------------------------------------


def policy_swap(bundle: dict[str, object]) -> dict[str, object]:
    """Re-declare the governing policy: the receipt claims it ran under a
    different (weaker) covenant than it did. A competent attacker keeps the
    declared envelope consistent, so only a verifier holding the *expected*
    policy hash out of band can notice."""
    working = _copy(bundle)
    working["engine"]["covenant_hash"] = digest(
        {"policy": "anything-goes", "version": 1}
    )
    working["engine"]["envelope_hash"] = envelope_hash(working)
    return _reseal(working)


def undeclared_dependency(bundle: dict[str, object]) -> dict[str, object]:
    """Make the answer depend on evidence the declared envelope does not
    contain: a claim cites a record id that is not packaged. The declared
    envelope stays internally consistent and is re-computed, so an
    envelope-closure check is satisfied — which is exactly the scope
    limitation the Proof-of-Execution paper states for its I5a invariant
    (undeclared dependencies enter through a deployment assumption, not
    the validator)."""
    working = _copy(bundle)
    claims = working["result"]["claims"]
    ghost = _copy(claims[0]["support"][0])
    ghost["id"] = "ghost-record-not-packaged"
    ghost["source"] = "external_system/ledger.csv (row 42)"
    claims[0]["support"] = [*claims[0]["support"], ghost]
    working["engine"]["envelope_hash"] = envelope_hash(working)
    return _reseal(working)


def stale_contract_replay(bundle: dict[str, object]) -> dict[str, object]:
    """No forgery at all: a byte-perfect, honest receipt whose governing
    mandate has expired, presented as current.

    This is the attack **content re-execution misses by design** — a PASS
    is a statement about claims and evidence, never about recency (the
    honest limit BUNDLE.md has recorded since the M20/M21 audit). A
    runtime-attestation validator with a contract-freshness invariant
    catches it. It is in this battery precisely because a benchmark whose
    author never loses a cell is not a benchmark."""
    working = _copy(bundle)
    working["engine"]["contract_not_after"] = EXPIRED_CONTRACT
    working["engine"]["envelope_hash"] = envelope_hash(working)
    return _reseal(working)


ATTACKS: tuple[Attack, ...] = (
    # --- envelope: byte-level tampering, NOT re-sealed ---------------------------
    Attack(
        "leaf_tamper",
        ENVELOPE,
        BASE_ANSWER,
        _from_mutation(mutations.leaf_tamper),
        "corrupt one manifest leaf without re-sealing",
    ),
    Attack(
        "root_mismatch",
        ENVELOPE,
        BASE_ANSWER,
        _from_mutation(mutations.root_mismatch),
        "corrupt the stored root",
    ),
    Attack(
        "extra_top_section",
        ENVELOPE,
        BASE_ANSWER,
        _from_mutation(mutations.extra_top_section),
        "smuggle an unauthenticated top-level section",
    ),
    # --- semantic: content forgery, re-sealed ------------------------------------
    Attack(
        "evidence_value_edit",
        SEMANTIC,
        BASE_ANSWER,
        _from_mutation(mutations.evidence_value_edit),
        "edit a cited amount so the claim no longer follows",
    ),
    Attack(
        "evidence_record_omission",
        SEMANTIC,
        BASE_ANSWER,
        _from_mutation(mutations.evidence_record_omission),
        "delete a cited evidence record",
    ),
    Attack(
        "claim_text_edit",
        SEMANTIC,
        BASE_ANSWER,
        _from_mutation(mutations.claim_text_edit),
        "rewrite a claim to say something the evidence does not",
    ),
    Attack(
        "verdict_flip",
        SEMANTIC,
        BASE_ANSWER,
        _from_mutation(mutations.verdict_flip),
        "flip a recorded verification verdict",
    ),
    Attack(
        "question_swap",
        SEMANTIC,
        BASE_ANSWER,
        _from_mutation(mutations.question_swap),
        "attach the answer to a different question",
    ),
    Attack(
        "fabricated_render",
        SEMANTIC,
        BASE_ANSWER,
        _from_mutation(mutations.fabricated_render),
        "fabricate the displayed provenance of cited evidence",
    ),
    Attack(
        "closure_kind_downgrade",
        SEMANTIC,
        BASE_ANSWER,
        _from_mutation(mutations.closure_kind_downgrade),
        "relabel the evidence closure to suppress re-execution",
    ),
    # --- action: the wire request / receipt, re-sealed ----------------------------
    Attack(
        "wire_body_injection",
        ACTION,
        BASE_ACTION,
        _from_mutation(mutations.wire_body_injection),
        "inject extra content into the outgoing request body",
    ),
    Attack(
        "wire_method_repoint",
        ACTION,
        BASE_ACTION,
        _from_mutation(mutations.wire_method_repoint),
        "repoint the request to a different endpoint/method",
    ),
    Attack(
        "wire_slot_edit",
        ACTION,
        BASE_ACTION,
        _from_mutation(mutations.wire_slot_edit),
        "edit a grounded value on its way to the wire",
    ),
    Attack(
        "outcome_forgery",
        ACTION,
        BASE_ACTION,
        _from_mutation(mutations.outcome_forgery),
        "forge the execution outcome (claim a real send)",
    ),
    Attack(
        "approval_strip",
        ACTION,
        BASE_ACTION,
        _from_mutation(mutations.approval_strip),
        "forge the human approval flag on an action",
    ),
    # --- chain: multi-agent forgery, re-sealed at every level ---------------------
    Attack(
        "chain_deep_forge",
        CHAIN,
        BASE_CHAIN,
        chain_deep_forge,
        "forge a claim inside an embedded upstream and rewrite every "
        "chain-level reference so the whole chain is self-consistent",
    ),
    Attack(
        "chain_cited_text_tamper",
        CHAIN,
        BASE_CHAIN,
        chain_cited_text_tamper,
        "alter what the chain says an upstream concluded",
    ),
    Attack(
        "chain_upstream_drop",
        CHAIN,
        BASE_CHAIN,
        chain_upstream_drop,
        "drop the upstream evidence a cited conclusion rests on",
    ),
    # --- declaration: what the receipt says about its own governance --------------
    Attack(
        "policy_swap",
        DECLARATION,
        BASE_DECLARED,
        policy_swap,
        "declare a different (weaker) governing policy than the one that ran",
        # Tessera keeps policy OUT of the artifact by design (ADR 0034), so
        # this attack does not exist against it — scored N/A, never a win.
        not_applicable_to=("re-execution",),
    ),
    Attack(
        "undeclared_dependency",
        DECLARATION,
        BASE_DECLARED,
        undeclared_dependency,
        "depend on evidence the declared envelope does not contain",
    ),
    # --- authorization: the axis runtime attestation owns -------------------------
    Attack(
        "stale_contract_replay",
        AUTHORIZATION,
        BASE_DECLARED,
        stale_contract_replay,
        "replay an honest, unaltered receipt whose mandate has expired "
        "(re-execution misses this BY DESIGN — a PASS is not a recency claim)",
    ),
)
