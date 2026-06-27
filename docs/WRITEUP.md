# Tessera — a trust layer for enterprise AI agents

*The technical write-up: what was built, how it is measured, what it cannot
do yet, and what was learned. Every number below is recorded in
[`eval/history.jsonl`](https://github.com/robert-vetter/tessera/blob/main/eval/history.jsonl);
every design decision cites its ADR.*

---

## The problem

Enterprise AI assistants fail in a specific, expensive way: they answer
fluently when they should refuse, and nobody can check where an answer came
from. The data underneath is heterogeneous — database tables, contracts,
CI logs, tickets — and the same real-world entity appears under different
names in each source. Three hard problems hide in that sentence:

1. **Unification.** Structured rows and unstructured text must become one
   queryable body of evidence without losing where anything came from.
2. **Identity.** "Müller Logistik GmbH", "Mueller Logistik Gmbh", and a
   contract that just says "Mueller Logistik" are one company; merging them
   wrongly is as bad as missing them.
3. **Trust.** "The assistant seems accurate" is not an engineering
   statement. Faithfulness has to be *defined*, *measured*, and *gated* —
   or it will quietly degrade.

Tessera is a working answer to all three, built deliberately small: a
vertical-neutral engine, two genuinely different reference verticals on top
of it, and an evaluation harness that treats trust like the build treats
compilation.

## The shape of the system

```
              data/salt_synthetic/        data/business_docs/      data/devex_synthetic/
                  (ERP tables)              (agreements)          (runs, logs, PRs, tickets)
                        │                        │                          │
                        └────────────┬───────────┘──────────────────────────┘
                                     ▼
   core      ingestion (one door) → EvidenceRecord {id, origin{source, locator, date}, text}
 (vertical-  → knowledge graph (nodes + structural edges)
  neutral)   → entity resolution (additive, reversible assertions with reasons)
             → lexical retrieval (BM25, deterministic) → principled refusal
                                     │
             ┌───────────────────────┴────────────────────────┐
             ▼                                                ▼
   tessera/business/                                tessera/devex/
   lookup · cross-source composition ·              RCA grounded in log lines ·
   compare/superlative · conflict surfacing         recurrence + incident links ·
                                                    PR change-summaries · on-call lookup
             └───────────────────────┬────────────────────────┘
                                     ▼
             eval batteries (gold + synthetic per vertical, one floor)
             tessera-chat (explorable provenance, live trust, guarded narration)
```

Five properties hold everywhere, by construction rather than convention:

- **No claim without evidence.** A `Claim` cannot be instantiated without at
  least one supporting record (it raises); an `EvidenceRecord` cannot exist
  without an origin and an in-source locator (ADR 0002). The kind-tagged
  locator has absorbed table rows, document spans, log spans, and diff hunks
  without ever being restructured.
- **A correct refusal beats a confident guess.** Out-of-corpus questions,
  ambiguous entity references, passed runs asked "why did this fail?",
  mixed-currency sums, conflicting renewal dates — each refuses with a
  stated reason. Refusal kinds are gold-set cases, not afterthoughts.
- **Entity resolution is fallible and says so** (ADR 0004). Merges are
  additive assertions carrying a reason and a confidence; resolved entities
  are derived connected components; withdrawing an assertion re-splits the
  cluster with no data loss.
- **Determinism end to end.** No model, no network, no RNG anywhere in the
  trust path — the whole eval reproduces on any machine, key-free (ADR
  0003/0006). The only LLM in the system narrates already-verified claims
  and is mechanically prevented from adding facts (ADR 0013).
- **The engine stays general.** Vertical question shapes live with the
  vertical (`tessera/business/`, `tessera/devex/`), down to the verifier
  grammars each battery declares for its own claims (ADR 0008/0011).

## How trust is measured (and earned)

Three metrics, defined in ADR 0005 and computed identically for every
vertical (ADR 0009):

- **Faithfulness** — the fraction of emitted claims whose content a
  deterministic verifier re-derives from exactly the cited evidence:
  verbatim containment, aggregate recomputation, conclusion recomputation
  over the whole graph, shared-fragment checks for "this happened before"
  claims. **This is the one hard floor**: any battery below 1.0 fails the
  build, locally and in CI.
- **Coverage** — of the evidence a gold case says a good answer should
  surface, how much the answer actually cited. Reported, not gated — it is
  the honest, improvable number.
- **Quality** — answerable cases contain the expected facts; refusal cases
  actually refuse.

Two design rules keep the 1.0 from being decorative:

- **The verifier is provably able to fail.** Its first test injects an
  unfaithful claim (a wrong total over a real row) and asserts it is caught.
  When the verifier was first wired up, it immediately caught a real
  under-citation in the composition layer — the metric did its job before it
  ever reported a clean number.
- **Synthetic cases are data-derived, never engine-echoed** (ADR 0007).
  Expectations come from reading the corpus (which log lines carry the error;
  which ticket a PR references), not from running the engine — so the
  battery cannot be a tautology.

### The recorded trail

| date | event | business gold coverage | devex gold coverage |
|---|---|---|---|
| Phase 1 close | first real numbers; the Lumière document-mention miss is *named* | **0.929** | — |
| Phase 2 mid | routing, multi-step, conflicts land | 0.938 | — |
| Phase 2 close | NFKD diacritic folding + suffix-tolerant mentions close the named miss (ADR 0004 addendum) | **1.000** | — |
| Phase 3 close | the DevEx battery lands; the *planted, predicted* `notif-svc` miss is measured | 1.000 | **0.917** |
| Phase 4, unit 2 | a **declared catalog alias** closes the measured miss (ADR 0010) | 1.000 | **1.000** |

Faithfulness was 1.000 (gated) and quality 1.000 at every recorded point;
synthetic batteries (52 business + 24 devex cases) have been at 1.000
across all three metrics since they landed.

The trail is the story: at no point did a number improve by weakening a
check. The two coverage recoveries are the project's central pattern — the
**trust loop**: *plant or discover a realistic difficulty → let the metric
measure it as a named miss → fix it with the smallest honest mechanism →
re-measure → record*. Both misses were known and documented before the eval
ever saw them; both fixes are deterministic and inspectable (a Unicode
normalization rule; a declared alias in a catalog file).

### Why not embeddings (yet)

The `notif-svc` miss fired the standing revisit triggers for semantic
retrieval and ML matching (ADR 0003/0004). The reassessment is recorded in
ADR 0010: the miss was closeable by *declaring data* — exactly how a real
organization fixes a catalog gap — so embeddings would have bought zero
measured improvement at the cost of non-determinism and a cloud dependency.
The refreshed trigger is precise: embeddings arrive when a **measured**
coverage miss exists that *no declarable data could fix*. A deliberately
retained specimen exists (`checkout-svc`, similarity 0.846, undeclared) so
the boundary of the current mechanism stays visible and tested. *(Milestone 6
acted on this — the refreshed trigger fired on Milestone 5's error-class-synonymy
specimen; see "Milestone 6: embeddings on SAP" below.)*

### Post-roadmap hardening: making the eval able to fail again

By the close of the four roadmap phases every recorded number was 1.000 and
both synthetic batteries had saturated (ADR 0007 trigger 2). A floor that
cannot fail is decorative, so a fifth milestone set out to make the eval able
to fail again — with **un-planted** difficulty, holding faithfulness gated at
1.0 and the trust path deterministic.

- **A real connector.** The project's own GitHub Actions history is ingested
  through the same door (a committed snapshot; the live fetch is a run-once
  script, the only network touchpoint — ADR 0014). Real CI logs spell failures
  `##[error]` with nanosecond timestamps and TAB-delimited job/step prefixes —
  nothing like the synthetic `ERROR <svc>:` shape — so the saturated eval
  finally measured a miss **no one authored**: GitHub-Actions gold coverage
  **0.000**, quality 0.500. The deterministic close (recognize real run ids, the
  `##[error]` marker, and the first such line as the signature — all additive)
  recovered it to **1.000**, including a genuine cross-run recurrence over two
  real Pages-deploy failures. The drop and the recovery are both recorded.
- **Multi-hop in one turn.** RCA now walks the incident ticket to the PR that
  resolved it and the diff that did it — `run → log → prior log → ticket → PR →
  diff`, each hop cited — closing the gap Phase 2 named. The mis-pivot trap (a
  follow-up PR that fixes a *different* ticket) is avoided structurally and
  guarded by the floor.
- **Phrasing variety, and its ceiling.** The router gained synonyms,
  word-boundary matching, and currency-set validation (two latent bugs fixed);
  the batteries now sample free-form phrasing. Intent-only words (`rank`,
  `lead`, `best`) are left as the named ADR 0006 ceiling, not force-fit.
- **Scale, measured.** The engine is faithful and ER-precise over 180 entities;
  and the over-merge risk is now a reproduced fact — generic-suffix firms cross
  the 0.85 threshold at volume.
- **The floor actually gates.** `tessera-eval` now runs inside the shared gate
  script, so the faithfulness floor fails the build in CI, not only in the local
  verify step.

The honest end state inverts the roadmap phases: rather than driving every
number back to 1.000, the milestone leaves three **named specimens** where the
deterministic approach reaches its edge — a verbatim-but-misleading claim the
structural verifier passes (ADR 0005), an error-class synonymy no declared alias
could bridge (ADR 0010), and the intent-verb router ceiling (ADR 0006). Each is
a committed test; none is acted on, because crossing into an LLM or embedding
dependency is a spend / clone-and-run decision held for the maintainer.

### Milestone 6: embeddings on SAP — the first named miss closed by a method upgrade

Milestone 5 deliberately *kept* its hardest specimen: the error-class synonymy in
the real Pages-deploy log (`HttpError: Not Found` ≈ `status: 404` ≈ `Ensure
GitHub Pages has been enabled`), a measured miss no declared catalog data could
fix — the exact firing condition ADR 0010 had set for embeddings. Milestone 6
acted on it, and did so **on real SAP infrastructure**.

The build kept the trust line intact. Embeddings serve **retrieval only** — they
change *which evidence is surfaced*, never *what is claimed or how a claim is
verified*; a subprocess leak-guard pins that the faithfulness verifier imports no
embedding module, so a 1.0 stays earned by structure, not a model. The seam is
two backends behind one protocol (so the design is not cloud-locked): SAP
Generative AI Hub embeddings stored in HANA's vector engine, and — after the
GenAI Hub deployment proved hard to configure — **HANA Cloud's in-database
`VECTOR_EMBEDDING`**, where one SAP service does embedding, storage, and KNN
(ADR 0015 records the pivot). Offline and in CI, retrieval falls back to the
deterministic lexical path, key-free.

A new `github_actions` gold case asks, in pure out-of-log vocabulary, *"is the
published documentation site unreachable for visitors?"* — sharing **zero
tokens** with any record. Lexical BM25 returns nothing → a recorded miss (gold
coverage **0.833**, quality 0.800). Then the live run: HANA Cloud in-database
`VECTOR_EMBEDDING` (`SAP_NEB.20240715`, 768-dim) + `COSINE_SIMILARITY` closed it
— coverage **1.000**, quality **1.000**, faithfulness 1.0 throughout. Both points
are in `eval/history.jsonl`. This is the **inverse of Milestone 5**: a
previously-recorded, named miss closed by a real method upgrade, measured on
cloud infrastructure — *designed for SAP* became *ran on SAP*.

Two honesties came with it. The recorded number is a **timestamped online
measurement, not a CI-reproducible one** — the cloud model can change, so CI
stays on lexical and `github_actions` gold still reads 0.833 there. And SAP's
embedding shows **long-document dilution**: it bridges the concept (every
`Docs`-failure record outranks the unrelated ruff failure), but the concise
run-status *row* outranks the long, noisy error-*log* chunk, so the answer
surfaces the failed run rather than the specific 404 line — recorded as a named
limitation, not papered over by inflating the retrieval depth.

### Milestone 7: embeddings beyond retrieval — entity resolution and de-diluted logs

Milestone 6 confined embeddings to retrieval and named two limitations as the
next steps. Milestone 7 acted on both, holding the same line — embeddings touch
*linking*, never the claim path (the leak-guard now also bans the new ER module).

**Embedding-assisted entity resolution.** ER had stayed pure-`difflib` character
similarity, with two opposite-signed misses: `checkout-service ↔ checkout-svc`
(0.846, just under the 0.85 threshold) needs *more* merging; the generic-suffix
firms (`… Logistik GmbH`) over-merge at volume and need *less*. A naive name-cosine
pass closes the first and worsens the second. The fix is to embed the **distinctive
stem** — the name with its generic tokens (legal forms, universal descriptors,
corpus-frequent words) removed — and merge on stem cosine: `checkout-service` and
`checkout-svc` both reduce to `checkout` and merge, while `Granite`/`Pyrite`
`Logistik GmbH` reduce to distinct stems and stay apart (ADR 0016). A new module
proposes ordinary additive, reversible `Resolution`s; the deterministic
`difflib` pass and the engine graph are untouched, and the application is
vertical-side (the ADR 0010 alias precedent). A labeled ER pair-set
(`tests/test_er_metrics.py`) **measures** the effect: `difflib` alone scores
precision 0.50 / recall 0.50 on the set; the stem-embedding regime scores
**1.00 / 1.00**.

**Finer log chunking.** `parse_log_chunks` now splits a runner-log group at its
`##[error]` marker, isolating the failure cluster (with a few lines of diagnostic
context) into its own short chunk — the Pages-deploy 404 becomes a focused
14-line `error1`, not lines 50–57 of a 60-line wall. Chunk ids became **stable and
role-tagged** (`chunk{n}`/`error{n}`, ADR 0017) so the gold cases survive
re-chunking; RCA needed no change.

Then the **recorded online run**, again on SAP HANA Cloud in-database
`VECTOR_EMBEDDING`. A new devex gold case (the `checkout-service` on-call lookup)
reads coverage **0.950**, quality **0.889** offline — `difflib` leaves
`checkout-svc` unresolved, so the answer is a faithful *partial* — and the
de-diluted `github_actions` synonymy case stays the lexical **0.833** offline
miss. The one online one-shot closed **both**: devex gold **1.000 / 1.000**
(the embedding resolved `checkout-svc`) and `github_actions` gold **1.000 /
1.000** (the answer now surfaces the actual 404 line). Faithfulness 1.0
throughout; both points in `eval/history.jsonl`.

Two honesties, again. The close is **earned, not a re-saturation** (ADR 0015,
verified online): distinct services did **not** over-merge (cross-service stem
cosines 0.49–0.58, all under 0.85); only the catalog↔on-call stem matches fired.
And a real-model finding: HANA's embeddings are **asymmetric** (`QUERY` vs
`DOCUMENT` mode), so even identical text scores ~0.889, not 1.0 — above threshold,
the close holds with margin, but it is a reminder that the cloud number is a
measurement, not a constant. One residual is recorded plainly: the embedding
regime is *additive*, so it cannot remove `difflib`'s existing generic-suffix
over-merge — closing that needs the same stem-gating applied to the `difflib` pass
(a deterministic change) or multi-field ER, the named next lever.

