# 0040. The Joule-style conversational surface: one assistant, visible trust

- **Phase / milestone:** Phase 4 — platform, polish, and the story (spec 0035 Unit 6)
- **Issue:** —
- **Status:** approved (autonomous mode; ADR 0013 records the narration boundary)

## Problem

ROADMAP Phase 4: "the conversational surface polished into a Joule-style
experience with explorable provenance and a visible trust signal." Today each
vertical has a one-shot routed CLI that prints an answer once and exits;
provenance is shown but not *explorable*, the trust numbers live only in the
eval, and there is no conversational session. Separately, ADR 0006's trigger 2
has fired by reaching this phase: a Joule-style interface wants natural
fluency, and the recorded plan is that an LLM **narrates** grounded results —
claims stay verifier-checked; the model never generates facts.

## Acceptance criteria

- [ ] `uv run tessera-chat` opens an interactive session over **both**
      verticals (`:vertical business|devex` switches; the active vertical and
      every route decision are always printed). One-shot mode
      (`tessera-chat "question" --vertical devex`) works for scripting/demos.
- [ ] Claims render numbered; `:show N` expands claim N's provenance — full
      evidence text, source, locator parts, snapshot date, and any
      resolution/mention assertions (with reasons and confidence) attached to
      the cited records. Refusals print their reason, as always.
- [ ] **Visible trust signal**: every answer carries a live verifier line —
      each claim re-checked with the *same* `is_supported` + vertical claim
      shapes the eval uses (✓ n/n verified; a ✗ is loud). `:trust` shows the
      recorded battery numbers from `eval/history.jsonl` (+ badge state), so
      the session links to the measured story.
- [ ] **Optional narration** (ADR 0006 trigger 2, ADR 0013): when a provider
      is configured (`TESSERA_NARRATOR`, spec 0039), a clearly labelled
      narration paragraph renders **after** the canonical claims. A
      deterministic novelty guard discards any narration that introduces
      numbers or id-like tokens absent from the claims/question (with an
      honest notice); provider failure degrades silently to deterministic
      rendering. Default remains no narration, key-free.
- [ ] All trust-bearing behaviour is tested offline (narration via a fake
      provider); eval numbers pinned unchanged.

## Scope

**In:** `tessera/surface/` (session, narration, cli), the `tessera-chat`
entry point, ADR 0013, tests, README/docs touch-ups deferred to Unit 8's
stranger pass except the command's own docstrings.

**Out:** replacing the per-vertical doors (`tessera`, `tessera-devex` stay —
they are the routed demos specs 0020/0031 promised); cross-vertical
auto-routing (guessing which vertical a question belongs to is a new
unmeasured behaviour — explicit switching is honest; revisit with a measured
need); conversation memory/multi-turn reasoning (each question is answered
from evidence alone — follow-up context is future work, named in the
write-up); narration of *refusals* (a refusal is already one honest
sentence).

## Eval impact

None. The surface consumes the same engines and the same verifier; narration
never touches claims. Pinned by the existing eval tests.

## Risks / open questions

- The novelty guard is deliberately conservative (numbers + id-like tokens);
  it cannot catch every possible hallucination shape — recorded as an ADR
  0013 limitation, alongside why narrated text is *presentation*, never
  evidence: the canonical claims are always printed above it.
- REPL ergonomics (input loop) must stay testable: the loop reads from an
  injectable stream and is covered by tests.
