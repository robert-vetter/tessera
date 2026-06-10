"""``uv run tessera-chat`` — the Joule-style door over both verticals.

An interactive, explainable session (spec 0040): every route decision is
printed, claims are numbered and traceable on demand, the trust signal is
computed live by the eval's own verifier, and narration (if configured)
renders strictly below the canonical claims under the ADR 0013 boundary.

    uv run tessera-chat                          # interactive session
    uv run tessera-chat "Why did run R-1042 fail?" --vertical devex
    TESSERA_NARRATOR=anthropic uv run tessera-chat   # with narration

Session commands:
    :vertical business|devex   switch the active vertical
    :show N                    explore claim N's provenance in depth
    :trust                     the recorded battery numbers (eval history)
    :help                      this list
    :quit                      leave
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TextIO

from tessera.platform.providers import ModelProvider, ProviderError, provider_from_env
from tessera.surface.narration import NARRATION_LABEL, narrate
from tessera.surface.session import VERTICALS, ChatSession, TurnResult

_HISTORY_PATH = Path(__file__).resolve().parents[3] / "eval" / "history.jsonl"

_HELP = (
    "  :vertical business|devex   switch the active vertical\n"
    "  :show N                    explore claim N's provenance in depth\n"
    "  :trust                     the recorded battery numbers (eval history)\n"
    "  :help                      this list\n"
    "  :quit                      leave"
)


def _render_turn(turn: TurnResult, narrator: ModelProvider | None) -> str:
    """One answer, rendered for the session: route, numbered claims with
    provenance, the live trust line, and (optionally) labelled narration."""
    lines = [f"[{turn.vertical} · route: {turn.route.kind} — {turn.route.reason}]"]
    answer = turn.answer
    if not answer.is_grounded:
        lines.append(answer.refusal or "Refused.")
        return "\n".join(lines)

    for number, claim in enumerate(answer.claims, start=1):
        lines.append(f"[{number}] {claim.text}")
        lines.extend(f"      ↳ {record.source}" for record in claim.support)

    checked = sum(turn.verified)
    total = len(turn.verified)
    if turn.all_verified:
        lines.append(f"✓ trust: {checked}/{total} claims verifier-checked")
    else:
        lines.append(
            f"✗ TRUST WARNING: only {checked}/{total} claims passed the "
            "verifier — this should never happen; the eval gate would fail."
        )

    if narrator is not None:
        narration, notice = narrate(answer, narrator)
        if narration:
            lines.append("")
            lines.append(NARRATION_LABEL)
            lines.append(narration)
        elif notice:
            lines.append(notice)
    return "\n".join(lines)


def _show_claim(session: ChatSession, number: int) -> str:
    claim = session.claim(number)
    lines = [f"claim [{number}]: {claim.text}", ""]
    for record in claim.support:
        lines.append(f"evidence {record.id}")
        lines.append(f"  source      {record.origin.source}")
        lines.append(f"  locator     {record.origin.locator.render()}")
        lines.append(f"  snapshot    {record.origin.ingested_at}")
        lines.append(f"  full text   {record.text}")
        # Identical assertions (e.g. the same mention reason from many log
        # chunks) collapse into one line with a count — depth without noise.
        grouped: dict[tuple[str, float], int] = {}
        for assertion in session.assertions_about(record.id):
            key = (assertion.reason, assertion.confidence)
            grouped[key] = grouped.get(key, 0) + 1
        for (assertion_reason, confidence), count in grouped.items():
            suffix = f" ×{count}" if count > 1 else ""
            lines.append(
                f"  assertion   {assertion_reason} "
                f"(confidence {confidence:.3f}){suffix}"
            )
        lines.append("")
    return "\n".join(lines).rstrip()


def _trust_panel() -> str:
    """The recorded story: the latest eval history entry, made readable."""
    if not _HISTORY_PATH.is_file():
        return "No recorded eval history found."
    last_line = _HISTORY_PATH.read_text("utf-8").strip().splitlines()[-1]
    entry = json.loads(last_line)
    lines = [f"recorded {entry.get('recorded', '?')} — {entry.get('note', '')}"]
    for battery in entry.get("batteries", []):
        gold, synthetic = battery.get("gold", {}), battery.get("synthetic", {})
        lines.append(
            f"  [{battery.get('name')}] gold {gold.get('cases')} cases: "
            f"faithfulness {gold.get('faithfulness')}, coverage "
            f"{gold.get('coverage')}, quality {gold.get('quality')} · "
            f"synthetic {synthetic.get('cases')} cases: faithfulness "
            f"{synthetic.get('faithfulness')}"
        )
    lines.append("  floor: any faithfulness < 1.0 fails the build (tessera-eval, CI).")
    return "\n".join(lines)


def _handle_command(session: ChatSession, command: str) -> str:
    parts = command.split()
    if parts[0] == ":help":
        return _HELP
    if parts[0] == ":trust":
        return _trust_panel()
    if parts[0] == ":vertical":
        if len(parts) != 2 or parts[1] not in VERTICALS:
            return f"usage: :vertical {('|'.join(VERTICALS))}"
        session.switch(parts[1])
        return f"[vertical: {parts[1]}]"
    if parts[0] == ":show":
        try:
            return _show_claim(session, int(parts[1]))
        except (IndexError, ValueError):
            return "usage: :show N   (N = a claim number from the last answer)"
        except LookupError as error:
            return str(error)
    return f"unknown command {parts[0]!r} — try :help"


def _narrator() -> ModelProvider | None:
    try:
        return provider_from_env()
    except (ProviderError, ValueError) as error:
        # A misconfigured narrator must not block grounded answers; say why.
        print(f"[narration disabled: {error}]")
        return None


def repl(stream: TextIO, session: ChatSession) -> None:
    narrator = _narrator()
    mode = "deterministic rendering"
    if narrator is not None:
        mode = f"narration via {narrator.name} (ADR 0013 boundary)"
    print(
        "Tessera — grounded answers with claim-level provenance.\n"
        f"[vertical: {session.vertical} · {mode}]\n"
        "Ask a question, or :help for commands."
    )
    while True:
        print(f"{session.vertical}> ", end="", flush=True)
        line = stream.readline()
        if not line:  # EOF ends the session cleanly
            print()
            return
        text = line.strip()
        if not text:
            continue
        if text in {":quit", ":q", ":exit"}:
            return
        if text.startswith(":"):
            print(_handle_command(session, text))
            continue
        print(_render_turn(session.ask(text), narrator))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera-chat",
        description=(
            "A Joule-style conversational session over both verticals: "
            "explainable routing, explorable provenance, a live trust "
            "signal, optional LLM narration of verified claims."
        ),
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=None,
        help="Ask one question and exit (omit for an interactive session).",
    )
    parser.add_argument(
        "--vertical",
        choices=VERTICALS,
        default="business",
        help="The vertical to start in (default: business).",
    )
    args = parser.parse_args(argv)

    session = ChatSession(vertical=args.vertical)
    if args.question is not None:
        print(_render_turn(session.ask(args.question), _narrator()))
        return 0

    import sys

    repl(sys.stdin, session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