## The generality proof

Phase 3's milestone was not "a second vertical works" but "the **same,
unchanged** core serves both." That claim was made checkable (ADR 0008): the
core modules were frozen by name at the phase start, and the close audit
recorded `git diff phase-2..phase-3` over the frozen list — **empty**. The
only sanctioned core deltas were two vertical-neutral generalizations (one
new verifier grammar; battery parameterization of the harness), and the
business battery reproduced its numbers exactly through both.

The DevEx vertical exercised the engine on genuinely different material —
log spans and diff hunks as evidence, recurrence claims spanning sources,
service-name abbreviations as the ER challenge — through the same ingestion
door, the same graph, the same resolution layer, the same retrieval, and the
same metric definitions. In Phase 4 the symmetry was completed: the business
answer layer moved beside `tessera/devex/` (spec 0037) and each vertical now
owns its claim grammars, carried to the shared verifier by its eval battery
(ADR 0011) — `eval/metrics.py` contains zero vertical vocabulary, and a test
fails if that ever regresses.

## The conversational surface

`uv run tessera-chat` is the Joule-style door over both verticals:

- every answer opens with its **route and reason** (routing is part of the
  answer's story);
- claims are numbered, and `:show N` walks one back to its records — full
  text, source, locator, snapshot date, and the resolution/mention
  assertions that connected the evidence, each with its reason and
  confidence;
- the **trust signal is live**: every answer is re-verified on the spot by
  the same verifier the eval uses, and `:trust` shows the recorded battery
  numbers;
- with a configured provider (SAP Generative AI Hub, or an Anthropic key for
  a laptop demo — spec 0039), an LLM **narrates** the verified claims below
  them, under a visible label, behind a deterministic guard that rejects any
  narration introducing numbers or ids the claims don't contain (ADR 0013).
  Unset, everything is deterministic — the default.

## The platform posture

Tessera is **designed to run on SAP's AI stack and runs fully without it**
(ADR 0012, [DEPLOYMENT.md](DEPLOYMENT.md)): GenAI Hub on AI Core is the
documented model path (adapter implemented, contract-tested against fakes;
provisioning is a written runbook, deliberately not executed); HANA Cloud is
the documented graph/vector target (deliberately not built ahead of a
measured need); the local mode — pure stdlib, zero runtime dependencies, no
keys — is what CI verifies and what a stranger clones.

## Honest limitations

Named with the same prominence as the results:

- **The corpus is mostly synthetic, and bounded.** Schema-faithful (SALT's real
  ERP schema; realistic CI/tracker shapes) with planted, *measured* difficulty,
  now joined by a **real** GitHub Actions connector — but still hundreds of
  records, not millions. Scale behaviour is no longer fully untested: the engine
  is faithful and ER-precise over 180 entities (`tests/test_scale.py`), and the
  transitive over-merge risk is now a *measured* fact at volume — but BM25
  latency and graph performance at millions of records remain genuinely
  out of reach with a synthetic corpus.
- **Faithfulness is structural, not semantic.** The verifier re-derives
  quantities, containment, and cross-source fragments; it cannot judge a
  subtly misleading-but-verbatim juxtaposition — now demonstrated by a committed
  specimen (a "recurring failure" claim built on a generic shared trailer passes
  the structural check). An LLM-judged faithfulness layer has a standing trigger
  (ADR 0005) and has still not been forced by any *measured* case.
- **Question understanding is rule-based.** Phrasings outside the routers'
  rules refuse rather than guess — honest, but a usability ceiling. The router
  was widened this milestone (synonyms, word-boundary matching, currency-set
  validation) and the batteries now *do* sample free-form phrasing, but
  intent-only words (`rank`, `lead`, `best`) stay the named ADR 0006 ceiling;
  its measured-miss trigger has not fired (a correct refusal is the fallback).
- **ER recall now uses embeddings; the over-merge residual stands.** Milestone 7
  added an embedding-assisted resolution regime (stem-gated, additive, ADR 0016)
  that closed the undeclared `checkout-svc` recall miss online (devex gold
  0.950 → 1.000) without over-merging distinct services — measured both ways on a
  labeled pair-set (`tests/test_er_metrics.py`). But the regime is *additive*, so
  it cannot remove `difflib`'s **existing** generic-suffix over-merge (distinct
  firms sharing `… Logistik GmbH` still cross 0.85, `tests/test_scale.py`):
  closing that needs the stem-gating applied to the `difflib` pass itself, or
  multi-field matching (name + address + keys) — the named, recorded next lever.
