# Community posts — drafts (publish under the maintainer's identity, his timing)

*Numbers verified 2026-07-03 against `uv run tessera-benchmark`; re-verify
before publishing. Sequence: Show HN first (its thread is the anchor link),
these within 24–48h, each adapted to the channel — never post identical
text twice.*

---

## r/LLMDevs

**Title:** I benchmarked an evidence-gated agent against its own ungated
retrieval — same corpus, same verifier. The "faithfulness" numbers
surprised me.

**Body:**

The setup: I've built an open-source evidence layer for agents (claim-level
provenance, refusals when evidence is missing, actions gated on verified
claims). For launch I wanted a benchmark that couldn't be accused of an
LLM judge doing the scoring — so it's fully deterministic: the baseline is
the engine's *own* BM25 retrieval, recited verbatim, always answering; the
gated side adds routing, entity resolution, recomputed aggregates,
refusals, and a deterministic verifier. Same corpora, same questions, same
verifier for both.

The result worth discussing here: **the ungated baseline scores 1.000
per-claim faithfulness** — verbatim recitation trivially passes a
containment check — **while producing trustworthy outcomes on 0–25% of
cases**. It answers questions it should refuse (ambiguous entities,
conflicting evidence, questions about runs that never failed) and can
never state what the evidence adds up to (sums, recurrences, fix chains).

My takeaway: per-claim faithfulness scores — the thing most RAG evals
report — are close to meaningless without also measuring *disposition*
(did it answer when it shouldn't?) and *composition* (did it assert what
the question needed, with the evidence cited?). A recitation bot maxes the
first metric and fails the task.

Before anyone points it out: part of the quality gap is definitional
(some expected answers are phrased by the gated engine), and the benchmark
computes exactly how much per battery and prints it — the interesting
part is what's left after that discount. Method, per-case tables, and the
"how to attack this" section:
https://github.com/robert-vetter/tessera/blob/main/docs/BENCHMARK.md —
reproducible offline from a clone (`uv run tessera-benchmark`), no
accounts, no API keys; CI regenerates the published tables so they can't
drift.

Honest limits: corpora are mine (two synthetic verticals + the repo's real
CI history), n=110 cases, and the extractive baseline's faithfulness is a
best case by construction — a paraphrasing agent only does worse *on that
axis*.

Repo: https://github.com/robert-vetter/tessera — I'd genuinely value
methodology attacks. HN discussion: [link after Show HN is live].

---

## X / Twitter thread

1/ Last year an agent deleted a prod database during a code freeze, then
misreported the rollback. The industry's fix: approval gates for
*actions*. But agents' *statements* need gates too. I spent a month
building both, open source. 🧵

2/ Tessera is an evidence gate: every claim in an answer traces to
specific source records (row, log lines, doc span), re-checked by a
deterministic verifier. Not "the model says it's grounded" — recomputed,
in code. No evidence → refusal, with the reason.

3/ Actions: drafted only from verifier-passing claims → the exact wire
request previewed (the literal GitHub POST body) → approval → execution →
receipt. Over MCP, so your agent can use it today. The public actuator is
simulated; the one real send it ever did is on the record, receipt
committed.

4/ "Trust" is a number in CI, not a vibe: faithfulness has a hard 1.0
floor — an unsupported claim fails the build. It has genuinely failed
before. A floor that can't fail is decoration.

5/ For launch I benchmarked the gated engine against its own ungated
retrieval (BM25, recite, always answer). Same corpus, same verifier. The
ungated bot scores a *perfect* 1.000 per-claim faithfulness — and
trustworthy outcomes on 0–25% of cases. Recitation maxes the metric,
fails the task.

6/ That's the quiet scandal in RAG evals: response-vs-context faithfulness
rewards answering everything. The expensive behaviors — refusing on
ambiguity, on conflicts, on missing evidence; recomputing what evidence
adds up to — are what the common metrics don't see.

7/ It runs on your data in ~20s after clone: `tessera connect github
<owner>/<repo>` → grounded root-cause on your real CI failures, offline,
nothing leaves your machine. Plus a per-repo `smoke` battery that says
whether the contract holds on YOUR repo — on one repo it honestly failed.
That's the feature.

8/ Live demo (read-only): https://robert-vetter-tessera.hf.space
Benchmark + how to attack it: docs/BENCHMARK.md in the repo
Repo (MIT): https://github.com/robert-vetter/tessera
Building toward design-partner pilots — DMs open.

---

## Channel notes

- **HN:** stay in-thread 3–4h; the known-attack answers live in
  `show-hn.md`. Concede real limitations fast; never argue tone.
- **Reddit:** no live-demo link in the body (self-promo smell); repo +
  benchmark link only, demo link in a comment if asked. Flair: Discussion
  or Resource, not Self-Promotion, and the post genuinely is about the
  metric finding.
- **X:** attach a 20–30s screen capture on tweet 2 if available (DEMO.md
  §2 beats 1–2, cut down). Thread posted as original content, not a link
  dump; the repo link waits until tweet 8.
- **After the first wave:** MLOps.community Slack (#llmops), MCP Discord
  (#showcase), SAP Community blog (the S4 angle — separate piece, SAP
  vocabulary, not this thread).
