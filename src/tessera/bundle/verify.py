"""Offline re-executing verification of a trust bundle (spec 0134).

The differentiator of the act (plan spec 0131): ``verify_bundle`` re-derives a
bundle's verdicts **from the file's content alone** — no network, no engine
cache, no trust in the operator. Two layers, always both, reported
separately:

- **Integrity** (unit 0133's re-check): proves the file is the file, names
  the exact leaf. A broken envelope does not suppress the semantic layer —
  a tamperer who re-seals (recomputes manifest + root, trivial until
  signatures land in unit 0135) makes integrity pass; semantics catch the
  lie.
- **Semantic re-execution**, two checks:
  (a) *claim-vs-evidence*: every recorded claim is re-verified with the
  eval's own ``is_supported`` against the packaged graph, and compared with
  the recorded verdict; (b) *answer re-derivation*: the domain's
  deterministic router re-runs the question over the packaged corpus and
  must yield the recorded answer — the check that binds
  question → answer → claims and defeats the claim-swap attack (a re-sealed
  bundle whose claims are *different, individually true* claims from the
  same corpus would pass (a) alone). (b) is also what makes a *refusal*
  bundle re-derivable: the corpus itself re-yields the refusal and its
  reason.

Verdict taxonomy per bundle (spec 0131 D3): ``RE-DERIVED`` (re-execution
ran; per-claim verdicts + match), ``INTEGRITY-ONLY`` (closure not fully
packaged — hashes checked, content not re-derivable, and the output says
so), ``NOT-EVALUABLE`` (unknown domain, version or shape-identifier
mismatch — a verdict under a different grammar would be a different verdict
wearing the same name; ADR 0031 §5). Degradation is always visible, never a
false PASS.

Exit codes (precedence 4 > 2 > 3 > 0): 4 envelope unreadable/broken ·
2 semantic failure (mismatch, divergence, structural violation) ·
3 degraded but nothing failed · 0 fully re-derived, matched, verified.
"""

from __future__ import annotations

from dataclasses import dataclass

from tessera.agent.grounded import (
    GroundedResult,
    available_domains,
    domain,
    serialize_answer,
)
from tessera.bundle.canonical import canonical_bytes
from tessera.bundle.ed25519 import verify as ed25519_verify
from tessera.bundle.emit import engine_version, shape_identifiers
from tessera.bundle.format import (
    CHAIN_DOMAIN,
    CLOSURE_CHAIN,
    CLOSURE_FULL_SNAPSHOT,
    FORMAT_MAJOR,
    FORMAT_NAME,
    integrity_mismatches,
)
from tessera.bundle.serde import (
    claim_from_grounded,
    graph_from_dict,
    grounded_result_from_dict,
    kb_from_dict,
)
from tessera.eval.metrics import ClaimShape, is_supported
from tessera.graph import KnowledgeGraph
from tessera.grounding import KnowledgeBase

RE_DERIVED = "RE-DERIVED"
INTEGRITY_ONLY = "INTEGRITY-ONLY"
NOT_EVALUABLE = "NOT-EVALUABLE"


class BundleFormatError(ValueError):
    """The file is not a readable trust bundle (missing/malformed sections,
    wrong format major) — the envelope-level failure, exit code 4."""


@dataclass(frozen=True)
class ClaimCheck:
    """One recorded claim's re-execution: the re-derived verdict, the recorded
    verdict, whether they match, and — when something is wrong — the named
    cause."""

    index: int
    text: str
    recorded: bool
    rederived: bool
    cause: str | None

    @property
    def matches(self) -> bool:
        return self.recorded == self.rederived

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "text": self.text,
            "recorded": self.recorded,
            "rederived": self.rederived,
            "matches": self.matches,
            "cause": self.cause,
        }


@dataclass(frozen=True)
class UpstreamCheck:
    """One embedded upstream bundle's recursive verification (spec 0143): its
    sealed root, the verdict its own full re-verification produced *here*
    (recorded verdicts are never trusted), the named cause on non-PASS, and
    the upstream's signature status/signer (spec 0144: chain signer policies
    read the recursion the verifier already performs)."""

    root: str
    verdict: str
    cause: str | None
    signature_status: str = "UNSIGNED"
    signer: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "verdict": self.verdict,
            "cause": self.cause,
            "signature_status": self.signature_status,
            "signer": self.signer,
        }


UNSIGNED = "UNSIGNED"
SIGNED = "SIGNED"
ed25519_ALGORITHM = "ed25519"


