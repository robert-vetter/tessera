# 0026. Best-effort client-side idempotency on the real execution path

- **Status:** accepted
- **Date:** 2026-07-01

## Context

Milestone 14 (ADR 0025) built the opt-in real `GithubActuator` — double-gated on approval
**and** a credential, pure-stdlib `urllib`, an injected transport, contract-tested against
a fake transport — and proved the real path is *real* (it binds, authenticates, and would
send) without ever sending in this repository. It named one honest edge plainly and left
it: *"a real create-issue is not idempotent; re-running would create duplicate issues …
recorded as a caller responsibility, not engineered."*

Milestone 15 crosses the last edge of the execution arc — **actually sending** one grounded
action (the first real, credentialed, irreversible side effect) behind approval — and so it
must close that idempotency gap: a real path that can duplicate on a retry is not one a
trust layer should hand an operator. The maintainer's M15 scope (asked & answered
2026-07-01, spec 0103): (a) engineer honest idempotency on the real actuator as the
**CI-verifiable core** (deterministic, offline, faithfulness gated 1.0, frozen core
untouched); then (b) a single maintainer-triggered real send. This ADR settles *how* the
real path becomes idempotent, and — as important — *how honest* that idempotency can be,
given the target API.

The constraint that shapes everything: **GitHub's `POST /repos/{owner}/{repo}/issues` has
no server-side idempotency key.** Unlike a payment API, you cannot ask GitHub to dedupe a
create. Any idempotency here is *client-side* and therefore *best-effort* — a fact this ADR
refuses to paper over, in keeping with the project's honesty rules (a decorative guarantee
is worse than a named limit).

## Decision

**A deterministic idempotency key identifies a grounded action.** Inside
`GithubActuator.execute`, after both gates pass and before any create, compute
`idempotency_key(payload) = "sha256:" + sha256(canonical_json({method, path, body}))`,
where `canonical_json` sorts keys, uses fixed separators, is UTF-8, and hashes the grounded
body **with the marker excluded** (so the key never depends on itself). The path hashed is
the *unbound* payload path (`{owner}`/`{repo}` still placeholders), so the key is
deployment-independent: the same grounded action has one key regardless of destination, and
per-repo dedup comes from querying *within* the target repo. The key is a pure function of
the grounded request — byte-stable across processes and `PYTHONHASHSEED`.

**The key is embedded as a three-surface marker — declared deployment scaffolding.** On the
outgoing issue/comment the actuator stamps, from one hash: an HTML comment
`<!-- tessera-idempotency-key: sha256:<hex> -->` in the body (the exact, machine-findable
verification target, invisible when the Markdown renders), a human-visible provenance
footer line, and — for an *issue* — a deterministic `idem-<first16hex>` label (a comment
carries no label). The marker is **declared scaffolding**, exactly like the fixed M13 issue
labels and section headings: a deterministic function of already-verified values, asserting
no new claim. It is embedded by the real actuator at send into a *copy* of the body; it
**never enters the M13 renderer or the grounded slots**, so the payload boundary, the
simulated execution boundary, and **faithfulness stay 1.0** everywhere the repo measures.
The simulated default embeds no marker and records the grounded template unchanged.

**The pre-send check reads the primary, immediately-consistent endpoint — deliberately not
search — and pages.** *(The issues URL below is superseded — the label filter was removed;
see the 2026-07-02 addendum.)* Before creating, the actuator queries the target's primary
list endpoint — for an issue, `GET /repos/{owner}/{repo}/issues?state=all&per_page=100&labels=
idem-<hex>`; for a PR comment, `GET …/issues/{pr}/comments?per_page=100` — and **verifies
the exact full marker substring** in a returned candidate's body before trusting it (so a
bare label collision can never be mistaken for a match). It **pages** (`&page=N`) until the
marker is found, a short page ends the thread, or a page cap (`_MAX_PRECHECK_PAGES`, 20 ×
100 = 2000 items) is hit — because a busy PR's comment thread cannot be label-filtered and
can span pages; reading only the first page would miss a marker comment on page 2+ and
duplicate on a plain sequential re-run. If the cap is reached before the thread is fully
scanned, the pre-check **refuses** (`inconclusive`), never risking a duplicate over an
un-scanned page. The eventually-consistent Search API (`GET /search/issues`) is
*deliberately not used*: the issues/comments list endpoints read the primary datastore and
reflect a just-created issue immediately, whereas the search index lags ~a minute. Choosing
the primary endpoint shrinks the residual duplicate window from "any retry within the search
lag" to "a genuine concurrent create" (two sends before either issue is listable).

