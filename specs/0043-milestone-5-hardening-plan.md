# 0043. Milestone 5 plan: hardening — make the eval able to fail again

- **Phase / milestone:** Milestone 5 — Hardening (post-roadmap; the four ROADMAP
  phases are complete and tagged `phase-0`…`phase-4`)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018: decisions recorded here
  instead of asked — except the two project-shaping questions below, which were
  asked)

## Problem

The four roadmap phases are done and **every recorded number is 1.000** across
both batteries (business gold 7 + synthetic 52; devex gold 7 + synthetic 24).
ADR 0007's revisit trigger 2 — *the synthetic battery saturates (every case
passes for two consecutive phases)* — is now true of **both** batteries. This is
not a success to bank; it is the central problem. The project's thesis is *trust
is measured, and the metric can fail*. Right now it cannot fail, which makes the
floor decorative — exactly what CLAUDE.md principle 3 and ADR 0005 forbid.

A second, sharper critique the project must answer: both prior coverage
recoveries (business 0.929 → 1.000; devex 0.917 → 1.000) closed misses the
project itself **planted and predicted** before the eval ever saw them. A fair
reviewer asks: *can it surface a miss you did not author?*

This milestone makes the eval able to fail again — with **un-planted** difficulty
from real data and harder synthetic cases — while keeping faithfulness gated at
1.0 and the trust path deterministic, offline, and key-free.

**Maintainer decisions (asked 2026-06-16, because they are project-shaping):**

1. **Next milestone = the hardening loop** (chosen over a real connector alone,
   agentic/MCP mode, BTP provisioning, and packaging). It is the one candidate
   the project's own principles select: every other option stacks capability on
   top of an eval that can no longer fail.
2. **Hardness source = both** — one **real connector** *and* harder synthetic
   cases. A real connector is the honest source of misses no one planted
   (answering the critique above) and converts the WRITEUP's *claimed* "drop-in
   shaped" property into a *demonstrated* one; synthetic gives controlled
   multi-hop and phrasing coverage.
3. **Determinism line held — pause and ask.** When a harder case exposes a miss
   that can only be closed by an LLM-judge (ADR 0005) or embeddings (ADR 0010) —
   both add a model/cloud dependency and spend and break pure clone-and-run — the
   milestone closes everything it can deterministically, **records the fired
   trigger as a named measured specimen, and stops for the maintainer's explicit
   go-ahead** before introducing any such dependency. No LLM or embedding model
   is added this milestone.