@dataclass(frozen=True)
class VerifyReport:
    """The full two-layer verification result of one bundle."""

    domain: str
    sealed_under: str
    installed: str
    taxonomy: str
    taxonomy_reason: str | None
    integrity_problems: tuple[str, ...]
    signature_status: str
    signature_public_key: str | None
    signature_problems: tuple[str, ...]
    structural_problems: tuple[str, ...]
    claims: tuple[ClaimCheck, ...]
    answer_rederives: bool | None
    answer_cause: str | None
    refused: bool
    #: Chain bundles only (spec 0143): one entry per embedded upstream, from
    #: its recursive re-verification here. Empty for single-decision bundles.
    upstreams: tuple[UpstreamCheck, ...] = ()

    @property
    def envelope_problems(self) -> tuple[str, ...]:
        """The envelope layer: integrity (the file is the file) plus signature
        (origin). Either broken is a tamper-level failure (exit 4)."""
        return self.integrity_problems + self.signature_problems

    @property
    def semantic_problems(self) -> tuple[str, ...]:
        """Named semantic failures: structural violations, claim mismatches,
        and an answer that does not re-derive."""
        problems = list(self.structural_problems)
        problems.extend(c.cause for c in self.claims if not c.matches and c.cause)
        if self.answer_rederives is False and self.answer_cause:
            problems.append(self.answer_cause)
        return tuple(problems)

    @property
    def degraded(self) -> bool:
        """Visible degradation: not re-derivable, or an honestly-unverified
        claim faithfully recorded (unreachable on the committed corpora,
        whose faithfulness floor is 1.0 — kept for the taxonomy's honesty)."""
        return self.taxonomy != RE_DERIVED or any(
            not c.recorded and not c.rederived for c in self.claims
        )

    @property
    def exit_code(self) -> int:
        if self.envelope_problems:
            return 4
        if self.semantic_problems:
            return 2
        if self.degraded:
            return 3
        return 0

    @property
    def verdict(self) -> str:
        return {0: "PASS", 2: "FAIL", 3: "DEGRADED", 4: "TAMPERED"}[self.exit_code]

    def to_dict(self) -> dict[str, object]:
        return {
            "domain": self.domain,
            "sealed_under": self.sealed_under,
            "installed": self.installed,
            "taxonomy": self.taxonomy,
            "taxonomy_reason": self.taxonomy_reason,
            "integrity_problems": list(self.integrity_problems),
            "signature": {
                "status": self.signature_status,
                "public_key": self.signature_public_key,
                "problems": list(self.signature_problems),
            },
            "structural_problems": list(self.structural_problems),
            "claims": [c.to_dict() for c in self.claims],
            "answer_rederives": self.answer_rederives,
            "answer_cause": self.answer_cause,
            "refused": self.refused,
            "upstreams": [u.to_dict() for u in self.upstreams],
            "semantic_problems": list(self.semantic_problems),
            "verdict": self.verdict,
            "exit_code": self.exit_code,
        }


# --- envelope reading ------------------------------------------------------------


def _section(bundle: dict[str, object], key: str) -> dict[str, object]:
    value = bundle.get(key)
    if not isinstance(value, dict):
        raise BundleFormatError(f"missing or malformed bundle section {key!r}")
    return value


def _verify_signature(
    bundle: dict[str, object], *, require_signed: bool
) -> tuple[str, str | None, tuple[str, ...]]:
    """Check the optional Ed25519 signature over ``integrity.root`` with the
    pure-Python verifier (no extra needed). Returns
    ``(status, public_key, problems)``: an absent signature is ``UNSIGNED``
    with no problem (unless ``require_signed``); a present-but-invalid or
    malformed signature is a named envelope failure (exit 4). Binds the bundle
    to *the holder of this key* — the report carries the key so a consumer can
    compare it to one they trust; key distribution is out of scope (ADR 0032).
    """
    signature = bundle.get("signature")
    if signature is None:
        if require_signed:
            return (
                UNSIGNED,
                None,
                ("the bundle is unsigned, but --require-signed was set",),
            )
        return UNSIGNED, None, ()
    if not isinstance(signature, dict):
        raise BundleFormatError("the signature section is not an object")

    algorithm = signature.get("algorithm")
    public_key_hex = signature.get("public_key")
    signature_hex = signature.get("signature")
    if algorithm != ed25519_ALGORITHM:
        raise BundleFormatError(
            f"unsupported signature algorithm {algorithm!r} (expected "
            f"{ed25519_ALGORITHM!r})"
        )
    if not isinstance(public_key_hex, str) or not isinstance(signature_hex, str):
        raise BundleFormatError("signature.public_key / signature must be hex strings")
    try:
        public_key = bytes.fromhex(public_key_hex)
        sig = bytes.fromhex(signature_hex)
    except ValueError as error:
        raise BundleFormatError(f"signature is not valid hex: {error}") from error
    if len(public_key) != 32 or len(sig) != 64:
        raise BundleFormatError(
            "signature has the wrong length "
            f"(public_key {len(public_key)}B, signature {len(sig)}B; "
            "expected 32B / 64B)"
        )

    integrity = bundle.get("integrity")
    if not isinstance(integrity, dict) or not isinstance(integrity.get("root"), str):
        # No sealed root to verify against — the integrity layer already
        # reports this; the signature simply cannot be checked.
        return (
            SIGNED,
            public_key_hex,
            ("the signature cannot be checked: the bundle carries no sealed root",),
        )
    root_bytes = integrity["root"].encode("utf-8")
    if ed25519_verify(public_key, root_bytes, sig):
        return SIGNED, public_key_hex, ()
    return (
        SIGNED,
        public_key_hex,
        (
            "the signature does not verify against the sealed root — the root was "
            "re-sealed by someone who does not hold this key, or the signature was "
            "altered",
        ),
    )