**On the pre-check, refuse rather than duplicate.** A verified hit short-circuits to a new
`outcome="exists"` (`sent=False`, `executed=False`, the existing resource carried in
`result`). A pre-check that **cannot decide** — the list read raises, or returns non-2xx —
short-circuits to a new `outcome="inconclusive"` (`sent=False`), never a silent create. This
is the groundedness principle applied to a side effect: *a correct refusal beats a confident
duplicate.* Both new outcomes sit beside M14's `withheld`/`simulated`/`created`/`blocked`/
`error`; `withheld_reason` stays reserved for the ungrounded M13 gate (an `exists`/
`inconclusive` action *was* grounded — its detail lives in `outcome` + `result`).

**The receipt records the key and what would be / was sent.** `ExecutionReceipt` gains an
`idempotency_key` field (surfaced in `to_dict()`), populated on the real path
(`created`/`exists`/`inconclusive`/`error`) and `None` on the simulated dry run and the
ungrounded/blocked gates, which form no real send. The `created`/`exists`/`inconclusive`
receipts record the marker-augmented `body` (what was, or would have been, sent) — lossless
with respect to the real request, the same way the `created` path already records the
`{owner}`/`{repo}`-bound path rather than the raw payload path.

**The transport seam grows a read half.** The M14 `Transport` was `post()`-only; the
pre-check needs a read, so the Protocol gains `get(url, *, headers) -> tuple[int, object]`
(the list endpoints return a JSON array, hence `object`), implemented on `_UrllibTransport`
behind `# pragma: no cover - real network, never in CI` and on every injected fake
transport. As in M14, tests drive the actuator against a fake transport; the real
network is never touched in CI, and the actuator is never constructed by the default path.

## Consequences

- **The real path is best-effort idempotent, not exactly-once — stated everywhere.** A
  sequential re-run of the same grounded action into the same repo is deduped reliably (the
  primary endpoint is immediately consistent, and the pre-check pages the thread rather than
  reading only its first page); a genuine concurrent create can still duplicate. A thread
  longer than the page cap does not silently duplicate either — the pre-check refuses
  (`inconclusive`). That residual is named here, in the spec, STATUS, the WRITEUP, and the
  runbook — never asserted away. The blast radius of the one real send is further contained
  to a throwaway sandbox repo.
- **Faithfulness stays the single hard gate at 1.0, across every boundary.** The marker is
  real-path-only scaffolding and never touches the renderer or the grounded slots; the
  payload and simulated-execution boundary measurements are unchanged. The new behavior is
  pinned by fake-transport contract tests (`created` with the marker embedded, `exists`,
  `inconclusive`, exact-marker-not-just-label, an end-to-end re-run dedupe, and PR-comment
  dedupe), not by a new gated metric.
- **A create that fails to attach the `idem-` label degrades to the residual window.**
  *(Superseded — the 2026-07-02 addendum removed this residual: the pre-check is now
  label-independent.)* The mechanism relies on the label being attached (an
  `Issues: write` fine-grained PAT covers it); if it is not, the body's HTML-comment
  marker is still present but the label-filtered list would not surface it, so a re-run
  could duplicate. Named as a known limit, acceptable for the opt-in, sandbox-scoped
  one-shot.
- **The structural-verifier limit (ADR 0005) carries through unchanged.** A slot
  `verified=True`, and now an `idempotency_key`, mean the request is mechanically grounded
  and self-identifying — not that sending it is wise. Approval is still the human/agent gate
  on the real path. ADR 0005/0006 triggers were re-examined at the idempotency path and
  recorded **not forced**: the key, the marker, and the pre-send decision are deterministic
  (a `sha256` + an exact substring match), not an LLM judgment or a semantic route.

