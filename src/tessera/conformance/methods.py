"""Steelmanned reference implementations of published verification methods.

Spec 0146 / ADR 0036. Each method is **our own** implementation of a
*publicly described method* — never a vendor's product, never a named
score. Each is written to be as strong as its source describes, and each
docstring records the source and the scope that source claims for itself.
A benchmark whose baselines were built to lose is marketing; these are
built to win wherever their design allows.

Two threat models (spec 0146):

- ``OUTSIDER`` — the attacker cannot produce the issuer's attestation.
  An attested root is unforgeable, so any change is detected. Under this
  model the signature-based methods detect **everything**.
- ``ISSUER`` — the forgery is produced inside the trust boundary and
  re-attested with a legitimate key (a self-serving operator, a
  compromised key, or an agent pipeline sealing its own output). This is
  the operative model for an agent's own receipt.

Signatures are modelled as an *unforgeable attested root* rather than by
calling real crypto: an Ed25519 signature over the root provides exactly
that property (ADR 0032), so the model is faithful while the benchmark
stays key-free and runnable on a clean clone.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from tessera.bundle.canonical import digest
from tessera.bundle.format import compute_root, leaf_manifest
from tessera.bundle.verify import BundleFormatError, verify_bundle

#: Threat models.
OUTSIDER = "outsider"
ISSUER = "issuer"
THREATS = (OUTSIDER, ISSUER)

#: Outcomes. NOT_APPLICABLE exists so an attack that cannot exist against
#: a design is never scored as a win for it (ADR 0036).
DETECTED = "DETECTED"
MISSED = "MISSED"
NOT_APPLICABLE = "NOT-APPLICABLE"


@dataclass(frozen=True)
class Method:
    """One verification method under test: its id, the source it models,
    and the check itself."""

    key: str
    title: str
    models: str
    check: Callable[[dict[str, object], dict[str, object], str], str]

    def to_dict(self) -> dict[str, object]:
        return {"key": self.key, "title": self.title, "models": self.models}


def _attested_root(original: dict[str, object]) -> str:
    """What the issuer attested at seal time — the root of the honest
    bundle. Under OUTSIDER this value is unforgeable; under ISSUER the
    attacker re-attests, so the comparison is against the mutant's own."""
    return compute_root(leaf_manifest(original))


def _stored_root(bundle: dict[str, object]) -> object:
    integrity = bundle.get("integrity")
    return integrity.get("root") if isinstance(integrity, dict) else None


def _stored_leaves(bundle: dict[str, object]) -> dict[str, object]:
    integrity = bundle.get("integrity")
    leaves = integrity.get("leaves") if isinstance(integrity, dict) else None
    return leaves if isinstance(leaves, dict) else {}


# --- 1. hash-manifest -------------------------------------------------------------


def hash_manifest(
    original: dict[str, object], mutant: dict[str, object], threat: str
) -> str:
    """Per-leaf canonical hashing plus a Merkle root recompute — the plain
    hash-chained/Merkle receipt every 2026 audit-log product ships.

    Models: hash-chained evidence bundles / Merkle audit logs (the shape
    the IETF receipt drafts and the agent-governance toolkits all build
    on). Scope its own literature claims: *the record was not altered*.

    Deliberately NOT extended with a commitment to the section set — a
    manifest that hashes leaves does not, by itself, notice a section that
    was never hashed. (Tessera's own integrity layer had exactly this hole
    until its M20/M21 audit; keeping the difference visible here is the
    point of a fair benchmark.)
    """
    try:
        manifest = leaf_manifest(mutant)
    except ValueError:
        return DETECTED  # unreadable shape
    if _stored_root(mutant) != compute_root(manifest):
        return DETECTED
    for name, value in _stored_leaves(mutant).items():
        if manifest.get(name) != value:
            return DETECTED
    return MISSED


# --- 2. signed-receipt ------------------------------------------------------------


def signed_receipt(
    original: dict[str, object], mutant: dict[str, object], threat: str
) -> str:
    """Hash-manifest plus an Ed25519 signature over the root, checked
    offline against the declared signer key.

    Models: the IETF ASQAV "Compliance Profile of Signed Action Receipts
    for AI Agents" draft (2026) — canonicalize, hash, sign, verify
    offline. Scope it claims: the receipt is authentic and unaltered.

    Under OUTSIDER the attested root cannot be forged, so *any* change is
    detected — including re-sealed semantic edits. Under ISSUER the
    forgery is re-signed by a legitimate key and the signature check
    passes, leaving only the hash checks, which the re-seal satisfies.
    """
    if hash_manifest(original, mutant, threat) == DETECTED:
        return DETECTED
    if threat == OUTSIDER:
        try:
            recomputed = compute_root(leaf_manifest(mutant))
        except ValueError:
            return DETECTED
        if recomputed != _attested_root(original):
            return DETECTED
    return MISSED


# --- 3. policy-bound-receipt ------------------------------------------------------