def _check_format(bundle: dict[str, object]) -> None:
    fmt = _section(bundle, "format")
    if fmt.get("name") != FORMAT_NAME:
        raise BundleFormatError(
            f"not a trust bundle: format.name is {fmt.get('name')!r}"
        )
    if fmt.get("major") != FORMAT_MAJOR:
        raise BundleFormatError(
            f"unsupported format major {fmt.get('major')!r} "
            f"(this verifier reads major {FORMAT_MAJOR})"
        )


def _closure_rederivable(closure: dict[str, object]) -> bool:
    """Whether the closure actually packages a re-derivable corpus — a graph
    with at least one node and a knowledge base. This is a **structural fact**
    about the file's content, not a self-declared label: the verifier decides
    whether it can re-execute from what is present, so an attacker cannot flip
    a ``kind`` string to switch re-execution off (the downgrade attack)."""
    graph = closure.get("graph")
    if not isinstance(graph, dict):
        return False
    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return False
    return isinstance(closure.get("kb"), dict)


def _referential_problems(
    result: GroundedResult, graph: KnowledgeGraph
) -> tuple[str, ...]:
    """Every id the packaged graph and the recorded claims reference must
    resolve to a packaged node. The claim shapes and the router dereference
    node ids directly (``graph.node(id)``), so a dangling reference — a
    deleted cited row, a ghost edge — would otherwise crash re-execution with
    an uncaught ``KeyError`` (an undefined exit outside the 0/2/3/4 taxonomy).
    Checked here so it degrades to a named semantic failure instead. Honest
    bundles reference only packaged nodes across all committed corpora (0
    exceptions), so this never false-fails a genuine bundle.
    """
    node_ids = {node.id for node in graph.nodes}
    problems: list[str] = []
    for edge in graph.edges:
        for role, ref in (("src", edge.src), ("dst", edge.dst)):
            if ref not in node_ids:
                problems.append(
                    f"edge {edge.relation!r} references a {role} node {ref!r} "
                    "absent from the packaged snapshot"
                )
    for res in graph.resolutions:
        for ref in (res.node_a, res.node_b):
            if ref not in node_ids:
                problems.append(
                    f"a resolution references node {ref!r} absent from the "
                    "packaged snapshot"
                )
    for mention in graph.mentions:
        for ref in (mention.chunk, mention.node):
            if ref not in node_ids:
                problems.append(
                    f"a mention references node {ref!r} absent from the "
                    "packaged snapshot"
                )
    for index, claim in enumerate(result.claims):
        for record in claim.support:
            if record.id not in node_ids:
                problems.append(
                    f"claim {index} cites record {record.id!r}, which is absent "
                    "from the packaged evidence snapshot"
                )
    return tuple(dict.fromkeys(problems))  # de-duplicate, order-preserving


def _structural_problems(result: GroundedResult) -> tuple[str, ...]:
    """The exactly-one-mode invariants a recorded result must satisfy."""
    problems: list[str] = []
    if result.grounded == result.refused:
        problems.append(
            "the recorded result violates the exactly-one-mode invariant "
            f"(grounded={result.grounded}, refused={result.refused})"
        )
    if result.refused and result.claims:
        problems.append("the recorded result is a refusal but carries claims")
    if result.refused and not result.refusal:
        problems.append("the recorded result is a refusal without a reason")
    if result.grounded and not result.claims:
        problems.append("the recorded result is grounded but carries no claims")
    if result.grounded and result.refusal is not None:
        problems.append("the recorded result is grounded but carries a refusal")
    return tuple(problems)


# --- the two semantic checks -------------------------------------------------------


def _claim_checks(
    result: GroundedResult,
    graph: KnowledgeGraph,
    shapes: tuple[ClaimShape, ...],
) -> tuple[ClaimCheck, ...]:
    """Check (a): re-run ``is_supported`` for every recorded claim against the
    packaged graph, and compare with the recorded verdict."""
    nodes = {node.id: node for node in graph.nodes}
    checks: list[ClaimCheck] = []
    for index, claim in enumerate(result.claims):
        rederived = is_supported(claim_from_grounded(claim), nodes, graph, shapes)
        cause: str | None = None
        if claim.verified and not rederived:
            cause = (
                f"claim {index} ({claim.text!r}) is recorded verified=true but "
                "does not re-derive from the evidence packaged in this bundle"
            )
        elif not claim.verified and rederived:
            cause = (
                f"claim {index} ({claim.text!r}) re-derives as supported but is "
                "recorded verified=false — the recorded verdict was altered"
            )
        checks.append(
            ClaimCheck(
                index=index,
                text=claim.text,
                recorded=claim.verified,
                rederived=rederived,
                cause=cause,
            )
        )
    return tuple(checks)


