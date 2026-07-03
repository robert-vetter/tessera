"""Pure HTML rendering over the trust objects — escape everything (ADR 0027).

Every function here is a pure ``object -> str`` — no network, no state, and no
I/O except the one named, cached exception (:func:`_trust_rows`, which reads
the committed eval history once per process) — so the whole presentation is
unit-testable with hostile content. The one security rule is the web analogue
of the payload-renderer's fence rule (spec 0109 B4): **evidence text is
attacker-shaped in principle** (real CI logs flow through it), so every dynamic
string passes :func:`_e` (``html.escape``) before it touches markup — values
are *displayed*, never interpreted; query-string values additionally pass
:func:`_q` (URL-encoding) so links can neither split nor truncate.

The UI asserts nothing of its own: verdict chips mirror ``verified`` flags the
verifier computed, refusals render as refusals, narration (when configured)
appears strictly below the canonical claims under the ADR 0013 label, and the
action flow ends at a **simulated** receipt — the real path stays
maintainer-only, outside the UI (ADR 0025/0027).
"""

from __future__ import annotations

import html
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from tessera.agent.actions import ActionField, ActionProposal
from tessera.agent.execution import ExecutionReceipt
from tessera.agent.grounded import (
    GroundedAssertion,
    GroundedClaim,
    GroundedEvidence,
    GroundedResult,
)
from tessera.agent.payloads import PayloadSlot, RenderedPayload
from tessera.surface.narration import NARRATION_LABEL

_HISTORY_PATH = Path(__file__).resolve().parents[3] / "eval" / "history.jsonl"

# The demo questions the README walks through — one click instead of typing.
SAMPLE_QUESTIONS: dict[str, tuple[str, ...]] = {
    "business": (
        "Summarise Müller Logistik: its sales orders and agreement terms.",
        "Which entity has the highest total order value in EUR?",
        "What is Atlas Trading's total order value?",
    ),
    "devex": (
        "Why did run R-1042 fail?",
        "What does PR-201 actually change?",
        "Who is on call for notifications-service?",
    ),
    "github_actions": (
        "Why did run 27014662820 fail?",
        "Is the published documentation site unreachable for visitors?",
    ),
}

_CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font: 15px/1.55 system-ui, -apple-system, sans-serif; margin: 0 auto;
       max-width: 62rem; padding: 1.2rem 1rem 4rem; }
h1 { font-size: 1.35rem; margin: .4rem 0 .2rem; }
h1 a { color: inherit; text-decoration: none; }
h2 { font-size: 1.05rem; margin: 1.6rem 0 .5rem; }
.tag { font-size: .78rem; opacity: .75; }
.card { border: 1px solid rgba(128,128,128,.35); border-radius: 10px;
        padding: .8rem .95rem; margin: .6rem 0; }
.chip { display: inline-block; font-size: .74rem; border-radius: 999px;
        padding: .05rem .55rem; border: 1px solid rgba(128,128,128,.4);
        vertical-align: middle; }
.chip.ok { background: rgba(46,160,67,.16); border-color: rgba(46,160,67,.5); }
.chip.bad { background: rgba(248,81,73,.16); border-color: rgba(248,81,73,.5); }
.chip.info { background: rgba(56,139,253,.12); border-color: rgba(56,139,253,.45); }
.refusal { border-left: 4px solid rgba(212,153,0,.8); }
.claim-text { white-space: pre-wrap; margin: .3rem 0 .1rem; }
pre { white-space: pre-wrap; word-break: break-word; background: rgba(128,128,128,.12);
      border-radius: 8px; padding: .6rem .7rem; font-size: .82rem; margin: .4rem 0; }
details { margin: .35rem 0 0; }
summary { cursor: pointer; font-size: .82rem; opacity: .8; }
table { border-collapse: collapse; font-size: .84rem; width: 100%; }
td, th { border: 1px solid rgba(128,128,128,.3); padding: .3rem .5rem;
         text-align: left; vertical-align: top; }
form.ask { display: flex; gap: .5rem; flex-wrap: wrap; margin: .8rem 0; }
form.ask input[type=text] { flex: 1 1 24rem; padding: .5rem .6rem;
        border-radius: 8px; border: 1px solid rgba(128,128,128,.45);
        font: inherit; background: transparent; color: inherit; }
