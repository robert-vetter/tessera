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
from tessera.bundle.emit import engine_version, shape_identifiers
from tessera.bundle.format import (
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
class VerifyReport:
    """The full two-layer verification result of one bundle."""

    domain: str
    sealed_under: str
    installed: str
    taxonomy: str
    taxonomy_reason: str | None
    integrity_problems: tuple[str, ...]
    structural_problems: tuple[str, ...]
    claims: tuple[ClaimCheck, ...]
    answer_rederives: bool | None
    answer_cause: str | None
    refused: bool

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
        if self.integrity_problems:
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
            "structural_problems": list(self.structural_problems),
            "claims": [c.to_dict() for c in self.claims],
            "answer_rederives": self.answer_rederives,
            "answer_cause": self.answer_cause,
            "refused": self.refused,
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


# --- the verifier ------------------------------------------------------------------


def verify_bundle(bundle: dict[str, object]) -> VerifyReport:
    """Verify one parsed bundle, both layers. Raises
    :class:`BundleFormatError` when the envelope is unreadable."""
    _check_format(bundle)
    engine = _section(bundle, "engine")
    closure = _section(bundle, "evidence_closure")

    try:
        integrity = tuple(integrity_mismatches(bundle))
    except ValueError as error:
        raise BundleFormatError(str(error)) from error

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
    taxonomy = RE_DERIVED
    reason: str | None = None
    if domain_name not in available_domains():
        taxonomy, reason = (
            NOT_EVALUABLE,
            (
                f"unknown domain {domain_name!r} — this engine knows "
                f"{', '.join(available_domains())}"
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
        installed_shapes = shape_identifiers(domain(domain_name).claim_shapes)
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
    answer_rederives: bool | None = None
    answer_cause: str | None = None
    if taxonomy == RE_DERIVED:
        try:
            graph = graph_from_dict(_section(closure, "graph"))
            kb = kb_from_dict(_section(closure, "kb"))
        except ValueError as error:
            raise BundleFormatError(f"malformed evidence closure: {error}") from error
        # A full re-derivable graph is present, so re-execution runs regardless
        # of the kind label. If the label nonetheless claims a partial closure,
        # that inconsistency is itself a semantic failure — the downgrade
        # attack (relabel to suppress the check) is caught, not silently obeyed.
        if closure.get("kind") != CLOSURE_FULL_SNAPSHOT:
            structural.append(
                f"the closure kind {closure.get('kind')!r} claims a partial "
                f"closure, but a full re-derivable graph is packaged (expected "
                f"{CLOSURE_FULL_SNAPSHOT!r}) — the label cannot suppress "
                "re-execution"
            )
        referential = _referential_problems(result, graph)
        if referential:
            # A dangling reference would crash re-execution; report it as a
            # named semantic failure and do not attempt the checks that assume
            # a referentially-consistent graph.
            structural.extend(referential)
        else:
            dom = domain(domain_name)
            try:
                claims = _claim_checks(result, graph, dom.claim_shapes)
                answer_rederives, answer_cause = _answer_rederivation(
                    _section(bundle, "result"), result, graph, kb, domain_name
                )
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
        structural_problems=tuple(structural),
        claims=claims,
        answer_rederives=answer_rederives,
        answer_cause=answer_cause,
        refused=result.refused,
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