def _answer_rederivation(
    stored_result: dict[str, object],
    result: GroundedResult,
    graph: KnowledgeGraph,
    kb: KnowledgeBase,
    domain_name: str,
) -> tuple[bool, str | None]:
    """Check (b): re-run the domain's deterministic router over the packaged
    corpus; the recorded answer must re-derive **exactly**. Returns
    ``(rederives, named_cause)``.

    The equality test compares the recorded result's *canonical bytes*
    against the re-derived answer's — not the reconstructed dataclasses. This
    binds every serialized field, including derived/display ones that
    reconstruction drops (a cited record's ``locator.render`` provenance
    string, the ``all_verified`` summary): those are shipped to be trusted
    without a round-trip, so a fabricated one must not pass. The structured
    fields (mode, route, claim texts, verdicts, evidence ids/sources/parts/
    text) are named first when they diverge; a bytes-only divergence with the
    structure intact is a fabricated display field, named as such.
    """
    dom = domain(domain_name)
    route, answer = dom.route(result.question, graph, kb)
    fresh = serialize_answer(
        answer,
        graph,
        dom.claim_shapes,
        domain=domain_name,
        question=result.question,
        route=route,
    )
    return _fresh_divergence(stored_result, result, fresh)


def _chain_answer_rederivation(
    stored_result: dict[str, object],
    result: GroundedResult,
    graph: KnowledgeGraph,
    kb: KnowledgeBase,
) -> tuple[bool, str | None]:
    """Check (b) for chain bundles (spec 0143 D5): re-run the deterministic
    chain route — the frozen core's lexical retrieval over the derived claim
    records — over the packaged corpus; equality rules identical to the
    domain check."""
    from tessera.bundle.chain import CHAIN_CLAIM_SHAPES, chain_route

    route, answer = chain_route(result.question, graph, kb)
    fresh = serialize_answer(
        answer,
        graph,
        CHAIN_CLAIM_SHAPES,
        domain=CHAIN_DOMAIN,
        question=result.question,
        route=route,
    )
    return _fresh_divergence(stored_result, result, fresh)


def _fresh_divergence(
    stored_result: dict[str, object],
    result: GroundedResult,
    fresh: GroundedResult,
) -> tuple[bool, str | None]:
    """The shared equality rule for check (b): canonical-bytes equality, then
    the first divergence named (mode, refusal, claim texts, metadata, or a
    fabricated derived/display field)."""
    if canonical_bytes(stored_result) == canonical_bytes(fresh.to_dict()):
        return True, None
    # Name the first divergence — the packaged corpus does not yield this answer.
    if fresh.refused != result.refused:
        return False, (
            "the packaged corpus does not re-derive the recorded answer: it "
            f"yields a {'refusal' if fresh.refused else 'grounded answer'} for "
            "this question, but the bundle records the opposite mode"
        )
    if fresh.refusal != result.refusal:
        return False, (
            "the recorded refusal reason does not re-derive: the packaged "
            f"corpus yields {fresh.refusal!r}, the bundle records "
            f"{result.refusal!r}"
        )
    if [c.text for c in fresh.claims] != [c.text for c in result.claims]:
        return False, (
            "the recorded claims are not the answer this packaged corpus "
            "yields for this question (claim texts diverge) — the claims, "
            "the question, or the evidence they rest on were altered"
        )
    if fresh != result:
        return False, (
            "the recorded answer does not re-derive from the packaged corpus "
            "(route or verdict metadata diverges)"
        )
    return False, (
        "a derived field in the recorded result — a provenance render string "
        "or the all_verified summary — does not match the re-derived answer; "
        "the displayed provenance was fabricated"
    )


# --- action re-derivation (spec 0136) ----------------------------------------------


