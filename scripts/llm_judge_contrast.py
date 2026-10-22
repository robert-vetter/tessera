#!/usr/bin/env python3
"""LLM-judge vs Tessera on the forged challenge bundle (spec 0140, Q2).

The forged bundle (`scripts/forge_challenge_bundle.py`) is a confident,
well-cited, *wrong* answer. Two verification styles are asked the same
question — is each claim faithful to its cited evidence?

- **Tessera** (deterministic): re-sums the cited rows. The inflated totals
  don't add up → the claims fail. This is what `tessera verify` does.
- **An LLM faithfulness judge** (Claude, the same task an LLM-as-judge
  evaluator like RAGAS performs): "given this context, is this statement
  supported?" — a semantic judgement, not a recomputation.

This script records what each says, side by side. **The LLM is the measured
subject here, never part of Tessera's trust path** — it judges nothing the
engine relies on. The result is one recorded measurement (model + prompt
disclosed), not a CI-gated claim; a run is a few API calls.

Run (needs a key): `set -a; source .env; set +a; uv run python
scripts/llm_judge_contrast.py`. With no key it prints how to run and exits 0
(never fails CI, never a hard dependency).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tessera.bundle.verify import verify_bundle
from tessera.platform.config import PROVIDER_ANTHROPIC, load_config
from tessera.platform.providers import AnthropicProvider, ProviderError

FORGED = Path(__file__).resolve().parents[1] / "data" / "challenge" / "forged.tsb"

_JUDGE_SYSTEM = (
    "You are a faithfulness evaluator, the kind used to score retrieval-"
    "augmented answers. Given a CONTEXT (source records) and a STATEMENT, "
    "decide whether the statement is supported by — can be inferred from — the "
    "context. Reply with STRICT JSON only: "
    '{"faithful": true|false, "confidence": 0.0-1.0, "reason": "<one sentence>"}.'
)


def _entity(claim_text: str) -> str | None:
    """The customer a claim is about, from its own text (``'<name>': …``)."""
    match = re.match(r"'([^']+)'", claim_text)
    return match.group(1) if match else None


def _claim_context(claim: dict[str, object]) -> str:
    """A FAIR context: the cited records, explicitly attributed to the claim's
    customer so entity-linking is not the blocker — the only thing left to
    check is whether the stated total follows from the rows (the arithmetic
    Tessera recomputes)."""
    support = claim.get("support")
    records = []
    if isinstance(support, list):
        for item in support:
            if isinstance(item, dict):
                records.append(f"- {item.get('text', '')}")
    entity = _entity(str(claim.get("text", "")))
    header = (
        f"All {len(records)} sales records below are orders of {entity}.\n"
        if entity
        else ""
    )
    return header + "\n".join(records)


def _judge(provider: AnthropicProvider, claim: dict[str, object]) -> dict[str, object]:
    prompt = (
        f"CONTEXT:\n{_claim_context(claim)}\n\n"
        f"STATEMENT:\n{claim.get('text', '')}\n\n"
        "Is the statement faithful to the context? JSON only."
    )
    raw = provider.complete(_JUDGE_SYSTEM, prompt)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"faithful": None, "confidence": None, "reason": f"unparsed: {raw[:80]}"}
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {"faithful": None}
    except json.JSONDecodeError:
        return {"faithful": None, "confidence": None, "reason": "invalid JSON"}


def main() -> int:
    cfg = load_config()
    if not cfg.anthropic_api_key:
        print(
            "no ANTHROPIC_API_KEY — this is a manual one-shot, not part of the "
            "gate.\nrun: set -a; source .env; set +a; "
            "uv run python scripts/llm_judge_contrast.py"
        )
        return 0
    # Build the Anthropic judge directly (independent of the narrator setting).
    provider = AnthropicProvider(
        config=cfg.__class__(**{**cfg.__dict__, "provider": PROVIDER_ANTHROPIC})
    )

    bundle = json.loads(FORGED.read_text(encoding="utf-8"))
    report = verify_bundle(bundle)
    tessera_by_index = {c.index: c.rederived for c in report.claims}
    claims = bundle["result"]["claims"]

    print(f"model: {cfg.anthropic_model}")
    print(f"bundle: data/challenge/forged.tsb — Tessera verdict {report.verdict}\n")
    llm_faithful = tessera_faithful = 0
    for index, claim in enumerate(claims):
        try:
            verdict = _judge(provider, claim)
        except ProviderError as error:
            print(f"claim {index}: judge error — {error}")
            continue
        llm_ok = bool(verdict.get("faithful"))
        tess_ok = tessera_by_index.get(index, True)
        llm_faithful += int(llm_ok)
        tessera_faithful += int(tess_ok)
        print(f"claim {index}: {claim['text'][:70]}")
        print(
            f"    LLM judge: {'FAITHFUL' if llm_ok else 'unfaithful'} "
            f"(conf {verdict.get('confidence')}) — {verdict.get('reason', '')[:80]}"
        )
        print(f"    Tessera:   {'re-derived' if tess_ok else 'UNSUPPORTED'}")
    total = len(claims)
    print(
        f"\nsummary: LLM judge scored {llm_faithful}/{total} claim(s) faithful; "
        f"Tessera re-derived {tessera_faithful}/{total}.\n"
        "The judge's verdict depends on how the context is framed and is not "
        "deterministic (see docs/CHALLENGE.md); Tessera's is a recomputation "
        "anyone re-runs offline to the same answer."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