**Connector choice (recorded decision, not asked — no spend, own data):** the
real connector ingests **Tessera's own GitHub Actions history** (repo
`robert-vetter/tessera`). It is real, free, legally unencumbered (the
maintainer's own private repo), self-demonstrating, and — per the Milestone-5
reconnaissance — a genuine source of un-planted misses: real run logs spell
failures `##[error]…` with nanosecond timestamps, ANSI, and TAB-delimited
job/step prefixes, nothing like the synthetic `ERROR <svc>:` shape the RCA
heuristic keys on. The repo's own CI even contains a real, recorded failure
(`uv run ruff format --check .` reformat on the SALT ingestion PR) alongside the
recurring `Docs`/Pages-deploy 404.

## The inverted success criterion

Prior phases succeeded by driving every number **to** 1.000. This milestone
succeeds by the **opposite** shape, and that distinction is the point:

- **At least one un-planted, measured miss is surfaced** (coverage and/or quality
  drops below 1.000 on real or genuinely-harder data) and is then **either closed
  with the smallest honest deterministic mechanism or retained as a named,
  recorded specimen** that fires a standing trigger and is escalated.
- **Faithfulness stays gated at 1.0 throughout** — never weakened, never
  re-defined. Coverage/quality are the metrics allowed to move.
- **The milestone may end with a recorded sub-1.0 coverage number** that names a
  fired trigger (embeddings / semantic routing / LLM-judge). That is **success**,
  not regression: it is the deterministic approach reaching a real boundary with
  a measured number, the honest opposite of saturation. (The existing
  `checkout-svc` 0.846 retained specimen, ADR 0010, is the precedent for keeping
  a named miss on purpose.)
- If everything added still reads 1.000, the milestone **failed its own goal** and
  that is reported plainly, not dressed up.

## Acceptance criteria

- [ ] **The floor actually gates the build.** `uv run tessera-eval`'s non-zero
      exit on a faithfulness breach runs in CI (via `scripts/gate.sh`, the single
      source of truth), not only in the manual `/verify`. Proven by a forced
      breach failing the gate locally.
- [ ] **A real GitHub Actions connector** ingests a committed snapshot of the
      repo's own runs+logs through the **same ingestion door**, with zero engine
      change (ADR 0002 cashed a 4th time). The live fetch is a run-once dev script
      (the only network touchpoint); ingestion and the eval stay offline/key-free.
      Recorded in an ADR (the fetch-vs-ingest boundary).
- [ ] **An un-planted miss is measured and recorded** in `eval/history.jsonl`:
      real-log RCA coverage/quality drops, then the deterministic part is closed
      (`##[error]` marker recognition; failed-job derived from
      conclusion+skipped), and the recovery is recorded. Faithfulness 1.0 at both
      points.
- [ ] **Mixed-modality multi-hop in one turn** (the Phase-2-named gap): a single
      question traverses run → error log → prior incident ticket → fixing PR →
      follow-up, each hop individually cited; the mis-pivot trap (DEVEX-204 is a
      *follow-up*, not the original fix) is caught by the faithfulness floor when
      done naively. Engine stays frozen; all traversal vertical-side.
- [ ] **Free-form phrasing variety** exercises the routers: deterministically
      closeable gaps are closed; genuinely-semantic ones (intent-verb
      mis-routing) are retained as named specimens firing ADR 0006.
- [ ] **Scale**: the synthetic corpora are regenerated larger; metrics hold at
      volume or a scale-dependent miss is surfaced and named.
- [ ] **Trigger status** is consolidated: ADR 0005 / 0006 / 0010 each have a
      concrete committed specimen showing where the deterministic approach reaches
      its boundary; none is acted on across the determinism line; all are
      escalated.
- [ ] **Close**: gate green under multiple `PYTHONHASHSEED` values, all batteries
      re-recorded with `--record`, WRITEUP/STATUS/CHANGELOG updated, tagged
      `milestone-5`, memory updated, next kickoff handed back.

## Scope

**In — the unit breakdown (one PR each, spec each):**

| Unit | Spec | Content |
|---|---|---|
| 1 | 0043 | this plan |
| 2 | 0044 | wire `uv run tessera-eval` into `scripts/gate.sh` so the faithfulness floor gates the build in CI, not only `/verify` |
| 3 | 0045 | real GitHub Actions connector: run-once fetch script + committed snapshot + `sources/github_actions.py`; ADR 0014 (fetch-vs-ingest boundary) |
| 4 | 0046 | real-data RCA — the **measured un-planted miss** then its deterministic close (`##[error]` recognition; derived failed-job); both recorded |
| 5 | 0047 | mixed-modality multi-hop in one turn (latent edges materialized vertical-side; the mis-pivot faithfulness trap; honest omissions) |
| 6 | 0048 | free-form phrasing variety: close the deterministic gaps; retain the semantic ones as ADR 0006 specimens |
| 7 | 0049 | scale the synthetic corpora; re-measure at volume |
| 8 | 0050 | trigger-status specimens (ADR 0005/0006/0010) + milestone close (re-measure, WRITEUP/STATUS/CHANGELOG, tag `milestone-5`, memory, kickoff) |

**Out (explicitly):** any LLM-judge or embedding/semantic-retrieval
implementation (determinism line — escalated, not built); a *second* real
connector or any new source family beyond the GitHub Actions one (principle:
generalize across what exists before adding breadth); BTP/cloud provisioning
(separate, spend-gated, maintainer's call); agentic/MCP mode; multi-field ER;
persistence/multi-tenancy/security. These remain the WRITEUP's named future work.

## Eval impact

This is the **first milestone whose intended impact is to move a number the
"wrong" way and keep it honest.** Expect:

- **Coverage/quality to drop** on real-log RCA (U4) and on the multi-hop and
  phrasing cases (U5/U6) before deterministic closure — the recorded "eval can
  fail again" evidence.
- **Coverage to recover** where the miss is deterministically closeable, recorded
  as a trust-loop pair (drop → fix) on un-planted data.
- **A recorded sub-1.0 coverage specimen to remain** where the miss is genuinely
  undeclarable/semantic (the fired ADR 0010 / 0006 trigger) — the anti-saturation
  end state.
- **Faithfulness pinned at 1.0** at every recorded point. Any faithfulness drop is
  a real bug to fix (or, for the multi-hop mis-pivot, the *intended* catch proving
  the floor still bites), never re-recorded as a new normal.

## Risks / open questions

- **Recording a deliberately-degraded number.** `eval/history.jsonl` is
  append-only; U4 records a coverage drop on purpose to make the failure visible,
  then the recovery. The gate never sees red because faithfulness stays 1.0
  (coverage is reported, not gated). Documented in U4's spec and STATUS so a
  reviewer cloning at the drop commit understands it is intentional.
- **The real corpus is skewed** — 33 of 34 real failures are the same Pages-deploy
  404, one is the ruff-format gate failure. So the real snapshot is used to stress
  **format/vocabulary divergence**, not failure-cause breadth; synthetic stays the
  breadth source. (Reconnaissance risk, recorded.)
- **Engine-leak risk in multi-hop.** All new traversal must stay vertical-side
  (`sources/devex.py` edges, `devex/rca.py` or a new `devex/trace.py`); a generic
  `path()` helper on `KnowledgeGraph` would leak vertical semantics into the
  frozen core (ADR 0008). Guarded by the empty-diff core check at close.
- **Pinned counts** (`test_synthetic.py` == 52, `test_devex_synthetic.py` == 24,
  `test_eval.py` gold 7) are tripwires; every case addition updates them
  deliberately, never silently.
- **Determinism hazards** the maps flagged: `##[error]` marker handling and
  failed-job derivation belong in the **source**, not the engine
  (`chunk_text`/`is_supported` stay general); new time-ordered hops use the
  snapshot/`started` attrs, never wall-clock; multi-entity output is sorted by
  `node.id` to defeat hash-seed flakiness (Phase-2 bit us here).
- **Adding a first devex `ClaimShape`** (if a multi-hop conclusion needs a
  recomputed grammar) changes the "devex proves generality with zero owned
  grammars" story (ADR 0011) — to be weighed in U5 and noted in an ADR addendum if
  taken.
- **The fetch script touches the network and a token.** It is run-once, off the
  eval path, pins explicit `databaseId`s (never "latest N"), and commits scrubbed
  fixtures; the gate stays runnable with the committed snapshot and no token.