def _action_problems(
    action_section: dict[str, object],
    result: GroundedResult,
) -> tuple[str, ...]:
    """Re-derive the WHOLE wire action from the re-derived answer (spec 0136).

    The strong check — the action-layer analogue of the answer re-derivation
    (b): re-run the frozen drafting + rendering pipeline over the re-derived
    ``result`` (bound to the packaged evidence by check (b)) and require the
    recorded receipt's request and slots to equal it **exactly**. Because the
    frozen pipeline is a deterministic function of the answer, this binds the
    method, path, the *entire* body dict (every key — labels, and anything an
    attacker might inject), the per-slot value→claim→role attribution, and the
    slot order all at once. Anything the receipt added or altered beyond what
    the evidence produces diverges and fails. Pure over the file's content;
    the actuator and network are never touched (the adversarial review of
    unit 0136 found the earlier field-by-field check let injected body keys,
    a repointed method/path, and cross-claim splices pass — this closes them).
    """
    from tessera.agent.actions import _CATALOG, ActionProposal, _draft_fields
    from tessera.agent.payloads import render_payload
    from tessera.bundle.serde import execution_receipt_from_dict

    try:
        receipt = execution_receipt_from_dict(action_section)
    except ValueError as error:
        return (f"the action section is malformed: {error}",)

    problems: list[str] = []
    if receipt.sent:
        problems.append(
            "the bundled action claims a real send (sent=true); only simulated "
            "actions are ever bundled"
        )
    if receipt.domain != result.domain or receipt.question != result.question:
        problems.append(
            "the action records a different domain/question than the answer it rests on"
        )

    kind = _CATALOG.get(receipt.kind)
    if kind is None:
        return tuple(
            dict.fromkeys([*problems, f"unknown action kind {receipt.kind!r}"])
        )
    if result.domain not in kind.domains:
        return tuple(
            dict.fromkeys(
                [
                    *problems,
                    f"the {receipt.kind!r} action does not apply to "
                    f"domain {result.domain!r}",
                ]
            )
        )
    if result.route_kind != kind.required_route:
        return tuple(
            dict.fromkeys(
                [
                    *problems,
                    f"the {receipt.kind!r} action requires route "
                    f"{kind.required_route!r}, but the answer routed to "
                    f"{result.route_kind!r}",
                ]
            )
        )

    # Re-derive the exact wire request the frozen pipeline produces from this
    # answer, then re-run the SIMULATED execution over it and require the WHOLE
    # recorded receipt to match — the request AND the execution-outcome metadata
    # (outcome, result, simulated/executed/actuator, approval). The adversarial
    # audit of M20/M21 found that binding only the request let a receipt claim a
    # real create (outcome="created", simulated=false, a fabricated result URL)
    # while passing; comparing the full simulated receipt closes that, since a
    # bundled action is only ever an unapproved, unsent simulation.
    from tessera.agent.execution import execute_payload

    proposal = ActionProposal(
        kind=receipt.kind,
        domain=result.domain,
        question=result.question,
        route_kind=result.route_kind,
        route_reason=result.route_reason,
        grounded=True,
        refused=False,
        refusal=None,
        fields=tuple(_draft_fields(kind, result)),
    )
    expected = render_payload(proposal)
    if not expected.rendered:
        problems.append(
            "the packaged evidence does not re-derive a grounded wire request "
            "for this action (the frozen pipeline withholds it)"
        )
        return tuple(dict.fromkeys(problems))

    expected_receipt = execute_payload(expected)  # SimulatedActuator, no approval
    expected_d = expected_receipt.to_dict()
    recorded_d = receipt.to_dict()
    if recorded_d != expected_d:
        named = False
        if receipt.method != expected_receipt.method or receipt.path != (
            expected_receipt.path
        ):
            problems.append(
                "the wire method/path does not match the request re-derived from "
                "the packaged evidence"
            )
            named = True
        if receipt.body != expected_receipt.body:
            problems.append(
                "the wire body does not match the request re-derived from the "
                "packaged evidence — it adds or alters content beyond the "
                "grounded values"
            )
            named = True
        if recorded_d["slots"] != expected_d["slots"]:
            problems.append(
                "the wire slots do not match those re-derived from the packaged "
                "evidence (a value, its provenance, or its role was altered)"
            )
            named = True
        outcome_keys = (
            "target",
            "actuator",
            "executed",
            "simulated",
            "withheld",
            "withheld_reason",
            "outcome",
            "result",
            "idempotency_key",
            "approved",
            "requires_approval",
        )
        diverged = [k for k in outcome_keys if recorded_d.get(k) != expected_d.get(k)]
        if diverged:
            problems.append(
                "the action's execution outcome does not match a simulated draft "
                f"(altered {', '.join(diverged)}) — a bundled action is an "
                "unapproved, unsent simulation, not an executed one"
            )
            named = True
        if not named:
            # Safety net: the recorded receipt differs from the re-derived one in
            # a field none of the named checks covers — never a silent pass.
            problems.append(
                "the action receipt does not match the one re-derived from the "
                "packaged evidence"
            )
    return tuple(dict.fromkeys(problems))


# --- the chain layer (spec 0143) ---------------------------------------------------


def _short_root(root: str) -> str:
    """A readable root prefix for named causes: ``sha256:`` + 12 hex chars."""
    return root[:19] + "…" if len(root) > 20 else root