def policy_bound_receipt(
    original: dict[str, object], mutant: dict[str, object], threat: str
) -> str:
    """Signed receipt plus a declared policy ("covenant") hash binding the
    decision to the governance rules it ran under.

    Models: Microsoft's Agent Governance Toolkit proposal "Independently
    Verifiable Compliance Receipts" — three checks: signature validity,
    chain integrity, and the declared policy hash matching the expected
    one. The proposal itself states the verifier confirms consistent
    signing, not whether the decision was correct.

    Adds real detection power over a plain signed receipt: a receipt that
    silently claims a *different* governing policy is caught here.
    """
    if signed_receipt(original, mutant, threat) == DETECTED:
        return DETECTED
    expected = _declared_policy(original)
    if expected is not None and _declared_policy(mutant) != expected:
        return DETECTED
    return MISSED


def _declared_policy(bundle: dict[str, object]) -> str | None:
    """The policy/covenant hash a receipt declares, if the design carries
    one in the artifact at all."""
    engine = bundle.get("engine")
    if not isinstance(engine, dict):
        return None
    declared = engine.get("covenant_hash")
    return declared if isinstance(declared, str) else None


# --- 4. syntactic-envelope --------------------------------------------------------

#: The fixed date this benchmark verifies at — a constant, never a clock,
#: so the scorecard is byte-stable. Contract windows are compared to it.
BENCHMARK_DATE = "2026-07-18"


def envelope_hash(bundle: dict[str, object]) -> str:
    """The declared-envelope hash over the replay-critical fields: the
    engine/contract section (excluding the hash itself) and the format pin.

    Exported so the attack battery can recompute it exactly as the verifier
    does — a benchmark must assume a *competent* attacker who keeps every
    declared value internally consistent, or it measures the attacker's
    sloppiness instead of the method's power.
    """
    engine = bundle.get("engine")
    settled = (
        {k: v for k, v in engine.items() if k != "envelope_hash"}
        if isinstance(engine, dict)
        else engine
    )
    return digest([settled, bundle.get("format")])


def syntactic_envelope(
    original: dict[str, object], mutant: dict[str, object], threat: str
) -> str:
    """Declared-envelope-hash consistency plus sealed-order/immutability —
    the validator invariants of a runtime-attestation design.

    Models: "Proof of Execution: Runtime Verification for Governed AI
    Agent Actions" (Rhodes & Kang, arXiv:2607.05397, 2026), whose
    validator checks invariants the paper itself describes as *syntactic
    predicates* over (contract, event stream, replay context) — notably
    envelope closure (I5a), which the paper scopes to checking that the
    **declared** envelope is consistent with the replay context. The
    paper places discovery of *undeclared* dependencies outside that
    scope, and its deterministic-replay guarantee rests on stated
    deployment assumptions rather than on the validator recomputing
    content. PoE is strong at what it claims — authorization, scope,
    trace integrity, replayability — which is a different axis from
    claim-vs-evidence checking, and this benchmark does not grade it on
    the axis it never claimed.
    """
    if signed_receipt(original, mutant, threat) == DETECTED:
        return DETECTED
    declared = _declared_envelope(mutant)
    if declared is not None and declared != envelope_hash(mutant):
        return DETECTED
    # Contract freshness (PoE's I1): a receipt whose governing mandate has
    # expired is rejected even when nothing about it was altered. This is
    # the axis runtime attestation owns and content re-execution does not.
    not_after = _declared_contract_window(mutant)
    if not_after is not None and not_after < BENCHMARK_DATE:
        return DETECTED
    return MISSED


def _declared_envelope(bundle: dict[str, object]) -> str | None:
    engine = bundle.get("engine")
    if not isinstance(engine, dict):
        return None
    declared = engine.get("envelope_hash")
    return declared if isinstance(declared, str) else None


def _declared_contract_window(bundle: dict[str, object]) -> str | None:
    engine = bundle.get("engine")
    if not isinstance(engine, dict):
        return None
    not_after = engine.get("contract_not_after")
    return not_after if isinstance(not_after, str) else None


# --- 5. re-execution --------------------------------------------------------------


def re_execution(
    original: dict[str, object], mutant: dict[str, object], threat: str
) -> str:
    """Tessera: re-derive every recorded claim verdict from the packaged
    evidence and require the packaged corpus to re-yield the recorded
    answer (plus the wire action and, for chains, every embedded upstream,
    recursively).

    Scope it claims: claim-vs-evidence faithfulness and approval-gated
    action — *not* truth in the world, and not execution attestation.
    """
    try:
        report = verify_bundle(mutant)
    except BundleFormatError:
        return DETECTED
    return DETECTED if report.exit_code != 0 else MISSED


METHODS: tuple[Method, ...] = (
    Method(
        key="hash-manifest",
        title="Hash manifest / Merkle receipt",
        models="hash-chained audit logs & Merkle evidence bundles",
        check=hash_manifest,
    ),
    Method(
        key="signed-receipt",
        title="Signed receipt (Ed25519 over the root)",
        models="IETF ASQAV signed action receipts (2026 draft)",
        check=signed_receipt,
    ),
    Method(
        key="policy-bound-receipt",
        title="Policy-bound signed receipt",
        models="Microsoft Agent Governance Toolkit verifiable compliance receipts",
        check=policy_bound_receipt,
    ),
    Method(
        key="syntactic-envelope",
        title="Syntactic envelope / runtime attestation invariants",
        models="Proof of Execution (Rhodes & Kang, arXiv:2607.05397)",
        check=syntactic_envelope,
    ),
    Method(
        key="re-execution",
        title="Re-execution of claim vs. evidence (Tessera)",
        models="this project",
        check=re_execution,
    ),
)
