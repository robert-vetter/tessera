"""``uv run tessera-ui`` — the one-page web surface over the trust objects.

Pure stdlib: ``http.server`` + the agent boundary layer, nothing else
(ADR 0027). The server is stateless over the committed demo data (domain
engines are built once and cached by the grounded layer), holds **no
credential**, and wires the **simulated** actuator only — a hosted instance
can, by construction, neither send anything nor leak anything. Narration is
optional per environment (``TESSERA_NARRATOR``, ADR 0013) and simply stays off
key-free.

Every response carries a strict CSP (``default-src 'none';
style-src 'unsafe-inline'``): the page ships zero JavaScript and zero external
assets, so the browser is told to load nothing else — the web analogue of the
engine's zero-dependency posture.
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from tessera.agent.actions import available_actions, draft_action
from tessera.agent.execution import execute_action
from tessera.agent.grounded import (
    GroundedResult,
    assertions,
    available_domains,
    ground,
)
from tessera.agent.payloads import preview_payload
from tessera.platform.providers import ModelProvider, ProviderError, provider_from_env
from tessera.surface.narration import narrate_texts
from tessera.ui import render

_SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    ("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'"),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
)

# Built once at startup by main(); None → deterministic rendering only.
_NARRATOR: ModelProvider | None = None


def _narrate(result: GroundedResult) -> tuple[str | None, str | None]:
    """Narration for a GroundedResult under the ADR 0013 boundary — None
    whenever deterministic rendering must stand alone (no narrator configured,
    or a refusal, which is never narrated)."""
    if _NARRATOR is None or not result.grounded:
        return None, None
    return narrate_texts(
        result.question, [claim.text for claim in result.claims], _NARRATOR
    )


class TesseraUIHandler(BaseHTTPRequestHandler):
    """Routes: ``/`` · ``/ask`` · ``/assertions`` · ``/action`` · ``/payload``
    (GET) and ``/execute`` (POST — approval is an explicit submit, never a
    link). Unknown paths 404; bad parameters 400; every page HTML-escaped by
    the render layer."""

    server_version = "TesseraUI"
    sys_version = ""  # no Python version advertisement

    # -- plumbing ----------------------------------------------------------

    def _send(self, status: int, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        for name, value in _SECURITY_HEADERS:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def _params(self, query: str, *names: str) -> list[str]:
        parsed = parse_qs(query, keep_blank_values=True)
        missing = [name for name in names if not parsed.get(name, [""])[0].strip()]
        if missing:
            raise ValueError(f"missing parameter(s): {', '.join(missing)}")
        return [parsed[name][0].strip() for name in names]

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # One quiet line per request (BaseHTTPRequestHandler default is noisy).
        pass

    # -- routes ------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        split = urlsplit(self.path)
        try:
            if split.path == "/":
                domains = available_domains()
                self._send(200, render.index_page(domains, domains[0]))
            elif split.path == "/ask":
                domain_name, question = self._params(split.query, "domain", "q")
                result = ground(domain_name, question)
                narration, notice = _narrate(result)
                self._send(
                    200,
                    render.answer_page(result, available_actions(), narration, notice),
                )
            elif split.path == "/assertions":
                domain_name, record_id = self._params(
                    split.query, "domain", "record_id"
                )
                items = assertions(domain_name, record_id)
                self._send(200, render.assertions_page(domain_name, record_id, items))
            elif split.path == "/action":
                action, domain_name, question = self._params(
                    split.query, "action", "domain", "q"
                )
                proposal = draft_action(action, domain_name, question)
                self._send(200, render.action_page(proposal))
            elif split.path == "/payload":
                action, domain_name, question = self._params(
                    split.query, "action", "domain", "q"
                )
                payload = preview_payload(action, domain_name, question)
                self._send(200, render.payload_page(payload))
            else:
                self._send(404, render.error_page(404, "no such page."))
        except ValueError as error:
            self._send(400, render.error_page(400, str(error)))

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        split = urlsplit(self.path)
        try:
            if split.path != "/execute":
                self._send(404, render.error_page(404, "no such page."))
                return
            # Cap the read (review S1): the real form is a few hundred bytes;
            # an attacker-declared Content-Length must not pin a thread on a
            # blocking read for bytes that never arrive.
            length = min(int(self.headers.get("Content-Length") or 0), 64 * 1024)
            if length < 0:
                raise ValueError("negative Content-Length")
            body = self.rfile.read(length).decode("utf-8") if length else ""
            action, domain_name, question = self._params(body, "action", "domain", "q")
            # The explicit form submit IS the approval; the actuator is the
            # simulated default — the UI has no path to the real one (ADR 0027).
            receipt = execute_action(action, domain_name, question, approve=True)
            self._send(200, render.receipt_page(receipt))
        except ValueError as error:
            self._send(400, render.error_page(400, str(error)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera-ui",
        description=(
            "Serve the one-page web surface over the grounded engine "
            "(stdlib-only; simulated actions; no credential)."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1", help="bind address")
    parser.add_argument("--port", type=int, default=8033, help="port (0 = ephemeral)")
    args = parser.parse_args(argv)

    global _NARRATOR
    try:
        _NARRATOR = provider_from_env()
    except (ProviderError, ValueError) as error:
        print(f"[narration disabled: {error}]")
        _NARRATOR = None
    mode = (
        f"narration via {_NARRATOR.name} (ADR 0013 boundary)"
        if _NARRATOR is not None
        else "deterministic rendering"
    )

    server = ThreadingHTTPServer((args.host, args.port), TesseraUIHandler)
    host, port = str(server.server_address[0]), server.server_address[1]
    print(
        f"Tessera UI → http://{host}:{port}  ({mode}; simulated actions only; "
        "Ctrl-C to stop)"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye.")
    finally:
        server.server_close()
    return 0