def _chain_problems(
    closure: dict[str, object], kb: KnowledgeBase
) -> tuple[tuple[UpstreamCheck, ...], tuple[str, ...]]:
    """The chain checks (spec 0143 D5, ADR 0033): recursively re-verify every
    embedded upstream with the FULL verifier — recorded verdicts are never
    trusted — then require every derived record to byte-match the upstream
    claim it cites, and that claim to have re-derived in the upstream's own
    re-execution. Every failure is a named semantic problem (exit 2)."""
    problems: list[str] = []
    checks: list[UpstreamCheck] = []
    passing: dict[str, tuple[dict[str, object], VerifyReport]] = {}

    raw = closure.get("upstream")
    if not isinstance(raw, list):
        problems.append("the chain closure carries no upstream list")
        raw = []

    for position, item in enumerate(raw):
        if not isinstance(item, dict):
            problems.append(f"upstream[{position}] is not a bundle object")
            continue
        integrity = item.get("integrity")
        root = integrity.get("root") if isinstance(integrity, dict) else None
        root_name = root if isinstance(root, str) else f"upstream[{position}]"
        try:
            sub = verify_bundle(item)
        except BundleFormatError as error:
            problems.append(
                f"embedded upstream {_short_root(root_name)} cannot be "
                f"verified: {error}"
            )
            checks.append(
                UpstreamCheck(root=root_name, verdict="TAMPERED", cause=str(error))
            )
            continue
        cause: str | None = None
        if sub.verdict == "PASS":
            passing[root_name] = (item, sub)
        else:
            cause = (
                sub.taxonomy_reason
                or next(iter(sub.semantic_problems), None)
                or next(iter(sub.envelope_problems), None)
                or sub.verdict
            )
            problems.append(
                f"embedded upstream {_short_root(root_name)} does not "
                f"re-verify ({sub.verdict}): {cause}"
            )
        checks.append(
            UpstreamCheck(
                root=root_name,
                verdict=sub.verdict,
                cause=cause,
                signature_status=sub.signature_status,
                signer=sub.signature_public_key,
            )
        )

    for record in kb.records:
        locator = record.origin.locator
        parts = dict(locator.parts)
        cited_root = parts.get("bundle")
        cited_index = parts.get("claim")
        if locator.kind != "bundle-claim" or cited_root is None or cited_index is None:
            problems.append(
                f"chain record {record.id!r} does not cite an upstream claim "
                "(a chain corpus may contain nothing else)"
            )
            continue
        if cited_root not in passing:
            problems.append(
                f"chain record {record.id!r} cites upstream "
                f"{_short_root(cited_root)}, which is not embedded-and-passing "
                "in this bundle"
            )
            continue
        upstream, sub = passing[cited_root]
        result_section = upstream.get("result")
        claims_raw = (
            result_section.get("claims") if isinstance(result_section, dict) else None
        )
        claims_list = claims_raw if isinstance(claims_raw, list) else []
        index = int(cited_index) if cited_index.isdigit() else -1
        if not 0 <= index < len(claims_list):
            problems.append(
                f"chain record {record.id!r} cites claim {cited_index!r} of "
                f"{_short_root(cited_root)}, which does not exist"
            )
            continue
        upstream_claim = claims_list[index]
        claim_dict = upstream_claim if isinstance(upstream_claim, dict) else {}
        if claim_dict.get("text") != record.text:
            problems.append(
                f"chain record {record.id!r} does not match upstream claim "
                f"{index} of {_short_root(cited_root)} — the cited text was "
                "altered"
            )
            continue
        if claim_dict.get("verified") is not True:
            problems.append(
                f"chain record {record.id!r} cites upstream claim {index} of "
                f"{_short_root(cited_root)}, which is not a verifier-passing "
                "claim"
            )
            continue
        if index >= len(sub.claims) or not sub.claims[index].rederived:
            problems.append(
                f"chain record {record.id!r} cites upstream claim {index} of "
                f"{_short_root(cited_root)}, which does not re-derive from its "
                "own packaged evidence"
            )
    return tuple(checks), tuple(problems)


# --- the verifier ------------------------------------------------------------------


