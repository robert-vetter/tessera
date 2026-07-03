"""The web surface (Milestone 17 Unit 3, spec 0114, ADR 0027).

Two properties carry the unit: **presentation honesty** (the UI renders exactly
what the trust objects say — verdict chips mirror the verifier, refusals render
as refusals, withheld payloads carry no approve form, receipts say simulated /
sent=false) and **escaping** (evidence text is attacker-shaped in principle —
real CI logs flow through it — so hostile content must come out inert). Plus
one socket-level smoke test over the real handler, and the CSP header pin.
"""

from __future__ import annotations

import threading
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

from tessera.agent.execution import execute_action
from tessera.agent.grounded import (
    GroundedClaim,
    GroundedEvidence,
    GroundedResult,
)
from tessera.agent.payloads import preview_payload
from tessera.ui import render
from tessera.ui.server import TesseraUIHandler

_XSS = '<script>alert(1)</script><img src=x onerror="steal()">'


def _evidence(text: str) -> GroundedEvidence:
    return GroundedEvidence(
        id=f"Log:{_XSS}",
        source=f"logs/{_XSS}.log",
        locator_kind="log-span",
        locator_parts=(("lines", "1-2"), ("job", _XSS)),
        ingested_at="2026-07-03",
        text=text,
    )


def _result(*, grounded: bool, claims: tuple[GroundedClaim, ...]) -> GroundedResult:
    return GroundedResult(
        domain="devex",
        question=f"why did {_XSS} fail?",
        route_kind="rca",
        route_reason=f"names {_XSS}",
        grounded=grounded,
        refused=not grounded,
        refusal=None if grounded else f"refused: {_XSS}",
        claims=claims,
    )


# --- escaping: hostile content comes out inert ---------------------------------


def test_hostile_evidence_and_claims_are_escaped_everywhere() -> None:
    claim = GroundedClaim(
        text=f"the failure was {_XSS}", verified=True, support=(_evidence(_XSS),)
    )
    html = render.answer_page(_result(grounded=True, claims=(claim,)), [], None, None)
    # No UN-escaped form survives anywhere (tag, attribute, or quote)…
    assert "<script>" not in html
    assert 'onerror="steal' not in html and "<img src=x" not in html
    # …the hostile text is displayed as inert, escaped text instead.
    assert "&lt;script&gt;" in html and "onerror=&quot;steal" in html


def test_hostile_refusal_is_escaped() -> None:
    html = render.answer_page(_result(grounded=False, claims=()), [], None, None)
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "Refused." in html


def test_hostile_narration_is_escaped_and_labelled() -> None:
    claim = GroundedClaim(text="ok", verified=True, support=(_evidence("ok"),))
    html = render.answer_page(
        _result(grounded=True, claims=(claim,)), [], f"narrated {_XSS}", None
    )
    assert "<script>" not in html
    assert "narration (LLM-phrased from the verified claims" in html


# --- presentation honesty: the UI asserts nothing of its own -------------------


def test_verdict_chips_mirror_the_verifier() -> None:
    good = GroundedClaim(text="t", verified=True, support=(_evidence("t"),))
    bad = GroundedClaim(text="t", verified=False, support=(_evidence("t"),))
    html = render.answer_page(
        _result(grounded=True, claims=(good, bad)), [], None, None
    )
    assert "✓ verifier-checked" in html and "✗ unverified" in html
    assert "only 1/2" in html  # the trust line goes red on any unverified claim


def test_refusal_page_carries_no_claims_and_no_action_offers() -> None:
    html = render.answer_page(_result(grounded=False, claims=()), [], None, None)
    assert "Refused." in html
    assert "Act on it" not in html and "provenance —" not in html


def test_withheld_payload_has_no_approve_form() -> None:
    # PR-201 is a summary route; asking an incident of it withholds the payload.
    payload = preview_payload("incident", "devex", "What does PR-201 change?")
    assert not payload.rendered
    html = render.payload_page(payload)
    assert "Withheld." in html
    assert "/execute" not in html and "<form" not in html


def test_rendered_payload_and_simulated_receipt_are_honest() -> None:
    question = "Why did run R-1042 fail?"
    payload = preview_payload("incident", "devex", question)
    assert payload.rendered
    payload_html = render.payload_page(payload)
    assert "sent: false" in payload_html
    assert "simulated" in payload_html  # the approve button says what it does
    assert 'action="/execute"' in payload_html

    receipt = execute_action("incident", "devex", question, approve=True)
    receipt_html = render.receipt_page(receipt)
    assert "outcome: simulated" in receipt_html
    assert "sent: false" in receipt_html
    assert "holds no credential" in receipt_html or "maintainer-only" in receipt_html


def test_index_lists_domains_samples_and_the_measured_floor() -> None:
    html = render.index_page(("business", "devex", "github_actions"), "business")
    assert "R-1042" in html  # a devex sample question
    assert "The measured floor" in html and "faithfulness" in html


# --- the real handler over a socket ---------------------------------------------


def _serve() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), TesseraUIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = str(server.server_address[0]), server.server_address[1]
    return server, f"http://{host}:{port}"


def test_server_smoke_ask_flow_and_security_headers() -> None:
    server, base = _serve()
    try:
        with urllib.request.urlopen(f"{base}/") as response:
            assert response.status == 200
            assert (
                response.headers["Content-Security-Policy"]
                == "default-src 'none'; style-src 'unsafe-inline'"
            )
            assert "ask with proof" in response.read().decode("utf-8")

        query = urllib.parse.urlencode(
            {"domain": "devex", "q": "Why did run R-1042 fail?"}
        )
        with urllib.request.urlopen(f"{base}/ask?{query}") as response:
            body = response.read().decode("utf-8")
            assert response.status == 200
            assert "R-1042" in body and "verifier-checked" in body
            assert "draft incident" in body  # the action offer for an RCA route

        form = urllib.parse.urlencode(
            {"action": "incident", "domain": "devex", "q": "Why did run R-1042 fail?"}
        ).encode("utf-8")
        with urllib.request.urlopen(f"{base}/execute", data=form) as response:
            body = response.read().decode("utf-8")
            assert response.status == 200
            assert "outcome: simulated" in body and "sent: false" in body
    finally:
        server.shutdown()
        server.server_close()


def test_server_bad_requests_are_4xx_not_crashes() -> None:
    server, base = _serve()
    try:
        for path, expected in (
            ("/ask", 400),
            ("/nope", 404),
            ("/ask?domain=x&q=y", 400),
        ):
            try:
                with urllib.request.urlopen(f"{base}{path}") as response:
                    status = response.status
            except urllib.error.HTTPError as error:
                status = error.code
            assert status == expected, path
    finally:
        server.shutdown()
        server.server_close()
