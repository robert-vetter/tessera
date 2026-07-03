# 0114. Milestone 17 Unit 3: the web surface (ADR 0027)

- **Phase / milestone:** Milestone 17 Unit 3 — see spec 0112.
- **Issue:** —
- **Status:** implemented

## Problem

The audit's demo verdict: everything is a terminal. A stranger — a Z Fellows
reviewer, a design-partner prospect, a recruiter — needs to *see* the trust
contract work in under three minutes: grounded claims with verdicts, a
provenance drill-down, a principled refusal, and the action arc ending in a
receipt. The presentation must be a strict consumer of the existing trust
objects and must weaken nothing (no new deps, no credential, no new answer
path).

## Acceptance criteria

- [x] `uv run tessera-ui` (new `[project.scripts]` entry; `tessera/ui/`,
      pure stdlib — ADR 0027) serves: `/` (ask form, per-domain sample
      questions, the measured floor from `eval/history.jsonl`), `/ask`
      (route + reason, numbered claims with per-claim verifier chips,
      `<details>` provenance with full records and ER-trail links, refusals
      as refusal cards, optional ADR 0013 narration strictly below the
      claims), `/assertions` (the reversible ER trail), `/action` (field-
      verified proposal or carried refusal), `/payload` (exact request +
      slots, or withheld — no approve form), `POST /execute` (explicit
      approval → **simulated** receipt; the UI has no path to the real
      actuator).
- [x] **Escape-everything** (`ui/render.py::_e`), pinned by hostile-content
      tests (script/attribute injection through claim text, evidence,
      locators, refusals, narration — displayed inert, never interpreted).
- [x] Strict security headers on every response
      (`CSP default-src 'none'; style-src 'unsafe-inline'`, nosniff,
      no-referrer), pinned by the socket smoke test; zero JavaScript.
- [x] Presentation honesty pinned: verdict chips mirror `verified`; the trust
      line goes red if any claim is unverified; withheld payloads render no
      approve form; receipts say `outcome: simulated · sent: false`.
- [x] `narrate_texts` extracted in `surface/narration.py` (behaviour-
      preserving refactor) so the UI narrates a `GroundedResult` under the
      same guard the chat uses for an `Answer`.
- [x] Verified visually (local preview: index, RCA answer with opened
      provenance, dry-run payload page); `.claude/launch.json` added for
      one-command preview.
- [x] 10 new tests (`tests/test_ui.py`); gate green; every battery number
      byte-identical; **focused pre-merge adversarial review** (XSS/security,
      trust-presentation honesty, docs accuracy).

## Scope

**In:** the above. **Out:** auth/multi-tenancy (ADR 0027 records the public
read-only demonstrator posture); streaming/JS niceties; any engine, verifier,
or agent-layer change beyond the narration refactor; hosting itself (Unit 5).

## Eval impact

None — a consumer surface. Proven at the gate (floors unchanged).

## Risks / open questions

- Evidence text is attacker-shaped in principle: the single escape door +
  CSP + zero-JS is the defense in depth; the review's job is to break it.
- A hosted instance exposes compute (each request builds answers): fine for a
  demo behind a small host; rate limiting is the host's job, noted in the
  Unit 5 runbook.