- **Semantic embeddings ran on SAP for retrieval *and* ER, but stay link-only and
  cloud-measured.** Milestones 6–7 closed the synonymy miss, the `checkout-svc` ER
  miss, and the long-log dilution on HANA Cloud in-database embeddings — but
  embeddings only ever decide *what is surfaced or linked*, never *what is claimed*
  (a subprocess leak-guard pins the verifier imports no embedding module, ER
  module included). The closes are **timestamped online measurements** — CI stays
  on the deterministic path, where `github_actions` gold reads 0.833 and devex gold
  0.950 — and HANA's asymmetric (`QUERY`/`DOCUMENT`) embeddings mean even identical
  text scores ~0.889, so the cloud number is a measurement, not a constant.
- **The narration guard is conservative, not complete.** It catches
  fabricated quantities and identifiers, not every semantic drift — which is
  why narration is presentation below canonical claims, never evidence.
- **Conversation is stateless.** Each question is answered from evidence
  alone; follow-ups ("and what about its renewal terms?") need the entity
  repeated.

## Deliberately deferred (future work, not gaps missed)

More real connectors (the first — GitHub Actions — now exists and proves the
synthetic corpora were drop-in shaped; a Jira/PR-and-issue export is the obvious
next) · **curing the generic-suffix over-merge** (Milestone 7 added embedding ER
for *recall* on SAP HANA, ADR 0016, and de-diluted long logs, ADR 0017; the
additive regime cannot remove `difflib`'s existing over-merge — stem-gating the
`difflib` pass, or multi-field ER on name + address + keys, is the recorded next
step) · LLM-judged faithfulness alongside the deterministic floor · an agentic /
MCP-exposed mode (grounded actions, not just answers — the 2026-shaped extension
of the same trust substrate) · persistence, multi-tenancy, access governance.