def verify_bundle(
    bundle: dict[str, object], *, require_signed: bool = False
) -> VerifyReport:
    """Verify one parsed bundle, both layers. Raises
    :class:`BundleFormatError` when the envelope is unreadable. With
    ``require_signed``, an unsigned bundle is an envelope failure (exit 4)."""
    # Bundle-native chain grammars (spec 0143); imported here, not at module
    # level, to keep the bundle-layer import graph acyclic and shallow.
    from tessera.bundle.chain import CHAIN_CLAIM_SHAPES

    _check_format(bundle)
    # The anchor section is reserved for transparency-log anchoring (unit 0138)
    # and has no verifier yet. It is an attestation OVER the root, so it is not
    # in the integrity manifest; until 0138 gives it meaning, a non-null anchor
    # is unverifiable content this version must refuse rather than ignore (the
    # M20/M21 audit found it could otherwise ride along unauthenticated).
    if bundle.get("anchor") is not None:
        raise BundleFormatError(
            "the anchor section is reserved and not verifiable by this version "
            "(transparency anchoring arrives in a later unit)"
        )
    engine = _section(bundle, "engine")
    closure = _section(bundle, "evidence_closure")

    try:
        integrity = tuple(integrity_mismatches(bundle))
    except ValueError as error:
        raise BundleFormatError(str(error)) from error

    signature_status, signature_public_key, signature_problems = _verify_signature(
        bundle, require_signed=require_signed
    )

    domain_name = engine.get("domain")
    if not isinstance(domain_name, str):
        raise BundleFormatError("engine.domain is missing or not a string")
    sealed_under = engine.get("tessera_version")
    if not isinstance(sealed_under, str):
        raise BundleFormatError("engine.tessera_version is missing or not a string")
    installed = engine_version()

    try:
        result = grounded_result_from_dict(_section(bundle, "result"))
    except ValueError as error:
        raise BundleFormatError(f"malformed result section: {error}") from error

    structural = list(_structural_problems(result))
    if result.domain != domain_name:
        structural.append(
            f"the recorded result names domain {result.domain!r} but the "
            f"bundle was sealed for {domain_name!r}"
        )

    # --- taxonomy: can the installed engine honestly judge this bundle? ---
    # The chain domain is bundle-native (spec 0143 D5): it never enters the
    # GroundedDomain registry, declares no claim shapes, and re-executes via
    # the chain route — so its gate replaces registry membership only.
    taxonomy = RE_DERIVED
    reason: str | None = None
    if domain_name != CHAIN_DOMAIN and domain_name not in available_domains():
        taxonomy, reason = (
            NOT_EVALUABLE,
            (
                f"unknown domain {domain_name!r} — this engine knows "
                f"{', '.join(available_domains())} and chain bundles"
            ),
        )
    elif sealed_under != installed:
        taxonomy, reason = (
            NOT_EVALUABLE,
            (
                f"sealed under tessera {sealed_under}, installed {installed} — "
                "re-deriving under a different engine version would be a "
                "different verdict wearing the same name (ADR 0031); verify "
                "with the sealed version"
            ),
        )
    else:
        recorded_shapes = engine.get("claim_shapes")
        installed_shapes = shape_identifiers(
            CHAIN_CLAIM_SHAPES
            if domain_name == CHAIN_DOMAIN
            else domain(domain_name).claim_shapes
        )
        if recorded_shapes != installed_shapes:
            taxonomy, reason = (
                NOT_EVALUABLE,
                (
                    f"claim-shape identifiers diverge — sealed: {recorded_shapes!r}, "
                    f"installed: {installed_shapes!r}"
                ),
            )
        elif not _closure_rederivable(closure):
            # Genuinely partial: no full graph is packaged, so the verdicts
            # cannot be re-executed — hashes are all this can check. Note this
            # is decided on what is PRESENT, never on the self-declared kind,
            # so the label cannot suppress a re-execution the evidence allows.
            taxonomy, reason = (
                INTEGRITY_ONLY,
                (
                    "the evidence closure does not package a re-derivable graph "
                    f"(closure kind {closure.get('kind')!r}): hashes are checked, "
                    "but the verdicts cannot be re-executed from what is present"
                ),
            )

    claims: tuple[ClaimCheck, ...] = ()
    upstreams: tuple[UpstreamCheck, ...] = ()
    answer_rederives: bool | None = None
    answer_cause: str | None = None
    if taxonomy == RE_DERIVED:
        try:
            graph = graph_from_dict(_section(closure, "graph"))
            kb = kb_from_dict(_section(closure, "kb"))
        except ValueError as error:
            raise BundleFormatError(f"malformed evidence closure: {error}") from error
        # A full re-derivable graph is present, so re-execution runs regardless
        # of the kind label. If the label nonetheless claims a different
        # closure, that inconsistency is itself a semantic failure — the
        # downgrade attack (relabel to suppress a check) is caught, not obeyed.
        expected_kind = (
            CLOSURE_CHAIN if domain_name == CHAIN_DOMAIN else CLOSURE_FULL_SNAPSHOT
        )
        if closure.get("kind") != expected_kind:
            structural.append(
                f"the closure kind {closure.get('kind')!r} does not match the "
                f"sealed domain (expected {expected_kind!r}) — the label "
                "cannot suppress re-execution"
            )
        referential = _referential_problems(result, graph)
        if referential:
            # A dangling reference would crash re-execution; report it as a
            # named semantic failure and do not attempt the checks that assume
            # a referentially-consistent graph.
            structural.extend(referential)
        else:
            try:
                if domain_name == CHAIN_DOMAIN:
                    # The chain layer: recursive upstream re-verification plus
                    # the record↔upstream-claim cross-checks (spec 0143 D5).
                    upstreams, chain_problems = _chain_problems(closure, kb)
                    structural.extend(chain_problems)
                    claims = _claim_checks(result, graph, CHAIN_CLAIM_SHAPES)
                    answer_rederives, answer_cause = _chain_answer_rederivation(
                        _section(bundle, "result"), result, graph, kb
                    )
                else:
                    dom = domain(domain_name)
                    claims = _claim_checks(result, graph, dom.claim_shapes)
                    answer_rederives, answer_cause = _answer_rederivation(
                        _section(bundle, "result"), result, graph, kb, domain_name
                    )
                # An action bundle also re-derives its wire request (spec 0136).
                action_section = bundle.get("action")
                if isinstance(action_section, dict):
                    structural.extend(_action_problems(action_section, result))
            except Exception as error:  # noqa: BLE001 - backstop, see below
                # Defensive backstop: re-execution must never escape as an
                # uncaught exception (the command runs on strangers' machines).
                # Any surprise becomes a named semantic failure — a defined,
                # visible non-PASS verdict — not a crash.
                structural.append(
                    "re-execution failed on the packaged evidence "
                    f"({type(error).__name__}: {error}); the bundle's content "
                    "is internally inconsistent"
                )
                answer_rederives = False
                answer_cause = None

    return VerifyReport(
        domain=domain_name,
        sealed_under=sealed_under,
        installed=installed,
        taxonomy=taxonomy,
        taxonomy_reason=reason,
        integrity_problems=integrity,
        signature_status=signature_status,
        signature_public_key=signature_public_key,
        signature_problems=signature_problems,
        structural_problems=tuple(structural),
        claims=claims,
        answer_rederives=answer_rederives,
        answer_cause=answer_cause,
        refused=result.refused,
        upstreams=upstreams,
    )