## Alternatives considered

- **Use the Search API (`GET /search/issues?q=…in:body…`) to find the marker.** Rejected as
  the primary check: the search index is eventually consistent (~a minute of lag), so a
  retry inside the window would miss an existing issue and duplicate — a much larger residual
  than the primary list endpoint's true-concurrent-race window. The immediately-consistent
  list endpoint keyed on a deterministic label is strictly more honest *(the label keying
  was later removed — 2026-07-02 addendum; the endpoint choice stands)*. (Search could be
  added as a supplementary finder later; it would only widen coverage, never the guarantee.)
- **A deterministic key stamped on the receipt only, with no pre-send read.** Rejected as
  the deliverable: it makes duplicates *detectable* after the fact but prevents none — it
  fails M15's scoped "engineered, CI-verifiable idempotency." (It is subsumed here: the key
  *is* on the receipt, plus the pre-check.)
- **Caller-responsibility only (document, don't implement).** Rejected: it is the M14
  posture M15 was chosen to move past. Kept only as the honest fallback framing for the
  residual window and the label-attach-failure case.
- **Treat an inconclusive pre-check as "not found" and create anyway.** Rejected outright:
  it trades a correct refusal for a possible duplicate, inverting the groundedness principle.
  `inconclusive` refuses.
- **Engineer exactly-once (a server-side idempotency key).** Impossible on GitHub's
  create-issue endpoint; claiming it would be vaporware. Best-effort with a named residual
  is the honest ceiling.
- **Fold the marker into the M13 renderer / grounded slots.** Rejected: it would make an
  unverified deployment string part of the grounded payload and perturb the faithfulness
  measurement. The marker stays real-path scaffolding, added at send, outside the grounded
  set.

## Addendum (2026-07-02, spec 0109 — audit B2/B4): the pre-check is label-independent

The 2026-07-02 audit (finding **B2**) showed the original issues pre-check filtered the
listing by the `idem-` label and scanned bodies only *within* that filtered result —
making dedup silently depend on the label surviving. The original Consequences
**accepted the attach-failure variant as a known limit** rather than engineering it
away; the audit's contribution is eliminating it (and adding the variants the original
did not name: a label deleted later, and GitHub's documented permission-based silent
drop — labels on create are *silently dropped* for callers without push access, which
a least-privilege fine-grained PAT may well be). Any of these would make the filter
return empty and a re-run would **duplicate despite the body marker**.

**Change:** the issues pre-check now scans the **unfiltered** `state=all` listing for
the exact body marker — the same marker scan the comments path always did (the
comments listing has no state dimension to widen). Same pagination, same
refuse-on-cap. The `idem-` label is still embedded, but demoted to a *visible,
non-load-bearing handle* — dedup rests only on the signal that was verified anyway
(the exact marker substring). Costs, stated: the unfiltered listing **includes pull
requests**, which consume the 20×100 page cap, so a busy repo reaches the honest
`inconclusive` refusal sooner; a listed item's `body` can be `null` (skipped);
irrelevant for the sandbox one-shot.

**Residuals now named:**

- **Marker spoof → denial-of-create, and (since the B1 persistence policy) a
  persistable false `exists`:** the marker is a deterministic function of the grounded
  payload, so a party able to place content into the target repo's issues/comments (or
  into a log that reaches an issue body) could pre-embed the exact marker and force a
  false `exists` — never a wrong send, but the resulting receipt's `existing` detail
  would cite the spoofed item and is exactly what the recorder persists. The one-shot
  maintainer therefore **verifies the printed `html_url` is their own issue before
  committing**; a real multi-tenant deployment would need an authorship check on the
  candidate (out of scope, recorded).
- **Mid-scan deletion page-boundary race:** deleting/transferring an item newer than
  the marked issue between page fetches can shift the marker across an already-fetched
  page boundary and skip it — the same class as the genuine concurrent create; requires
  a multi-page listing and second-level timing, impossible on the one-page sandbox.
- **Keys are stable only within a renderer version:** the fence rule (spec 0109, B4)
  feeds the rendered body and therefore the key — do not change the renderer between a
  failed one-shot attempt and its retry.
