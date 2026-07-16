"""`tessera bundle explain` — a trust bundle made legible to a human (spec 0142).

`verify` proves a bundle re-derives; `explain` shows a person *what* it says:
the question, each claim with its re-derived verdict, the evidence each claim
cites, and — for an action bundle — the wire request with its per-slot
provenance. It is a read-only projection of what :func:`verify_bundle`
already computes, with the real verdict rendered first, so it can never dress
a failing bundle as sound.

Pure stdlib and offline (it calls the verify path, nothing more), so a
stranger reads a bundle with nothing installed.
"""

from __future__ import annotations

from dataclasses import dataclass

from tessera.bundle.verify import RE_DERIVED, VerifyReport, verify_bundle

_SNIPPET = 100  # default evidence-snippet width before eliding
_BODY = 400  # default action-body width before eliding


def _elide(text: str, limit: int, *, full: bool) -> str:
    text = text.replace("\n", " ")
    if full or len(text) <= limit:
        return text
    return f"{text[:limit]}… (+{len(text) - limit} chars)"


@dataclass(frozen=True)
class EvidenceView:
    id: str
    source: str
    locator: str
    snippet: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source": self.source,
            "locator": self.locator,
            "snippet": self.snippet,
        }


@dataclass(frozen=True)
class ClaimView:
    text: str
    status: str  # "re-derived" | "UNSUPPORTED" | "recorded" (degraded, not re-run)
    evidence: tuple[EvidenceView, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "status": self.status,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@dataclass(frozen=True)
class SlotView:
    part: str
    role: str
    value: str
    provenance: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "part": self.part,
            "role": self.role,
            "value": self.value,
            "provenance": list(self.provenance),
        }


@dataclass(frozen=True)
class ActionView:
    kind: str
    method: str
    path: str
    body: str
    outcome: str
    simulated: bool
    slots: tuple[SlotView, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "method": self.method,
            "path": self.path,
            "body": self.body,
            "outcome": self.outcome,
            "simulated": self.simulated,
            "slots": [s.to_dict() for s in self.slots],
        }


@dataclass(frozen=True)
class Explanation:
    verdict: str
    taxonomy: str
    taxonomy_reason: str | None
    domain: str
    question: str
    sealed_under: str
    installed: str
    integrity_ok: bool
    signature_status: str
    signature_public_key: str | None
    refused: bool
    refusal: str | None
    claims: tuple[ClaimView, ...]
    action: ActionView | None
    packaged_records: int
    cited_records: int

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "taxonomy": self.taxonomy,
            "taxonomy_reason": self.taxonomy_reason,
            "domain": self.domain,
            "question": self.question,
            "sealed_under": self.sealed_under,
            "installed": self.installed,
            "integrity_ok": self.integrity_ok,
            "signature": {
                "status": self.signature_status,
                "public_key": self.signature_public_key,
            },
            "refused": self.refused,
            "refusal": self.refusal,
            "claims": [c.to_dict() for c in self.claims],
            "action": self.action.to_dict() if self.action else None,
            "packaged_records": self.packaged_records,
            "cited_records": self.cited_records,
        }


def _section(bundle: dict[str, object], key: str) -> dict[str, object]:
    value = bundle.get(key)
    return value if isinstance(value, dict) else {}


def _evidence_views(support: object, *, full: bool) -> tuple[EvidenceView, ...]:
    views: list[EvidenceView] = []
    if isinstance(support, list):
        for item in support:
            if not isinstance(item, dict):
                continue
            locator = item.get("locator")
            rendered = ""
            if isinstance(locator, dict):
                rendered = str(locator.get("render", locator.get("kind", "")))
            views.append(
                EvidenceView(
                    id=str(item.get("id", "")),
                    source=str(item.get("source", "")),
                    locator=rendered,
                    snippet=_elide(str(item.get("text", "")), _SNIPPET, full=full),
                )
            )
    return tuple(views)


