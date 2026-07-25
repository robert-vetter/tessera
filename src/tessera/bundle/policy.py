"""Trust policies — the auditor's rules, re-executed at verify time (spec 0144).

A policy is a small, versioned JSON document of deterministic rules a
verifying party owns: `tessera verify decision.tsb --policy rules.json`
evaluates every rule against the sealed bundle and the verifier's own
re-execution report — PASS or VIOLATED per rule, each with a named detail,
offline, from the two files alone.

Two properties are load-bearing (ADR 0034):

- **Policy-at-verify, never policy-in-bundle.** A bundle that self-attests
  compliance is a rubber stamp. The policy is the *auditor's* document,
  applied to evidence sealed without knowing which policy it would face.
- **Fail-closed.** An unknown rule key, a malformed value, or an unreadable
  file refuses evaluation with a named :class:`PolicyError` — a typo in a
  guardrail must surface as a refusal, never as a silent pass.

COMPLIANT means exactly: this policy (name + canonical sha256), these
rules, this file. It is not correctness, not legal compliance, not
certification — the rendered output says so verbatim, and a test pins it.

Pure stdlib and offline, like every trust-path module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

from tessera.bundle.canonical import digest
from tessera.bundle.verify import RE_DERIVED, SIGNED, VerifyReport

SCOPE_LINE = (
    "COMPLIANT means: this policy, these rules, this file — not correctness, "
    "not legal compliance, not certification."
)

_TOP_KEYS = frozenset({"name", "version", "rules"})
_RULE_KEYS = (
    "require_signed",
    "allowed_signers",
    "require_rederived",
    "forbid_unverified_claims",
    "allowed_evidence_sources",
    "actions",
    "chain",
    "approvals",
    "redaction",
)
_ACTION_KEYS = ("allow", "require_approval_gate", "forbid_real_send")
_CHAIN_KEYS = ("max_depth", "require_signed_upstreams", "allowed_upstream_signers")
_APPROVAL_KEYS = ("require", "allowed_approvers", "distinct_approvers")
_REDACTION_KEYS = ("allow", "max_withheld")


class PolicyError(ValueError):
    """The policy cannot be evaluated — unreadable, unknown rule, or
    malformed value. Fail-closed: never a silent pass."""


@dataclass(frozen=True)
class PolicyCheck:
    """One rule's outcome: PASS or VIOLATED, with a named detail."""

    rule: str
    ok: bool
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {"rule": self.rule, "ok": self.ok, "detail": self.detail}


@dataclass(frozen=True)
class PolicyReport:
    """Every rule's outcome under one policy, tied to the exact policy text
    by its canonical sha256."""

    name: str
    version: int
    policy_digest: str
    checks: tuple[PolicyCheck, ...]

    @property
    def compliant(self) -> bool:
        return all(check.ok for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "policy_digest": self.policy_digest,
            "checks": [check.to_dict() for check in self.checks],
            "compliant": self.compliant,
            "scope": SCOPE_LINE,
        }


# --- loading (fail-closed) --------------------------------------------------------


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PolicyError(message)


def _validate_bool(rules: dict[str, object], key: str) -> None:
    if key in rules:
        _require(isinstance(rules[key], bool), f"rule {key!r} must be true/false")


def _validate_str_list(rules: dict[str, object], key: str) -> None:
    if key in rules:
        value = rules[key]
        _require(
            isinstance(value, list)
            and bool(value)
            and all(isinstance(item, str) for item in value),
            f"rule {key!r} must be a non-empty list of strings",
        )