# --- human-readable rendering --------------------------------------------------------


def render_report(report: VerifyReport, *, source: str) -> str:
    """The human-facing report: both layers, named causes, honest verdict."""
    lines = [f"bundle:    {source} — {FORMAT_NAME} v{FORMAT_MAJOR}"]
    lines.append(
        f"engine:    domain {report.domain}, sealed under tessera "
        f"{report.sealed_under} (installed: {report.installed})"
    )

    if report.integrity_problems:
        lines.append(f"integrity: BROKEN — {len(report.integrity_problems)} problem(s)")
        lines.extend(f"  ! {p}" for p in report.integrity_problems)
    else:
        lines.append("integrity: intact — every leaf and the root re-computed")

    if report.signature_status == UNSIGNED and not report.signature_problems:
        lines.append(
            "signature: UNSIGNED — integrity proves the file is the file, "
            "not who made it"
        )
    elif report.signature_problems:
        lines.append("signature: BROKEN")
        lines.extend(f"  ! {p}" for p in report.signature_problems)
    else:
        lines.append(
            f"signature: valid — signed by key {report.signature_public_key} "
            "(compare it to a key you trust)"
        )

    if report.taxonomy != RE_DERIVED:
        lines.append(f"semantic:  {report.taxonomy} — {report.taxonomy_reason}")
    else:
        if report.refused:
            lines.append("semantic:  RE-DERIVED — the recorded outcome is a refusal")
        else:
            matched = sum(1 for c in report.claims if c.matches)
            lines.append(
                f"semantic:  RE-DERIVED — {matched}/{len(report.claims)} recorded "
                "claim verdict(s) re-executed and matched"
            )
            for check in report.claims:
                mark = "ok" if check.matches and check.rederived else "!!"
                state = "supported" if check.rederived else "UNSUPPORTED"
                lines.append(f"  [{mark}] claim {check.index}: {state} — {check.text}")
        if report.upstreams:
            passing = sum(1 for u in report.upstreams if u.verdict == "PASS")
            lines.append(
                f"chain:     {passing}/{len(report.upstreams)} embedded "
                "upstream bundle(s) re-verified recursively"
            )
            for upstream in report.upstreams:
                mark = "ok" if upstream.verdict == "PASS" else "!!"
                suffix = f" — {upstream.cause}" if upstream.cause else ""
                lines.append(
                    f"  [{mark}] upstream {_short_root(upstream.root)}: "
                    f"{upstream.verdict}{suffix}"
                )
        if report.answer_rederives:
            lines.append(
                "answer:    re-derives — the packaged corpus yields exactly "
                "this answer for this question"
            )
        elif report.answer_rederives is False:
            lines.append(f"answer:    DOES NOT RE-DERIVE — {report.answer_cause}")

    for problem in report.structural_problems:
        lines.append(f"  ! {problem}")

    lines.append(f"verdict:   {report.verdict} (exit {report.exit_code})")
    return "\n".join(lines)
