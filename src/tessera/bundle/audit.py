"""`tessera bundle audit` — a decision record for an auditor (spec 0139).

From any trust bundle, produce the record a compliance or engineering buyer
actually needs: the verification verdict, the decision it records, and a
mapping of the bundle's contents to the record-keeping and human-oversight
*concepts* named in the EU AI Act (Article 12 and Article 14). It is a
read-only projection of what :func:`verify_bundle` already computes, so it
can never dress a failing bundle as sound — a FAILED re-verification
produces a record that says so.

**This is a documentation aid, not a compliance attestation or legal
advice.** The mapping links a bundle's fields to the concepts an article
names; it does not certify conformance with any standard, and the candidate
technical standards are still drafts. The dates are the *current* ones: the
Digital Omnibus deferred the Annex III high-risk obligations (Art. 12
logging, Art. 14 human oversight) to **2 December 2027**; only Art. 50
transparency applies from 2 August 2026 (docs/MARKET.md §3, docs/COMPLIANCE.md).

Pure stdlib and offline — it calls the verify path and reads the bundle,
nothing more.
"""

from __future__ import annotations

from dataclasses import dataclass

from tessera.bundle.verify import BundleFormatError, VerifyReport, verify_bundle

DISCLAIMER = (
    "This record is a documentation aid, not a compliance attestation or legal "
    "advice. It maps the bundle's contents to concepts named in the EU AI Act; "
    "it does not certify conformance, and the candidate technical standards "
    "(prEN 18229-1, ISO/IEC DIS 24970) are drafts. Timeline: the Digital Omnibus "
    "deferred the Annex III high-risk obligations (Art. 12 logging, Art. 14 human "
    "oversight) to 2 December 2027; only Art. 50 transparency applies from "
    "2 August 2026."
)