def validate_policy(policy: object) -> dict[str, object]:
    """Validate a parsed policy document, fail-closed. Returns it typed."""
    _require(isinstance(policy, dict), "a policy must be a JSON object")
    assert isinstance(policy, dict)
    unknown_top = set(policy) - _TOP_KEYS
    _require(not unknown_top, f"unknown policy key(s) {sorted(unknown_top)}")
    name = policy.get("name")
    _require(isinstance(name, str) and bool(name), "policy 'name' must be a string")
    version = policy.get("version")
    _require(
        isinstance(version, int) and not isinstance(version, bool),
        "policy 'version' must be an integer",
    )
    rules = policy.get("rules")
    _require(
        isinstance(rules, dict) and bool(rules),
        "policy 'rules' must be a non-empty object",
    )
    assert isinstance(rules, dict)

    unknown = set(rules) - set(_RULE_KEYS)
    _require(
        not unknown,
        f"unknown rule(s) {sorted(unknown)} — refusing to evaluate (a typo "
        "must never pass as compliant)",
    )
    _validate_bool(rules, "require_signed")
    _validate_bool(rules, "require_rederived")
    _validate_bool(rules, "forbid_unverified_claims")
    _validate_str_list(rules, "allowed_signers")
    _validate_str_list(rules, "allowed_evidence_sources")

    actions = rules.get("actions")
    if actions is not None:
        _require(isinstance(actions, dict), "rule 'actions' must be an object")
        assert isinstance(actions, dict)
        unknown_a = set(actions) - set(_ACTION_KEYS)
        _require(not unknown_a, f"unknown actions rule(s) {sorted(unknown_a)}")
        for key in _ACTION_KEYS:
            _validate_bool(actions, key)

    chain = rules.get("chain")
    if chain is not None:
        _require(isinstance(chain, dict), "rule 'chain' must be an object")
        assert isinstance(chain, dict)
        unknown_c = set(chain) - set(_CHAIN_KEYS)
        _require(not unknown_c, f"unknown chain rule(s) {sorted(unknown_c)}")
        if "max_depth" in chain:
            depth = chain["max_depth"]
            _require(
                isinstance(depth, int) and not isinstance(depth, bool) and depth >= 0,
                "chain rule 'max_depth' must be a non-negative integer",
            )
        _validate_bool(chain, "require_signed_upstreams")
        _validate_str_list(chain, "allowed_upstream_signers")

    approvals = rules.get("approvals")
    if approvals is not None:
        _require(isinstance(approvals, dict), "rule 'approvals' must be an object")
        assert isinstance(approvals, dict)
        unknown_ap = set(approvals) - set(_APPROVAL_KEYS)
        _require(not unknown_ap, f"unknown approvals rule(s) {sorted(unknown_ap)}")
        if "require" in approvals:
            count = approvals["require"]
            _require(
                isinstance(count, int) and not isinstance(count, bool) and count >= 1,
                "approvals rule 'require' must be a positive integer",
            )
        _validate_str_list(approvals, "allowed_approvers")
        _validate_bool(approvals, "distinct_approvers")

    redaction = rules.get("redaction")
    if redaction is not None:
        _require(isinstance(redaction, dict), "rule 'redaction' must be an object")
        assert isinstance(redaction, dict)
        unknown_r = set(redaction) - set(_REDACTION_KEYS)
        _require(not unknown_r, f"unknown redaction rule(s) {sorted(unknown_r)}")
        _validate_bool(redaction, "allow")
        if "max_withheld" in redaction:
            limit = redaction["max_withheld"]
            _require(
                isinstance(limit, int) and not isinstance(limit, bool) and limit >= 0,
                "redaction rule 'max_withheld' must be a non-negative integer",
            )
    return policy


