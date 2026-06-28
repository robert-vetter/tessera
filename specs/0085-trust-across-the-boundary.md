# 0085. Trust across the boundary

- **Phase / milestone:** Milestone 11, Unit 5 (see spec 0081)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018)

## Problem

Milestone 11's thesis is that an agent can call Tessera over MCP and the **trust
contract survives the protocol boundary** (spec 0081, ADR 0022). Units 3–4 built and
transported the grounded-tool layer; this unit *measures* the claim, so the new
capability's effect on the metric is **known** (principle 3 — "no capability is done
until its effect on the metrics is known"). The headline must be earned, not
asserted: a boundary that silently dropped, added, or altered a claim — or turned a
refusal into an answer — would defeat the entire milestone.

## What the measurement found (run before writing this spec)

Running **every gold case** (business 11, devex 9, github_actions 5) through the
grounded-tool layer:

- **Faithfulness is 1.0 across the boundary — universally.** Every emitted claim,
  for every gold case, in every domain, is verifier-supported (`all_verified=True`),
  including the refusal cases (vacuously). The one hard gate is preserved through the
  protocol.
- **The serialization is lossless** (measured): the `GroundedResult` for a case
  carries exactly the underlying `Answer`'s claim texts, support ids, and per-claim
  verdicts — nothing added, nothing dropped.
- **Refusals are preserved** across the boundary for every refuse-gold case bar one
  router-path divergence (below).

Two **dispositional divergences** surfaced — *not* faithfulness breaches (both keep
`all_verified=True`), but honest, recorded differences between the production
**router** path the agent calls (`ground`, the same path `tessera-chat` uses) and the
eval's per-case **engine** dispatch:

1. **`github_actions/05` (synonymy, gold=answer → agent refuses).** The documented
   offline synonymy miss: "Is the published documentation site unreachable for
   visitors?" has zero lexical overlap with the `##[error]HttpError: Not Found` /
   "Ensure GitHub Pages has been enabled" lines; only embeddings bridge it (M6/M7,
   online). The agent layer is **offline / lexical** by Milestone 11's deterministic
   posture (ADR 0022), so it refuses — *exactly as offline CI does* (the recorded
   github_actions gold coverage 0.833). The honest inheritance of a known limitation,
   not a new miss.
2. **`business/05` (ambiguous, gold=refuse → agent answers).** The question is the
   bare word `"Logistik"`. The eval uses `engine=compose`, which runs entity
   resolution, finds it matches *two* firms (Mueller Logistik, Nordwind Logistik),
   and refuses as ambiguous. The **router** classifies a bare term as a lexical
   `lookup` and grounds on the matching records (both firms), every claim faithfully
   cited. A **pre-existing router-vs-engine divergence** — `tessera-chat` grounds it
   too; the eval never caught it because it dispatches `compose` directly. Faithful,
   but it does not *signal* the ambiguity the way `compose` does. Recorded as a
   measured agent-path gap and the unit's named next lever (align the router's
   ambiguity handling with `compose`), **not** fixed here (a frozen-core router
   change, out of this unit's scope).

## The design

1. **Extract `serialize_answer`** in `tessera/agent/grounded.py`: the
   `Answer → GroundedResult` projection (verify each claim, sort support, carry the
   refusal), which `ground()` already does inline. Exposing it lets the boundary be
   measured over the eval's *own* per-case answers, isolating "the boundary preserves
   the contract" from "the router is as good as the engine."
2. **`tests/test_boundary.py`** — the recorded, CI-gated measurement over all three
   batteries' gold sets:
   - **Boundary fidelity (headline).** For every gold case, take the eval's answer
     (the same `Battery.answer` dispatch, offline `index=None`), serialize it, and
     assert claim texts + support ids + per-claim verdicts are **identical** to the
     underlying `Answer`, and a refusal serializes to `refused=True` with its reason.
   - **Faithfulness 1.0 across the boundary.** The verified fraction over all
     serialized gold-case claims is **1.0** — the gated floor, preserved through the
     projection.
   - **Router-path disposition.** Run `ground()` (the router) over every gold case;
     assert `all_verified` for **all**, and the grounded/refused disposition matches
     the gold `kind` **except** the two cases enumerated above, which are pinned with
     their explanation — so a *new* divergence fails the test loudly.
3. **ADR 0005 / 0006 re-examined and recorded unforced.** The structural verifier
   passed across the boundary with no measured case it missed (ADR 0005 not forced);
   the agent *client* may be an LLM but routing stays deterministic and the only
   router-path gap (business/05) is a deterministic alignment lever, not a case that
   *needs* semantic routing (ADR 0006 not forced). Recorded in the test + Unit 6.

## Acceptance criteria

- [ ] `serialize_answer(answer, graph, claim_shapes, *, domain, question, route)`
      extracted in `grounded.py`; `ground()` uses it; behaviour unchanged (the agent
      tests stay green).
- [ ] `tests/test_boundary.py` asserts, over **all** gold cases in all three
      batteries: serialization fidelity (claims/support/verdicts identical to the
      `Answer`); **faithfulness 1.0 across the boundary**; refusal preserved.
- [ ] The router-path disposition test asserts `all_verified` for every gold case and
      pins the two documented divergences (a third would fail).
- [ ] ADR 0005/0006 re-examined; recorded as not forced (test docstring + Unit 6).
- [ ] Gate green (base env); faithfulness 1.0 on all batteries; deterministic across
      `PYTHONHASHSEED`.

## Scope

**In:** the `serialize_answer` extraction; `tests/test_boundary.py` (the recorded
boundary measurement); the honest record of the two router-path divergences.

**Out:**
- **Fixing the router's ambiguity handling (business/05).** A frozen-core router
  change with eval implications; recorded as the next lever, not done here.
- **Closing the synonymy miss on the agent path (github/05).** Requires embeddings;
  Milestone 11 is deterministic/offline by the maintainer's posture. The online
  embedding close is already recorded (M6/M7).
- **A new gated metric / history.jsonl row.** Faithfulness stays the single hard CI
  floor; the boundary measurement is a pinned CI test (an honest "recorded measurement
  point" per spec 0081), not a new gate or a shoehorned battery row.
- **Acting on ADR 0005/0006.** No measured case forces either; re-examined and
  recorded.

## Eval impact

- **Faithfulness — 1.0, now also *proven preserved across the protocol boundary*.**
  The headline is a property newly measured and pinned in CI, not a number that
  moves. The existing battery numbers are untouched (the agent layer is a consumer,
  not an answer path).

## Risks / open questions

- **The boundary test must be anti-tautological.** It compares the serialized result
  to the *independently computed* `Answer` and verdicts, and asserts the verified
  fraction is 1.0 against the eval's own gold — a regression that dropped/altered a
  claim, or a verdict that silently flipped, would fail it. (The verifier's own
  failability is already pinned in `test_metrics.py`.)
- **The two recorded divergences could mask a future regression.** Mitigated by
  pinning them *explicitly* (by case id, with the expected disposition): any *new*
  divergence — or either of these changing shape — fails the test, so the record
  cannot silently grow.
- **business/05 is a real agent-path weakness.** Named honestly as the next lever
  (router ambiguity alignment); faithfulness is unaffected (the answer is faithful to
  its citations), and the chat surface already behaves this way, so M11 surfaces a
  pre-existing gap rather than introducing one.