@dataclass(frozen=True)
class MappingRow:
    """One row: a concept an EU AI Act article names ↔ what this bundle carries
    for it, and whether the bundle actually carries it (an answer-only bundle
    has no human-oversight record, and says so)."""

    concept: str
    article: str
    carried: bool
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {
            "concept": self.concept,
            "article": self.article,
            "carried": self.carried,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class AuditRecord:
    """A bundle's decision record: the verdict, the decision it records, the
    Art. 12/14 mapping, and the disclaimer."""

    domain: str
    question: str
    verdict: str
    re_derivable: bool
    refused: bool
    signed_by: str | None
    claim_count: int
    #: Claims whose verdict RE-DERIVES from the packaged evidence — counted
    #: from the verifier's re-execution, never from the bundle's own recorded
    #: flags (a forger controls those). ``None`` when the bundle was not
    #: re-executed here (a degraded bundle has no honest count to report).
    verified_claim_count: int | None
    has_action: bool
    mapping: tuple[MappingRow, ...]
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict[str, object]:
        return {
            "domain": self.domain,
            "question": self.question,
            "verdict": self.verdict,
            "re_derivable": self.re_derivable,
            "refused": self.refused,
            "signed_by": self.signed_by,
            "claims": {
                "total": self.claim_count,
                "re_derived": self.verified_claim_count,
            },
            "has_action": self.has_action,
            "eu_ai_act_mapping": [row.to_dict() for row in self.mapping],
            "disclaimer": self.disclaimer,
        }


def _mapping(
    report: VerifyReport, *, has_action: bool, approved: bool, requires_approval: bool
) -> tuple[MappingRow, ...]:
    """Map the bundle to the concepts Art. 12/14 name — grounded in the fields
    the bundle actually carries, never hand-waved."""
    re_derivable = report.taxonomy == "RE-DERIVED"
    rows = [
        MappingRow(
            "Record-keeping / traceability",
            "Art. 12",
            True,
            "the decision is one portable, tamper-evident file: the question, "
            "every claim, the exact evidence records each claim cites, and the "
            "verifier's verdict.",
        ),
        MappingRow(
            "Reconstructing why an output was produced",
            "Art. 12 (purpose)",
            re_derivable,
            (
                "an auditor re-derives every claim's verdict offline from the "
                "packaged evidence — a re-execution, not a log to be trusted."
                if re_derivable
                else "the installed engine cannot re-derive this bundle "
                f"({report.taxonomy_reason or report.taxonomy}); it can be "
                "hash-checked but not re-executed here."
            ),
        ),
    ]
    if has_action:
        rows.append(
            MappingRow(
                "Human oversight",
                "Art. 14",
                True,
                "the action was drafted, never auto-sent; the receipt records "
                f"requires_approval={requires_approval} and approved={approved} "
                "— the human-in-the-loop gate is in the record itself.",
            )
        )
        rows.append(
            MappingRow(
                "Accountability of an automated action",
                "Art. 14 (purpose)",
                True,
                "the receipt links the exact wire request → its approval → the "
                "verifier-passing claims → the evidence; nothing acts on "
                "ungrounded ground.",
            )
        )
    else:
        rows.append(
            MappingRow(
                "Human oversight",
                "Art. 14",
                False,
                "this bundle records an answer only (no action), so there is no "
                "approval gate to attest — an action bundle carries one.",
            )
        )
    return tuple(rows)


def audit_record(bundle: dict[str, object]) -> AuditRecord:
    """Build the decision record for a bundle. Raises
    :class:`BundleFormatError` when the envelope is broken (a file that cannot
    be read/hash-checked cannot be audited)."""
    report = verify_bundle(bundle)
    if report.integrity_problems or report.signature_problems:
        raise BundleFormatError(
            "cannot produce an audit record: the bundle's envelope is broken "
            f"({'; '.join(report.integrity_problems + report.signature_problems)})"
        )

    result = bundle.get("result")
    question = ""
    claims: list[object] = []
    if isinstance(result, dict):
        question = str(result.get("question", ""))
        raw_claims = result.get("claims")
        if isinstance(raw_claims, list):
            claims = raw_claims

    action = bundle.get("action")
    has_action = isinstance(action, dict)
    approved = bool(action.get("approved")) if isinstance(action, dict) else False
    requires_approval = (
        bool(action.get("requires_approval", True))
        if isinstance(action, dict)
        else True
    )

    # The honest count comes from the verifier's re-execution (a forger
    # controls the bundle's recorded flags, so those are never counted).
    re_derivable = report.taxonomy == "RE-DERIVED"
    verified = sum(1 for c in report.claims if c.rederived) if re_derivable else None

    return AuditRecord(
        domain=report.domain,
        question=question,
        verdict=report.verdict,
        re_derivable=re_derivable,
        refused=report.refused,
        signed_by=report.signature_public_key,
        claim_count=len(claims),
        verified_claim_count=verified,
        has_action=has_action,
        mapping=_mapping(
            report,
            has_action=has_action,
            approved=approved,
            requires_approval=requires_approval,
        ),
    )


# --- rendering --------------------------------------------------------------------

_VERDICT_LINE = {
    "PASS": "the decision RE-VERIFIED: every claim re-derives from its evidence.",
    "FAIL": "the decision FAILED re-verification: its claims do NOT re-derive "
    "from the packaged evidence — this record documents an unsound decision.",
    "DEGRADED": "the decision could not be fully re-derived here (degraded, "
    "see the mapping); it was not re-executed to a pass.",
}


def render_text(record: AuditRecord) -> str:
    lines = ["EU AI Act audit record — a decision made legible for an auditor", ""]
    lines.append(
        f"verdict:  {record.verdict} — {_VERDICT_LINE.get(record.verdict, '')}"
    )
    lines.append(f"domain:   {record.domain}")
    kind = " · action bundle" if record.has_action else " · answer only"
    if record.refused:
        lines.append("decision: an explicit refusal (the system declined to answer).")
    elif record.verified_claim_count is None:
        lines.append(f"decision: claim(s) not re-executed here (see mapping){kind}")
    else:
        lines.append(
            f"decision: {record.verified_claim_count}/{record.claim_count} "
            f"claim(s) re-derive from the packaged evidence{kind}"
        )
    origin = (
        f"signed by {record.signed_by}"
        if record.signed_by
        else "unsigned (integrity + re-derivability, not origin)"
    )
    lines.append(f"origin:   {origin}")
    lines.append(f"question: {record.question}")
    lines.append("")
    lines.append("Mapping to the concepts named in the EU AI Act:")
    for row in record.mapping:
        mark = "✓" if row.carried else "—"
        lines.append(f"  [{mark}] {row.article} · {row.concept}")
        lines.append(f"        {row.detail}")
    lines.append("")
    lines.append(record.disclaimer)
    return "\n".join(lines)
