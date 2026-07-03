# 0122. "The Faithfulness Floor" — the benchmark artifact

- **Phase / milestone:** Milestone 19 Unit 1 (ROADMAP2 M19.2; MARKET.md §5/§6
  "benchmark/architecture post" table stakes; the Z Fellows one-axis-outlier
  proof). M19 runs autonomously per CLAUDE.md; the kickoff fixed the unit
  breakdown (0122–0125), so decisions are recorded here, not asked.
- **Issue:** —
- **Status:** approved (autonomous mode).

## Problem

Every trust number the project publishes today measures Tessera against its
own gold expectations. That earns the floor, but it doesn't *show a stranger
the gap* — what an agent without an evidence gate does on the same corpus,
same questions, judged by the same verifier. The launch (spec 0124) and the
registries (spec 0123) need a credibility substrate that a skeptical reader
can clone, run, and attack: a deterministic, no-LLM-judge, reproducible
comparison whose numbers can fail in CI.

**Recorded decisions:**

1. **The baseline is Tessera's own ungated retrieval, not an authored
   strawman.** The comparison answerer is `tessera.retrieval.answer`
   (BM25 top-5, verbatim snippets, refuses only on zero content-token
   overlap) — the exact retrieval layer Tessera itself uses, minus everything
   above it (routing, composition, recomputation, entity resolution at answer
   time, refusal on ambiguity/conflict/incomparability, verification). So the
   measured gap is attributable to precisely the layers being sold, and
   nobody can claim we wrote the baseline to lose. Name it **"ungated
   retrieval (retrieve-and-recite)"** everywhere.
2. **Same everything else.** Same corpora and graph/KB builders, same gold +
   synthetic cases, same scoring function (`tessera.eval.harness._score` —
   imported, not reimplemented, so benchmark semantics cannot drift from eval
   semantics), same verifier (`is_supported`) *including the vertical's own
   claim shapes* — the baseline is scored with every grammar the real system
   gets (generous to the baseline, by design).
3. **Offline pinned.** The benchmark forces the deterministic lexical path
   (no semantic index) for BOTH sides, so anyone can reproduce it
   byte-for-byte with no accounts. Tessera's side therefore equals the
   *offline* eval numbers — including its own named misses (devex 0.950
   coverage / 0.889 quality; github_actions 0.833 / 0.800). The report shows
   them; a benchmark where our side is imperfect is the credible kind. The
   online-HANA close of the gha synonymy case stays a documented pointer,
   not part of the artifact.
4. **One derived headline metric, defined transparently: the
   trustworthy-outcome rate.** Per case: an answer-kind case is trustworthy
   iff the answer is grounded, every emitted claim passes the verifier, all
   expected facts appear, and all expected support is cited; a refuse-kind
   case is trustworthy iff the system refuses. Computed by running the same
   `_score` on single-case lists (so each component keeps exact eval
   semantics). Faithfulness/coverage/quality are also reported per side,
   unchanged.
5. **Recitation's trivial faithfulness is reported, not hidden.** The
   baseline's per-claim faithfulness will be ≈1.0 by construction (verbatim
   snippets pass containment). The report says so prominently: a system that
   only recites is trivially "faithful" and still fails the task — it answers
   questions it should refuse and cannot state what the evidence adds up to.
   The floor is cheap if you never assert anything; Tessera holds it *while*
   computing sourced aggregates, resolving entities, and walking multi-hop
   chains. That asymmetry **is** the finding.
6. **The published number can fail.** `docs/BENCHMARK.md` embeds tables
   between generation markers; a test regenerates them from a fresh run and
   fails on any byte difference — the published artifact cannot silently
   drift from the measured truth (Milestone 5's lesson, applied to a doc).
   A second test asserts the headline direction (Tessera's trustworthy rate
   strictly above the baseline's on every battery, gold and synthetic); if a
   future change makes the claim false, the build says so.
7. **Zero engine/eval changes.** New files + one `pyproject.toml`
   entry-point line (`tessera-benchmark`) only — the M18 precedent that
   keeps the ADR 0008 frozen-core audit clean. The gate itself is unchanged;
   the new tests ride the existing pytest step.

## Acceptance criteria

- [ ] `uv run tessera-benchmark` prints, per battery (business, devex,
      github_actions) × (gold, synthetic) × (Tessera, ungated retrieval):
      faithfulness, coverage, quality, trustworthy-outcome rate — plus case
      counts and the mode line (offline/deterministic, k=5).
- [ ] `uv run tessera-benchmark --markdown` emits the canonical tables;
      `docs/BENCHMARK.md` embeds them between markers; a test pins doc ==
      fresh output.
- [ ] `uv run tessera-benchmark --cases` lists every case id with both
      sides' per-case outcome and which check(s) failed (F/C/Q).
- [ ] Tessera's side of the benchmark reproduces the recorded offline eval
      numbers exactly (asserted in a test against `run_eval()` output).
- [ ] A test asserts the headline direction per battery and case set.
- [ ] `docs/BENCHMARK.md` states: method, both answerers precisely, the
      trustworthy-outcome definition, the recitation caveat (decision 5),
      Tessera's own misses, how to reproduce (two commands), how it can
      fail / what would falsify it, and limitations (extractive proxy is a
      *lower bound* on the gap to a real paraphrasing agent; corpora are
      ours except the real gha snapshot; n is small and stated).
- [ ] mkdocs nav + README link the report. Gate green; six eval lines
      byte-identical.

## Scope

**In:** `src/tessera/eval/benchmark.py`, `tests/test_benchmark.py`,
`docs/BENCHMARK.md`, one pyproject entry-point line, nav/README links.
**Out:** any change to `eval/harness.py`, `eval/metrics.py`, batteries,
gold sets, engine, gate; any LLM anywhere; the blog/post version (spec 0124
links the report); online/semantic mode.

## Eval impact

None by construction — the benchmark *consumes* the eval. The six recorded
lines must be byte-identical after this unit; the frozen-core audit stays
empty. (The benchmark adds new, separately-published numbers; they can fail
without touching the floor.)

## Risks / open questions

- **Strawman accusations** are the artifact's main attack surface → decisions
  1, 2, 5 (baseline is our own retrieval, scored generously, its trivial
  faithfulness reported). The report carries a "how to attack this" section
  inviting exactly that reading.
- **Tie or inversion risk:** on plain-lookup cases the two sides are
  identical by construction; the gap comes from compose/RCA/refusal cases.
  If a battery shows no strict gap, the test fails and the finding is
  recorded honestly rather than massaged (that would itself be a real
  result about the corpus mix).
- No ADR: the benchmark defines no new trust semantics — it composes the
  ADR 0005 verifier and ADR 0009 batteries. The trustworthy-outcome
  definition lives in the report + this spec and is recomputed from
  primitives, not stored.