def explain_bundle(bundle: dict[str, object], *, full: bool = False) -> Explanation:
    """Build the structured, human-facing view of a bundle. The verdict is
    :func:`verify_bundle`'s, so a failing bundle is shown as failing."""
    report: VerifyReport = verify_bundle(bundle)
    result = _section(bundle, "result")
    closure = _section(bundle, "evidence_closure")

    # Pair each recorded claim with verify's re-derived verdict (present only
    # when the bundle was actually re-executed; degraded bundles have none).
    rederived_by_index = {c.index: c.rederived for c in report.claims}
    claims: list[ClaimView] = []
    recorded_claims = result.get("claims")
    cited_ids: set[str] = set()
    if isinstance(recorded_claims, list):
        for index, claim in enumerate(recorded_claims):
            if not isinstance(claim, dict):
                continue
            evidence = _evidence_views(claim.get("support"), full=full)
            cited_ids.update(e.id for e in evidence)
            if index in rederived_by_index:
                status = "re-derived" if rederived_by_index[index] else "UNSUPPORTED"
            else:
                status = "recorded"  # degraded: not re-executed, shown as recorded
            claims.append(
                ClaimView(
                    text=str(claim.get("text", "")), status=status, evidence=evidence
                )
            )

    action = _action_view(bundle, full=full)

    graph = closure.get("graph")
    packaged = 0
    if isinstance(graph, dict) and isinstance(graph.get("nodes"), list):
        packaged = len(graph["nodes"])

    return Explanation(
        verdict=report.verdict,
        taxonomy=report.taxonomy,
        taxonomy_reason=report.taxonomy_reason,
        domain=report.domain,
        question=str(result.get("question", "")),
        sealed_under=report.sealed_under,
        installed=report.installed,
        integrity_ok=report.integrity_problems == (),
        signature_status=report.signature_status,
        signature_public_key=report.signature_public_key,
        refused=bool(result.get("refused")),
        refusal=(str(result["refusal"]) if result.get("refusal") else None),
        claims=tuple(claims),
        action=action,
        packaged_records=packaged,
        cited_records=len(cited_ids),
    )


def _action_view(bundle: dict[str, object], *, full: bool) -> ActionView | None:
    action = bundle.get("action")
    if not isinstance(action, dict):
        return None
    request = action.get("request")
    method = path = body = ""
    if isinstance(request, dict):
        method = str(request.get("method", ""))
        path = str(request.get("path", ""))
        body_val = request.get("body")
        body = _elide(str(body_val), _BODY, full=full)
    slots: list[SlotView] = []
    raw_slots = action.get("slots")
    if isinstance(raw_slots, list):
        for slot in raw_slots:
            if not isinstance(slot, dict):
                continue
            provenance = tuple(
                f"{e.source} ({e.locator})"
                for e in _evidence_views(slot.get("support"), full=full)
            )
            slots.append(
                SlotView(
                    part=str(slot.get("part", "")),
                    role=str(slot.get("role", "")),
                    value=_elide(str(slot.get("value", "")), _SNIPPET, full=full),
                    provenance=provenance,
                )
            )
    return ActionView(
        kind=str(action.get("kind", "")),
        method=method,
        path=path,
        body=body,
        outcome=str(action.get("outcome", "")),
        simulated=bool(action.get("simulated")),
        slots=tuple(slots),
    )


# --- text rendering ----------------------------------------------------------------


def render_text(explanation: Explanation, *, source: str) -> str:
    lines = [f"bundle:   {source}"]
    lines.append(
        f"verdict:  {explanation.verdict} — {explanation.taxonomy}"
        + (
            f" ({explanation.taxonomy_reason})"
            if explanation.taxonomy_reason and explanation.taxonomy != RE_DERIVED
            else ""
        )
    )
    lines.append(
        f"engine:   domain {explanation.domain}, sealed under tessera "
        f"{explanation.sealed_under}"
    )
    integ = "intact" if explanation.integrity_ok else "BROKEN"
    lines.append(f"integrity:{integ} · signature: {explanation.signature_status}")
    lines.append("")
    lines.append(f"Q: {explanation.question}")
    lines.append("")

    if explanation.refused:
        lines.append(f"↳ refusal: {explanation.refusal}")
    else:
        for i, claim in enumerate(explanation.claims):
            chip = {
                "re-derived": "[✓ re-derived]",
                "UNSUPPORTED": "[✗ UNSUPPORTED]",
                "recorded": "[· recorded]",
            }.get(claim.status, f"[{claim.status}]")
            lines.append(f"{chip} claim {i}: {claim.text}")
            for ev in claim.evidence:
                lines.append(f'    ↳ {ev.source} ({ev.locator}) — "{ev.snippet}"')
        lines.append("")
        lines.append(
            f"evidence: {explanation.cited_records} record(s) cited of "
            f"{explanation.packaged_records} packaged in the closure"
        )

    if explanation.action is not None:
        act = explanation.action
        lines.append("")
        sim = " (simulated)" if act.simulated else ""
        lines.append(f"action:   {act.kind} · {act.method} {act.path}{sim}")
        lines.append(f"  outcome: {act.outcome}")
        for slot in act.slots:
            prov = "; ".join(slot.provenance) or "—"
            lines.append(f"  [{slot.part}/{slot.role}] {slot.value}")
            lines.append(f"      ↳ {prov}")
    return "\n".join(lines)
