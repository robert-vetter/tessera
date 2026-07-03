# 0126. RCA recurrence refinement — sharper signature, correct anchor

- **Phase / milestone:** Milestone 19 Unit 5 — the M18-deferred item
  (STATUS 2026-07-03: "recurrence signature (skip generic trailers) +
  recurrence anchor (cite the signature's own chunk) — both to be done
  openly in a later milestone with the batteries re-run"), folded into
  M19 because launch invites strangers to run `connect` + `smoke` on
  their repos, and this is the one *known* failure class waiting for
  them. Admissibility checked: `devex/rca.py` is the **vertical layer**,
  not on the ADR 0008 frozen-core list; the M19 constraint "every battery
  number byte-identical" is kept — measured, not assumed (see below).
- **Issue:** —
- **Status:** approved (autonomous mode).

## Problem

Two related edges in `devex/rca.py`, both surfaced by M18's per-repo
smoke battery on `mkdocs/mkdocs` (a real FAIL — the battery working):

1. **Anchor mismatch (the smoke FAIL).** The recurrence / documented-
   incident claims cite `error_chunks[0]` as the current run's anchor,
   but `_signature()` scans **all** error chunks — on logs where chunk 0
   is error-marked (contains `ERROR`/`##[error]` text) yet carries no
   parseable error line, the signature comes from a later chunk. The
   shared-fragment verifier then correctly rejects the claim (the quoted
   fragment is absent from a cited record): a **true claim built on the
   wrong citation**, caught by our own verifier at answer time on foreign
   data.
2. **Generic-trailer signature (the smoke WARN).** `_signature()` takes
   the *first* error line even when it is the information-free
   `Process completed with exit code N.` trailer and a sharper line
   exists elsewhere — producing weak recurrence signals `smoke` must
   warn about even though a strong signature was available.

**Recorded decisions:**

1. **Signature: first non-generic error line across the run's error
   chunks; fall back to the first error line only when every candidate
   is generic** (generic = the bare exit-code trailer). The trailer-only
   case still produces the trailer signature — and `smoke`'s WARN still
   fires on it, unchanged (it reads emitted claim text, not rca
   internals). Repos with a sharper line stop emitting weak recurrence
   claims, so the WARN disappears exactly where it should.
2. **Anchor: the first error chunk whose text contains the chosen
   signature** — guaranteed to exist (the signature came from one), and
   exactly what the shared-fragment grammar requires of a citation.
3. **Output-neutrality on committed corpora is a measured gate, not an
   intention.** Pre-measured (2026-07-03, script in the PR discussion):
   on every failed run in the devex + github_actions graphs the current
   signature already sits in `error_chunks[0]` and is non-generic —
   except gha run 27014662820, whose generic signature never surfaces in
   any claim (no recurrence, no incident ticket). Therefore both fixes
   are no-ops on committed data. Proof carried in the unit: (a) a
   byte-identical diff of every committed failed run's full RCA render
   before/after, (b) the six eval lines unchanged, (c) the benchmark doc
   pin (already in CI) unchanged.
4. **The mkdocs shape is pinned by fixtures, not by committing foreign
   data** (ADR 0028 keeps workspaces local): unit tests build synthetic
   graphs with (i) an error-marked chunk 0 without a parseable error
   line + the signature in chunk 1, and (ii) a trailer-first log with a
   sharper line available — asserting the anchor carries the signature,
   `is_supported` passes the recurrence claim, and the sharper signature
   wins; plus (iii) a trailer-only log keeps the trailer (fallback).
5. **Adversarial review before merge** (trust-bearing: this constructs
   verifier-checked claims): one focused correctness/behavior review;
   findings fixed or recorded.

**Review amendments (2026-07-03 — 1 MAJOR, 2 MINOR, 1 NIT, all fixed):**

6. **Signature candidates are verifier-aware** (the MAJOR): the sharper
   preference as first written could select fragments the shared-fragment
   grammar structurally cannot check — a line containing `"` (breaks the
   verifier's parse) or one normalizing to empty (non-Latin /
   punctuation-only) — re-opening the claims-supported FAIL class on
   realistic foreign logs (demonstrated: `Missing config key "docs_dir"`).
   Now: prefer the first verifiable non-generic line, else the first
   verifiable line; if **no** verifiable candidate exists, emit **no**
   recurrence/incident claim at all (a claim our own verifier rejects is
   forbidden — ADR 0005 / spec 0029; the verbatim error chunks still
   speak). Whitespace-only `##[error]` remainders are dropped as
   candidates (empty "appears" everywhere and verifies nowhere).
7. **Negative exit codes are generic too** (`-?\d+`), and — a recorded
   scope amendment — `smoke`'s `_TRAILER` regex gets the same one-token
   change: the two regexes encode one definition of "generic trailer";
   moving one without the other would let a negative-code trailer count
   as "sharp" in rca yet escape the smoke WARN. (`The operation was
   canceled.` was noted as another information-free runner line —
   semantics, out of scope, recorded here.)
8. **The anchor is the extraction chunk** — `_signature` returns
   `(line, chunk)`, so an earlier error-marked chunk that merely quotes
   the signature text incidentally can never displace the true source
   (and the unreachable `ValueError` path is gone).
   All four review shapes are pinned as fixtures; the committed-corpora
   render diff was re-run after the fixes: still byte-identical.

## Acceptance criteria

- [ ] Both fixes implemented in `tessera/devex/rca.py` (vertical layer
      only; no core, eval, or smoke change).
- [ ] Fixture tests (decision 4) green; the mkdocs failure class is
      reproduced by fixture (i) failing on the OLD code (demonstrated in
      the PR) and passing on the new.
- [ ] Byte-identical RCA renders on all committed failed runs
      before/after (decision 3a).
- [ ] Gate green; **all six eval lines byte-identical**; benchmark doc
      pin untouched.
- [ ] PILOT.md's "planned work" sentence about the sharper signature /
      anchor edge updated to reflect it shipped.
- [ ] Adversarial review run; findings addressed.

## Scope

**In:** `_signature` + anchor selection in `devex/rca.py`; fixture tests;
the PILOT.md sentence.
**Out:** any core module (ADR 0008); `smoke` (its WARN contract is
already correct); recurrence *semantics* (what counts as prior/same
signature); re-snapshotting foreign repos; committing any foreign data.

## Eval impact

**None, proven** — decision 3's three-way proof. (On foreign mkdocs-class
repos the effect is the point: `smoke`'s claims-supported check goes
FAIL → PASS because the citation is now correct.)

## Risks / open questions

- If the neutrality proof had failed, the recorded fallback was to defer
  to a dedicated milestone with transparently re-recorded numbers; the
  pre-measurement made this moot.
- No ADR: no data model, boundary, or metric definition changes — two
  selection rules inside one vertical answer path, each the strictly
  more-correct reading of contracts that already exist (the
  shared-fragment grammar; spec 0119's weak-signal caveat).
