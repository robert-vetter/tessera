# 0048. Free-form phrasing variety: close the deterministic gaps, name the ceiling

- **Phase / milestone:** Milestone 5 — Hardening (spec 0043, unit 6)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

The WRITEUP names a real limitation: *"the batteries under-sample free-form
phrasing variety"*, and the rule routers have a literal ceiling — intent is
inferred only from which entity/id a question contains, plus a fixed superlative
word list (ADR 0006). The Milestone-5 reconnaissance found two **latent
correctness bugs** in that machinery, currently untriggered by any case:

1. `_CURRENCY = \b([A-Z]{3})\b` treats *any* uppercase triple as a currency, so
   "highest total — ASK finance" silently scopes a ranking to a non-existent
   currency `ASK` and answers "no orders".
2. `SUPERLATIVE_WORDS` are **substring**-matched, so `most` fires inside
   `almost` and `top` inside `desktop`.

Both are the kind of wrong-answer-with-full-confidence a harder phrasing case
would expose. Separately, reasonable synonyms (`greatest`, `maximum`) are not
recognized at all.

## Acceptance criteria

- [ ] **Deterministic closes** (all additive, no metric regression):
  - `greatest`, `maximum` added to `SUPERLATIVE_WORDS`.
  - a `mentions_superlative()` helper matches on **word boundaries** (fixing the
    substring bug), used by both `business/routing.classify` and `reason`.
  - `superlative()` scopes to the first 3-letter token that is an **actual
    corpus currency**, refusing for a currency otherwise (fixing the `_CURRENCY`
    hijack).
- [ ] **The batteries sample phrasing variety:** two business gold cases — a
  synonym paraphrase that is now answered correctly (`greatest … in EUR` →
  Orion Datentechnik, EUR 197,500.00) and a phrasing that the engine **honestly
  refuses** ("who is our biggest customer?" → asks for a currency rather than
  mixing them).
- [ ] **The genuinely-semantic ceiling is named, not papered over:** intent-only
  words (`rank`, `order`, `lead`, `best`) are deliberately *not* pattern-matched
  — a test pins this as the documented ADR 0006 boundary, carried to spec 0050.
- [ ] All eight prior recorded numbers unchanged; business gold 7 → 9, still
  faithfulness/coverage/quality 1.000; faithfulness 1.000 everywhere.

## Scope

**In:** the `reasoning.py` synonym/word-boundary/currency fixes; the
`routing.py` switch to `mentions_superlative`; two business gold cases; the
reasoning tests (including the documented-ceiling test); the count-pin updates.

**Out:** an LLM/semantic intent parser (the determinism line — escalated as the
ADR 0006 specimen in spec 0050, not built); recognizing `rank`/`lead`/`best`
(force-fitting intent words would be a brittle guess, exactly the trap ADR 0006
trigger 1 warns against); DevEx-side intent phrasing (the run-id grammar already
widened in spec 0046; verb-intent over runs is the same documented ceiling).

## Eval impact

business gold 7 → **9**, all metrics **1.000** (the synonym case is answered,
the biggest-customer case refuses honestly). All other numbers unchanged. The
contribution is **the eval now samples phrasing variety** — closing the
WRITEUP's named under-sampling — plus two real latent bugs fixed before a harder
case could trip them.

## Risks / open questions

- The word-boundary and currency-set fixes change behaviour only for inputs no
  existing case used (verified: all numbers unchanged) — but they are genuine
  behaviour changes, so they ship with their own pinning tests.
- The ceiling is real and stays: phrasings that need intent understanding refuse
  or fall to lexical lookup. That honesty is the point (a correct refusal beats a
  confident guess); the measured trigger to upgrade the router (ADR 0006) has
  still not *fired* with a case the rules must contort to pass — recorded in
  spec 0050's trigger status.