def load_policy(path: Path) -> dict[str, object]:
    """Read and validate a policy file, fail-closed with named errors."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise PolicyError(f"cannot read policy {path}: {error}") from error
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise PolicyError(f"policy {path} is not valid JSON: {error}") from error
    return validate_policy(parsed)


# --- evaluation -------------------------------------------------------------------


def chain_depth(bundle: dict[str, object]) -> int:
    """The embedded-upstream nesting depth: 0 for a single-decision bundle,
    1 + the deepest embedded chain otherwise. Walked defensively on the
    bundle structure (the structure is integrity-committed)."""
    closure = bundle.get("evidence_closure")
    upstream = closure.get("upstream") if isinstance(closure, dict) else None
    if not isinstance(upstream, list) or not upstream:
        return 0
    return 1 + max(
        (chain_depth(item) for item in upstream if isinstance(item, dict)),
        default=0,
    )


def _cited_sources(bundle: dict[str, object]) -> list[str]:
    """Every cited support source in the recorded result, in claim order."""
    result = bundle.get("result")
    claims = result.get("claims") if isinstance(result, dict) else None
    sources: list[str] = []
    for claim in claims if isinstance(claims, list) else []:
        support = claim.get("support") if isinstance(claim, dict) else None
        for entry in support if isinstance(support, list) else []:
            source = entry.get("source") if isinstance(entry, dict) else None
            if isinstance(source, str):
                sources.append(source)
    return sources


def _signed(report: VerifyReport) -> bool:
    return report.signature_status == SIGNED and not report.signature_problems


def evaluate_policy(
    policy: dict[str, object], bundle: dict[str, object], report: VerifyReport
) -> PolicyReport:
    """Evaluate a validated policy against a bundle and its verification
    report. Pure and deterministic; every rule yields a named outcome."""
    rules = policy["rules"]
    assert isinstance(rules, dict)
    checks: list[PolicyCheck] = []

    def add(rule: str, ok: bool, detail: str) -> None:
        checks.append(PolicyCheck(rule=rule, ok=ok, detail=detail))

    if rules.get("require_signed"):
        add(
            "require_signed",
            _signed(report),
            (
                f"signed by key {report.signature_public_key}"
                if _signed(report)
                else "the bundle is unsigned (or its signature does not verify)"
            ),
        )

    signers = rules.get("allowed_signers")
    if isinstance(signers, list):
        if not _signed(report):
            add(
                "allowed_signers",
                False,
                "the bundle is unsigned — no signer to check against the list",
            )
        else:
            ok = report.signature_public_key in signers
            add(
                "allowed_signers",
                ok,
                (
                    f"signer {report.signature_public_key} is "
                    f"{'on' if ok else 'NOT on'} the allowed list"
                ),
            )

    if rules.get("require_rederived"):
        ok = report.taxonomy == RE_DERIVED
        add(
            "require_rederived",
            ok,
            (
                "the verdicts were re-executed from the packaged evidence"
                if ok
                else f"not re-derived here: {report.taxonomy}"
                + (f" ({report.taxonomy_reason})" if report.taxonomy_reason else "")
            ),
        )

    if rules.get("forbid_unverified_claims"):
        offending = [c.index for c in report.claims if not (c.matches and c.rederived)]
        add(
            "forbid_unverified_claims",
            not offending,
            (
                f"all {len(report.claims)} recorded claim(s) re-derive and match"
                if not offending
                else f"claim(s) {offending} do not re-derive/match"
            ),
        )

    patterns = rules.get("allowed_evidence_sources")
    if isinstance(patterns, list):
        sources = _cited_sources(bundle)
        # fnmatchcase, not fnmatch: fnmatch is case-insensitive on Windows
        # (os.path.normcase), and a policy verdict must not depend on the
        # verifier's OS.
        bad = sorted(
            {
                s
                for s in sources
                if not any(fnmatchcase(s, pattern) for pattern in patterns)
            }
        )
        add(
            "allowed_evidence_sources",
            not bad,
            (
                f"all {len(sources)} cited source(s) match the allowlist"
                if not bad
                else f"cited source(s) outside the allowlist: {bad}"
            ),
        )

    actions = rules.get("actions")
    if isinstance(actions, dict):
        action = bundle.get("action")
        has_action = isinstance(action, dict)
        if actions.get("allow") is False:
            add(
                "actions.allow",
                not has_action,
                (
                    "no action packaged — a read-only decision"
                    if not has_action
                    else "the bundle packages an action, but the policy forbids them"
                ),
            )
        if actions.get("require_approval_gate"):
            if not has_action:
                add(
                    "actions.require_approval_gate",
                    True,
                    "no action packaged — the gate rule is vacuously satisfied",
                )
            else:
                assert isinstance(action, dict)
                ok = action.get("requires_approval") is True
                add(
                    "actions.require_approval_gate",
                    ok,
                    (
                        "the action records requires_approval=true"
                        if ok
                        else "the action does NOT record an approval requirement"
                    ),
                )
        if actions.get("forbid_real_send"):
            if not has_action:
                add(
                    "actions.forbid_real_send",
                    True,
                    "no action packaged — nothing was sent",
                )
            else:
                assert isinstance(action, dict)
                ok = action.get("sent") is False and action.get("simulated") is True
                add(
                    "actions.forbid_real_send",
                    ok,
                    (
                        "the action is a simulated draft (sent=false)"
                        if ok
                        else "the action records a real send or a non-simulated run"
                    ),
                )

    chain = rules.get("chain")
    if isinstance(chain, dict):
        depth = chain_depth(bundle)
        if "max_depth" in chain:
            limit = chain["max_depth"]
            assert isinstance(limit, int)
            add(
                "chain.max_depth",
                depth <= limit,
                f"embedded chain depth {depth} (limit {limit})",
            )
        # Fail-closed guard for the upstream rules: if upstreams exist but
        # the chain layer did not run (a degraded/not-evaluable bundle),
        # their signatures were never recursively checked — that is a
        # violation, not a vacuous pass.
        upstream_rules = ("require_signed_upstreams", "allowed_upstream_signers")
        if any(key in chain for key in upstream_rules):
            unchecked = depth > 0 and not report.upstreams
            if chain.get("require_signed_upstreams"):
                unsigned = [
                    u.root for u in report.upstreams if u.signature_status != SIGNED
                ]
                ok = not unchecked and not unsigned
                add(
                    "chain.require_signed_upstreams",
                    ok,
                    (
                        "the chain was not re-executed here — upstream "
                        "signatures could not be checked"
                        if unchecked
                        else (
                            f"all {len(report.upstreams)} upstream(s) signed"
                            if ok
                            else f"unsigned upstream(s): {unsigned}"
                        )
                    ),
                )
            allowed = chain.get("allowed_upstream_signers")
            if isinstance(allowed, list):
                offenders = [
                    u.root
                    for u in report.upstreams
                    if u.signature_status != SIGNED or u.signer not in allowed
                ]
                ok = not unchecked and not offenders
                add(
                    "chain.allowed_upstream_signers",
                    ok,
                    (
                        "the chain was not re-executed here — upstream "
                        "signers could not be checked"
                        if unchecked
                        else (
                            "every upstream is signed by an allowed key"
                            if ok
                            else "upstream(s) not signed by an allowed key: "
                            + repr(offenders)
                        )
                    ),
                )

    approval_rules = rules.get("approvals")
    if isinstance(approval_rules, dict):
        # Approvals inform; this rule group enforces (spec 0145). Only VALID
        # approvals count — and only allowed ones when the list is given.
        valid = [a for a in report.approvals if a.valid]
        allowed_keys = approval_rules.get("allowed_approvers")
        if isinstance(allowed_keys, list):
            outsiders = sorted(
                {a.approver for a in valid if a.approver not in allowed_keys}
            )
            add(
                "approvals.allowed_approvers",
                not outsiders,
                (
                    "every valid approval is from an allowed key"
                    if not outsiders
                    else "approval(s) from key(s) outside the allowed list: "
                    + repr(outsiders)
                ),
            )
            counted = [a for a in valid if a.approver in allowed_keys]
        else:
            counted = valid
        if "require" in approval_rules:
            needed = approval_rules["require"]
            assert isinstance(needed, int)
            keys = [a.approver for a in counted]
            if approval_rules.get("distinct_approvers"):
                effective = len(set(keys))
                counting = "distinct valid"
            else:
                effective = len(keys)
                counting = "valid"
            add(
                "approvals.require",
                effective >= needed,
                f"{effective} {counting} approval(s) of this exact root "
                f"(need {needed})",
            )

    redaction_rules = rules.get("redaction")
    if isinstance(redaction_rules, dict):
        # Disclosure is a control like any other: an auditor who needs the
        # full corpus says so once, here (spec 0149).
        withheld = len(report.withheld)
        if redaction_rules.get("allow") is False:
            add(
                "redaction.allow",
                withheld == 0,
                (
                    "no content was withheld"
                    if withheld == 0
                    else f"{withheld} item(s) withheld, but this policy requires "
                    "the complete evidence"
                ),
            )
        if "max_withheld" in redaction_rules:
            limit = redaction_rules["max_withheld"]
            assert isinstance(limit, int)
            add(
                "redaction.max_withheld",
                withheld <= limit,
                f"{withheld} item(s) withheld (limit {limit})",
            )

    name = policy["name"]
    version = policy["version"]
    assert isinstance(name, str) and isinstance(version, int)
    return PolicyReport(
        name=name,
        version=version,
        policy_digest=digest(policy),
        checks=tuple(checks),
    )


# --- rendering --------------------------------------------------------------------


def render_policy(report: PolicyReport) -> str:
    verdict = "COMPLIANT" if report.compliant else "NON-COMPLIANT"
    lines = [
        f"policy:    {report.name} v{report.version} "
        f"({report.policy_digest[:19]}…) — {verdict}"
    ]
    for check in report.checks:
        mark = "ok" if check.ok else "!!"
        lines.append(f"  [{mark}] {check.rule}: {check.detail}")
    lines.append(f"note:      {SCOPE_LINE}")
    return "\n".join(lines)
