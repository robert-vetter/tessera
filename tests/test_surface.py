"""The Joule-style surface (spec 0040): explorable provenance, live trust,
and the ADR 0013 narration boundary — all verified offline, key-free."""

from __future__ import annotations

import io
from dataclasses import dataclass

import pytest

from tessera.surface.cli import main, repl
from tessera.surface.narration import (
    DISCARDED_NOTICE,
    SYSTEM_PROMPT,
    introduces_new_facts,
    narrate,
)
from tessera.surface.session import ChatSession

# --- session: routing + live verification ------------------------------------


def test_business_question_is_routed_and_live_verified() -> None:
    session = ChatSession()
    turn = session.ask("Compare Müller Logistik and Nordwind Logistik totals.")
    assert turn.vertical == "business"
    assert turn.route.kind == "multi"
    assert turn.answer.is_grounded
    assert turn.verified and turn.all_verified  # the eval's verifier, live


def test_devex_question_after_switch() -> None:
    session = ChatSession()
    session.switch("devex")
    turn = session.ask("Why did run R-1042 fail, and has this happened before?")
    assert turn.route.kind == "rca"
    assert turn.all_verified


def test_switch_rejects_unknown_vertical() -> None:
    with pytest.raises(ValueError, match="unknown vertical"):
        ChatSession().switch("finance")


def test_claim_exploration_reaches_records_and_assertions() -> None:
    session = ChatSession()
    session.switch("devex")
    session.ask("Who is on call for notifications-service?")
    claim = session.claim(1)
    assert claim.support
    trail = session.assertions_about("Component:SVC-NOTIF")
    assert any("declared catalog alias" in a.reason for a in trail)


def test_claim_exploration_guards() -> None:
    session = ChatSession()
    with pytest.raises(LookupError, match="no answer"):
        session.claim(1)
    session.ask("What is Müller Logistik's total order value?")
    with pytest.raises(LookupError, match="claim number"):
        session.claim(99)


# --- narration: the ADR 0013 boundary ----------------------------------------


@dataclass(frozen=True)
class FakeProvider:
    reply: str

    @property
    def name(self) -> str:
        return "fake"

    def complete(self, system: str, prompt: str) -> str:
        assert system == SYSTEM_PROMPT  # the narrator speaks only as designed
        return self.reply


def _grounded_turn() -> tuple[ChatSession, str]:
    session = ChatSession()
    session.switch("devex")
    turn = session.ask("Why did run R-1042 fail?")
    claims = "\n".join(c.text for c in turn.answer.claims)
    return session, claims


def test_faithful_narration_is_accepted() -> None:
    session, _ = _grounded_turn()
    assert session.last_turn is not None
    narration, notice = narrate(
        session.last_turn.answer,
        FakeProvider(
            "Run R-1042 failed in integration-tests; the same "
            "timeout appeared before and is documented in DEVEX-187."
        ),
    )
    assert narration is not None and notice is None


def test_fabricated_id_is_discarded_with_notice() -> None:
    session, _ = _grounded_turn()
    assert session.last_turn is not None
    narration, notice = narrate(
        session.last_turn.answer,
        FakeProvider("The failure is fixed by PR-999 and affects 7,500 users."),
    )
    assert narration is None
    assert notice == DISCARDED_NOTICE


class ExplodingProvider:
    """A provider that must never be reached."""

    @property
    def name(self) -> str:
        return "exploding"

    def complete(self, system: str, prompt: str) -> str:
        raise AssertionError("a refusal must never reach the narrator")


def test_refusals_are_never_narrated() -> None:
    session = ChatSession()
    session.switch("devex")
    turn = session.ask("What colour is the sky?")
    assert not turn.answer.is_grounded
    narration, notice = narrate(turn.answer, ExplodingProvider())
    assert narration is None and notice is None


def test_novelty_guard_token_logic() -> None:
    source = "Run R-1042 failed after 30s; see DEVEX-187."
    assert not introduces_new_facts("R-1042 failed after 30s (DEVEX-187).", source)
    assert introduces_new_facts("R-1042 failed; roll back PR-201.", source)
    assert introduces_new_facts("It failed 42 times.", source)


# --- the CLI door --------------------------------------------------------------


def test_one_shot_prints_route_trust_and_provenance(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["Why did run R-1042 fail?", "--vertical", "devex"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "[devex · route: rca" in out
    assert "[1]" in out and "↳" in out
    assert "✓ trust:" in out and "verifier-checked" in out
    assert "narration" not in out  # key-free default: no narration block


def test_repl_session_commands(capsys: pytest.CaptureFixture[str]) -> None:
    script = io.StringIO(
        ":vertical devex\n"
        "Who is on call for notifications-service?\n"
        ":show 1\n"
        ":trust\n"
        ":help\n"
        ":quit\n"
    )
    repl(script, ChatSession())
    out = capsys.readouterr().out
    assert "[vertical: devex]" in out
    assert "✓ trust:" in out
    assert "snapshot    2026-06-10" in out  # :show walks to the origin
    assert "declared catalog alias" in out  # …and the assertion trail
    assert "floor: any faithfulness < 1.0 fails the build" in out
    assert ":vertical business|devex" in out  # help text


def test_repl_handles_unknown_commands_and_eof(
    capsys: pytest.CaptureFixture[str],
) -> None:
    repl(io.StringIO(":wat\n"), ChatSession())
    out = capsys.readouterr().out
    assert "unknown command" in out