## What was learned

1. **A metric you can fail is worth more than a metric that flatters.** The
   verifier caught a real bug the week it was born; the floor has been
   un-gameable since because weakening it is culturally and procedurally
   (CLAUDE.md, CI) a build failure.
2. **Name your misses before fixing them.** Both coverage gaps were
   documented, tested, *known* misses before the eval measured them — so a
   number moving meant something, and the fix could be minimal instead of
   defensive.
3. **Freezing the core made generality a fact, not a feeling.** An empty
   diff is a stronger sentence than any architecture diagram.
4. **Determinism is a feature with compounding returns.** Reproducible
   retrieval, resolution, and metrics made every refactor this phase
   verifiable by "the numbers must not move" — refactoring with a safety
   net most RAG systems don't have.
5. **The right place for an LLM is on top of, not inside, the trust path** —
   at least until a measured miss says otherwise. Every trigger that could
   bring one in is written down with its firing condition.

## Reproduce everything

```bash
git clone https://github.com/robert-vetter/tessera && cd tessera
uv sync                         # Python 3.12, zero runtime deps
uv run tessera-eval             # three batteries; non-zero exit if the floor breaks
uv run tessera-chat             # the Joule-style session (deterministic by default)
uv run tessera "Which customer has the greatest total order value in EUR?"
uv run tessera-devex "Why did run R-1042 fail, and how was it fixed?"
bash scripts/gate.sh            # format · lint · strict types · tests · eval floor
```

The development history itself is part of the result: every unit of work has
a spec written before code (`specs/`), every hard-to-reverse choice an ADR
with its alternatives (`docs/adr/`), every session a journal entry
(`docs/STATUS.md`), and every recorded metric an append-only history line —
the repository can answer "why is it this way?" without the author in the
room.