select, button { font: inherit; padding: .45rem .7rem; border-radius: 8px;
        border: 1px solid rgba(128,128,128,.45); background: transparent;
        color: inherit; cursor: pointer; }
button.primary { background: rgba(56,139,253,.15); border-color: rgba(56,139,253,.55); }
.samples a { display: inline-block; margin: .15rem .4rem .15rem 0;
        font-size: .8rem; opacity: .85; }
.narration { border-left: 4px solid rgba(163,113,247,.7); }
.small { font-size: .8rem; opacity: .8; }
footer { margin-top: 2.5rem; font-size: .78rem; opacity: .7; }
"""


def _e(value: object) -> str:
    """The one escaping door: every dynamic string passes here."""
    return html.escape(str(value), quote=True)


def _q(value: str) -> str:
    """A query-string VALUE: URL-encoded (so `&`/`#`/`"` in record ids or
    questions cannot split or truncate the link — review S2), producing plain
    %-ASCII that is inert in an attribute context too."""
    return quote(value, safe="")


def page(title: str, body: str) -> str:
    """The shell. Inline CSS only, zero JavaScript — the strict CSP the server
    sends (``default-src 'none'; style-src 'unsafe-inline'``) stays truthful."""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_e(title)}</title><style>{_CSS}</style></head><body>"
        '<h1><a href="/">Tessera</a> <span class="tag">the agent can only say '
        "what it can prove — and only do what you approve</span></h1>"
        f"{body}"
        "<footer>Every claim above carries a provenance path; every action ends in "
        "a receipt. Deterministic engine, zero runtime dependencies — "
        '<a href="https://github.com/robert-vetter/tessera">source &amp; '
        "write-up</a>.</footer></body></html>"
    )


def _verdict_chip(verified: bool) -> str:
    if verified:
        return '<span class="chip ok">✓ verifier-checked</span>'
    return '<span class="chip bad">✗ unverified</span>'


def _evidence_html(domain: str, record: GroundedEvidence) -> str:
    locator = ", ".join(f"{k} {v}" for k, v in record.locator_parts)
    trail = (
        f"/assertions?domain={_q(domain)}&record_id={_q(record.id)}" if domain else ""
    )
    trail_link = f' · <a href="{trail}">entity-resolution trail</a>' if trail else ""
    return (
        '<div class="card">'
        f'<b>{_e(record.id)}</b> <span class="small">— {_e(record.source)} · '
        f"{_e(record.locator_kind)} ({locator and _e(locator) or '—'}) · "
        f"snapshot {_e(record.ingested_at)}{trail_link}</span>"
        f"<pre>{_e(record.text)}</pre></div>"
    )


def _claim_html(domain: str, number: int, claim: GroundedClaim) -> str:
    evidence = "".join(_evidence_html(domain, record) for record in claim.support)
    return (
        '<div class="card">'
        f'<span class="chip info">[{number}]</span> {_verdict_chip(claim.verified)}'
        f'<div class="claim-text">{_e(claim.text)}</div>'
        f"<details><summary>provenance — {len(claim.support)} cited "
        f"record(s)</summary>{evidence}</details></div>"
    )


def _offered(action: dict[str, object], result: GroundedResult) -> bool:
    domains = action.get("domains")
    applicable = isinstance(domains, list) and result.domain in domains
    return applicable and action.get("from_route") == result.route_kind


def _action_offers(result: GroundedResult, actions: list[dict[str, object]]) -> str:
    offers = [action for action in actions if _offered(action, result)]
    all_verified = bool(result.claims) and all(c.verified for c in result.claims)
    if not result.grounded or not all_verified or not offers:
        return ""
    buttons = "".join(
        f'<a href="/action?action={_q(str(action["name"]))}'
        f"&domain={_q(result.domain)}"
        f'&q={_q(result.question)}"><button>draft '
        f"{_e(action['name'])} →</button></a> "
        for action in offers
    )
    return (
        '<h2>Act on it</h2><p class="small">A drafted action is a proposal: '
        "every field must trace to a verifier-passing claim, or it is not "
        "grounded. Nothing executes without your approval — and the UI can only "
        "ever run the <b>simulated</b> actuator.</p>" + buttons
    )


def answer_page(
    result: GroundedResult,
    actions: list[dict[str, object]],
    narration: str | None,
    notice: str | None,
) -> str:
    """The grounded answer: route, per-claim verdicts, provenance drill-down,
    labelled narration strictly below the canonical claims, action offers."""
    head = (
        f'<p class="small">domain <b>{_e(result.domain)}</b> · route '
        f"<b>{_e(result.route_kind)}</b> — {_e(result.route_reason)}</p>"
        f"<h2>“{_e(result.question)}”</h2>"
    )
    if not result.grounded:
        body = (
            head
            + '<div class="card refusal"><b>Refused.</b> '
            + f"{_e(result.refusal or 'Not enough evidence to answer honestly.')}"
            + '<div class="small">A principled refusal is the trust contract '
            "working: no evidence, no claim — never a guess.</div></div>"
        )
        return page("Tessera — refused", body)

    claims = "".join(
        _claim_html(result.domain, number, claim)
        for number, claim in enumerate(result.claims, start=1)
    )
    checked = sum(1 for claim in result.claims if claim.verified)
    trust_line = (
        f'<p><span class="chip ok">✓ trust: {checked}/{len(result.claims)} '
        "claims verifier-checked</span></p>"
        if result.claims and checked == len(result.claims)
        else (
            f'<p><span class="chip bad">✗ only {checked}/{len(result.claims)} '
            "claims passed the verifier</span></p>"
        )
    )
    narration_html = ""
    if narration:
        narration_html = (
            f'<div class="card narration"><div class="small">'
            f"{_e(NARRATION_LABEL)}</div><p>{_e(narration)}</p></div>"
        )
    elif notice:
        narration_html = f'<p class="small">{_e(notice)}</p>'
    return page(
        "Tessera — grounded answer",
        head + claims + trust_line + narration_html + _action_offers(result, actions),
    )


def _field_html(field: ActionField) -> str:
    support = ", ".join(_e(record.id) for record in field.support)
    return (
        f"<tr><td><b>{_e(field.name)}</b></td>"
        f'<td class="claim-text">{_e(field.value)}</td>'
        f"<td>{_verdict_chip(field.verified)}</td>"
        f'<td class="small">{support or "—"}</td></tr>'
    )


def action_page(proposal: ActionProposal) -> str:
    head = (
        f"<h2>Action draft: {_e(proposal.kind)}</h2>"
        f'<p class="small">domain <b>{_e(proposal.domain)}</b> · from '
        f"“{_e(proposal.question)}” · route {_e(proposal.route_kind)}</p>"
    )
    if proposal.refused or not proposal.fields:
        return page(
            "Tessera — action refused",
            head
            + '<div class="card refusal"><b>Not drafted.</b> '
            + _e(
                proposal.refusal
                or "The grounding refused; a refusal is never drafted over."
            )
            + "</div>",
        )
    rows = "".join(_field_html(field) for field in proposal.fields)
    grounded = (
        '<span class="chip ok">✓ all fields grounded</span>'
        if proposal.all_grounded
        else (
            '<span class="chip bad">✗ not fully grounded — '
            "no payload will render</span>"
        )
    )
    # The preview affordance only when a payload WILL render (review H3): a
    # "preview the request" button beside "no payload will render" would
    # contradict itself, even though the target correctly withholds.
    next_link = (
        (
            f'<p><a href="/payload?action={_q(proposal.kind)}'
            f"&domain={_q(proposal.domain)}"
            f'&q={_q(proposal.question)}"><button class="primary">preview the '
            "exact GitHub request →</button></a></p>"
        )
        if proposal.all_grounded
        else ""
    )
    return page(
        "Tessera — action draft",
        head + f"<p>{grounded}</p><table><tr><th>field</th><th>value (verbatim)</th>"
        f"<th>verdict</th><th>traced to</th></tr>{rows}</table>"
        + '<p class="small">Every value is a verbatim claim or evidence fragment '
        "with its own recomputed verdict — the proposal asserts nothing new.</p>"
        + next_link,
    )


def _slot_html(slot: PayloadSlot) -> str:
    support = ", ".join(_e(record.id) for record in slot.support)
    return (
        f"<tr><td>{_e(slot.part)}</td><td><b>{_e(slot.role)}</b></td>"
        f'<td class="claim-text">{_e(slot.value)}</td>'
        f"<td>{_verdict_chip(slot.verified)}</td>"
        f'<td class="small">{support or "—"}</td></tr>'
    )


def payload_page(payload: RenderedPayload) -> str:
    head = (
        f"<h2>Dry-run payload: {_e(payload.kind)} → {_e(payload.target)}</h2>"
        f'<p class="small">domain <b>{_e(payload.domain)}</b> · from '
        f"“{_e(payload.question)}”</p>"
    )
    if not payload.rendered:
        return page(
            "Tessera — payload withheld",
            head
            + '<div class="card refusal"><b>Withheld.</b> '
            + _e(
                payload.withheld_reason or "Not fully grounded; no request is rendered."
            )
            + '<div class="small">A payload is never rendered over ungrounded '
            "ground (ADR 0024).</div></div>",
        )
    request = json.dumps(payload.body, indent=2, ensure_ascii=False)
    slots = "".join(_slot_html(slot) for slot in payload.slots)
    approve = (
        '<form method="post" action="/execute">'
        f'<input type="hidden" name="action" value="{_e(payload.kind)}">'
        f'<input type="hidden" name="domain" value="{_e(payload.domain)}">'
        f'<input type="hidden" name="q" value="{_e(payload.question)}">'
        '<button class="primary" type="submit">approve &amp; execute '
        "(simulated) →</button></form>"
        '<p class="small">The UI wires the <b>simulated</b> actuator only — it '
        "holds no credential and can never send (ADR 0025/0027). The one real, "
        "maintainer-approved send is on the record: "
        '<a href="https://github.com/robert-vetter/tessera-exec-oneshot/issues/1">'
        "tessera-exec-oneshot#1</a>.</p>"
    )
    return page(
        "Tessera — dry-run payload",
        head + f'<p><span class="chip ok">✓ all values grounded</span> '
        f'<span class="chip info">{_e(payload.method)} {_e(payload.path)}</span> '
        '<span class="chip">sent: false</span></p>'
        + f"<pre>{_e(request)}</pre>"
        + f"<table><tr><th>part</th><th>role</th><th>value</th><th>verdict</th>"
        f"<th>traced to</th></tr>{slots}</table>"
        + '<p class="small">The body is byte-reconstructable from the verified '
        "slots — the renderer adds nothing beyond declared scaffolding.</p>" + approve,
    )


def receipt_page(receipt: ExecutionReceipt) -> str:
    head = (
        f"<h2>Execution receipt: {_e(receipt.kind)}</h2>"
        f'<p class="small">domain <b>{_e(receipt.domain)}</b> · from '
        f"“{_e(receipt.question)}” · actuator <b>{_e(receipt.actuator)}</b></p>"
    )
    if receipt.withheld:
        return page(
            "Tessera — execution withheld",
            head
            + '<div class="card refusal"><b>Withheld — nothing executed.</b> '
            + f"{_e(receipt.withheld_reason or '')}"
            + '<div class="small">Nothing executes over ungrounded ground '
            "(ADR 0025).</div></div>",
        )
    chips = (
        f'<span class="chip info">outcome: {_e(receipt.outcome)}</span> '
        f'<span class="chip">sent: {_e(str(receipt.sent).lower())}</span> '
        f'<span class="chip">simulated: {_e(str(receipt.simulated).lower())}</span> '
        f'<span class="chip">approved: {_e(str(receipt.approved).lower())}</span>'
    )
    request = json.dumps(
        {"method": receipt.method, "path": receipt.path, "body": receipt.body},
        indent=2,
        ensure_ascii=False,
    )
    slots = "".join(_slot_html(slot) for slot in receipt.slots)
    return page(
        "Tessera — execution receipt",
        head + f"<p>{chips}</p>"
        '<p class="small">This receipt is the lossless record of the exact '
        "request the actuator acted on — recorded, not sent (the UI can only "
        "simulate; the real path is maintainer-only and double-gated).</p>"
        f"<pre>{_e(request)}</pre>"
        f"<table><tr><th>part</th><th>role</th><th>value</th><th>verdict</th>"
        f"<th>traced to</th></tr>{slots}</table>",
    )


def assertions_page(domain: str, record_id: str, items: list[GroundedAssertion]) -> str:
    head = (
        f'<h2>Entity-resolution trail</h2><p class="small">record '
        f"<b>{_e(record_id)}</b> in domain <b>{_e(domain)}</b></p>"
    )
    if not items:
        return page(
            "Tessera — ER trail",
            head + '<div class="card">No resolution or mention assertions touch this '
            "record — it stands on its own.</div>",
        )
    rows = "".join(
        f"<tr><td>{_e(item.kind)}</td><td>{_e(item.a)}</td><td>{_e(item.b)}</td>"
        f"<td>{item.confidence:.3f}</td>"
        f'<td class="claim-text">{_e(item.reason)}</td></tr>'
        for item in items
    )
    return page(
        "Tessera — ER trail",
        head + f"<table><tr><th>kind</th><th>a</th><th>b</th><th>confidence</th>"
        f"<th>reason</th></tr>{rows}</table>"
        + '<p class="small">Assertions are additive and reversible: withdrawing '
        "one re-splits the cluster and leaves every raw record intact "
        "(ADR 0004).</p>",
    )


@lru_cache(maxsize=1)
def _trust_rows() -> str:
    """The one deliberate exception to this module's no-I/O rule (review S3):
    the measured-floor panel reads the committed ``eval/history.jsonl`` once
    per process (cached — the file only changes with a redeploy)."""
    if not _HISTORY_PATH.is_file():
        return ""
    lines = _HISTORY_PATH.read_text("utf-8").strip().splitlines()
    if not lines:  # a fresh/empty history file must not break the index page
        return ""
    last = json.loads(lines[-1])
    rows = []
    for battery in last.get("batteries", []):
        gold = battery.get("gold", {})
        rows.append(
            f"<tr><td><b>{_e(battery.get('name'))}</b></td>"
            f"<td>{_e(gold.get('cases'))}</td>"
            f"<td>{_metric(gold.get('faithfulness'))}</td>"
            f"<td>{_metric(gold.get('coverage'))}</td>"
            f"<td>{_metric(gold.get('quality'))}</td></tr>"
        )
    recorded = _e(last.get("recorded", "?"))
    return (
        f'<h2>The measured floor</h2><p class="small">latest recorded eval '
        f"({recorded}) — faithfulness &lt; 1.0 fails the build, in CI:</p>"
        "<table><tr><th>battery (gold)</th><th>cases</th><th>faithfulness</th>"
        f"<th>coverage</th><th>quality</th></tr>{''.join(rows)}</table>"
        '<p class="small">The sub-1.0 numbers are deliberate: offline lexical '
        "misses kept visible in CI, closed online on SAP HANA — the "
        "trail is in <code>eval/history.jsonl</code>.</p>"
    )


def _metric(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return "?" if value is None else _e(value)


def index_page(domains: tuple[str, ...], selected: str) -> str:
    options = "".join(
        f'<option value="{_e(name)}"{" selected" if name == selected else ""}>'
        f"{_e(name)}</option>"
        for name in domains
    )
    samples = "".join(
        f'<div class="samples"><b class="small">{_e(name)}:</b> '
        + " ".join(
            f'<a href="/ask?domain={_e(name)}&q={_e(question)}">“{_e(question)}”</a>'
            for question in SAMPLE_QUESTIONS.get(name, ())
        )
        + "</div>"
        for name in domains
    )
    return page(
        "Tessera — ask with proof",
        "<p>Ask a question over enterprise data — tables, documents, CI logs. "
        "Every claim in the answer traces to the exact records that support it; "
        "what cannot be proven is <b>refused</b>, and any action an agent takes "
        "ends in a <b>receipt</b>.</p>"
        '<form class="ask" action="/ask" method="get">'
        f'<select name="domain">{options}</select>'
        '<input type="text" name="q" placeholder="Ask, e.g. why did run '
        'R-1042 fail?" required>'
        '<button class="primary" type="submit">ask</button></form>'
        f"{samples}" + _trust_rows(),
    )


def error_page(status: int, message: str) -> str:
    return page(
        f"Tessera — {status}",
        f'<div class="card refusal"><b>{status}.</b> {_e(message)}</div>',
    )
