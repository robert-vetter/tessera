"""LLM narration of verified claims — rephrase, never add (ADR 0013).

The narrator runs *after* verification and sees only the question and the
claim texts. Its output is presentation: rendered below the canonical
claims, visibly labelled, never citable, never part of the eval. Two
deterministic defences enforce the boundary in code: the novelty guard
(:func:`introduces_new_facts`) rejects narration carrying numbers or
id-like tokens the claims don't contain, and every provider failure
degrades to plain deterministic rendering.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from tessera.grounding import Answer
from tessera.platform.providers import ModelProvider, ProviderError

NARRATION_LABEL = "≈ narration (LLM-phrased from the verified claims; not evidence)"

SYSTEM_PROMPT = (
    "You narrate already-verified evidence. Rephrase the claims below as one "
    "short, plain paragraph answering the user's question. STRICT RULES: use "
    "only facts stated in the claims; never add numbers, names, ids, dates, "
    "causes, or qualifiers that are not in the claims; no speculation; no "
    "advice. If the claims feel insufficient, summarize only what is there."
)

# Fact-like tokens the guard tracks: id-like tokens (R-1042, DEVEX-187,
# SVC-NOTIF, PR-201…) and numbers/amounts (30, 1.42.0, 77,500.00).
_ID_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]*-[A-Z0-9][A-Za-z0-9-]*\b")
_NUMBER = re.compile(r"\d[\d,.:]*")


def _fact_tokens(text: str) -> set[str]:
    tokens = set(_ID_TOKEN.findall(text))
    tokens.update(match.rstrip(".,:") for match in _NUMBER.findall(text))
    return tokens


def introduces_new_facts(narration: str, allowed_source: str) -> bool:
    """True if the narration carries a fact-like token absent from the source
    text (claims + question) — the deterministic novelty guard (ADR 0013)."""
    allowed = _fact_tokens(allowed_source)
    return bool(_fact_tokens(narration) - allowed)


DISCARDED_NOTICE = (
    "(narration discarded: it introduced fact-like tokens absent from the "
    "verified claims — deterministic rendering stands)"
)


def narrate_texts(
    question: str, claim_texts: Sequence[str], provider: ModelProvider
) -> tuple[str | None, str | None]:
    """``(narration, notice)`` for already-verified claim texts — the one
    narration core every surface shares (the chat session narrates an engine
    ``Answer``; the web UI narrates a boundary ``GroundedResult``; both reduce
    to question + verified claim texts, so the ADR 0013 guard runs identically).

    Narration is ``None`` whenever deterministic rendering must stand alone:
    nothing to narrate, provider failure (silent degradation, ADR 0013), or a
    guard rejection — the only case that also carries an honest ``notice``."""
    if not claim_texts:
        return None, None
    claims_text = "\n".join(f"- {text}" for text in claim_texts)
    prompt = f"Question: {question}\n\nVerified claims:\n{claims_text}"
    try:
        narration = provider.complete(SYSTEM_PROMPT, prompt).strip()
    except ProviderError:
        return None, None  # silent degradation: the canonical rendering stands
    if not narration:
        return None, None
    if introduces_new_facts(narration, prompt):
        return None, DISCARDED_NOTICE
    return narration, None


def narrate(answer: Answer, provider: ModelProvider) -> tuple[str | None, str | None]:
    """``(narration, notice)`` for a grounded engine answer — refusals are never
    narrated (already one honest sentence); everything else delegates to
    :func:`narrate_texts`."""
    if not answer.is_grounded:
        return None, None
    return narrate_texts(
        answer.question, [claim.text for claim in answer.claims], provider
    )
