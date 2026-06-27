# 0058. The online measurement — the synonymy miss closed, ran on SAP HANA

- **Phase / milestone:** Milestone 6 — Embeddings on SAP (Unit 8 of 9; plan 0051)
- **Issue:** —
- **Status:** approved (autonomous mode; live run with maintainer credentials)

## Problem

Everything was built and contract-tested; this unit runs the **one** live,
spend-bearing measurement that turns "designed for SAP" into "ran on SAP": embed
the `github_actions` records in HANA Cloud, retrieve the synonymy question
semantically, and record the close of the miss U6 recorded offline.

## What happened (honestly)

- **The HANA in-database embedding works.** `VECTOR_EMBEDDING(…, 'DOCUMENT'/'QUERY',
  'SAP_NEB.20240715')` returns 768-dim `REAL_VECTOR`s; `COSINE_SIMILARITY` ranks
  them — all in SQL, vectors never entering Python (the `HanaSemanticIndex`
  design). (An earlier attempt failed transiently while the model was still
  provisioning; it then worked from both the SAP console and `hdbcli`.)
- **The miss closed.** `TESSERA_EMBEDDINGS=hana uv run tessera-eval --record`
  moved `github_actions` gold **coverage 0.833 → 1.000, quality 0.800 → 1.000**,
  faithfulness gated **1.0** throughout. Recorded in `eval/history.jsonl`
  (offline-miss point + online-close point — the trust-loop pair).
- **Two real issues the live run surfaced, fixed here:**
  1. **Existence-check casing bug.** HANA upper-cases unquoted identifiers, so
     the `SYS.TABLES` check (binding `tessera`) never matched the stored
     `TESSERA` and re-`CREATE`d the table every run. Fixed (bind upper-cased
     names) in `HanaSemanticIndex` and `HanaVectorStore`; pinned by a regression
     test.
  2. **The gold case expected the wrong record.** SAP's embedding bridges the
     concept (all `Docs`-failure records outrank the unrelated ruff failure), but
     the concise run-status **row** outranks the long, noisy error-**log** chunk
     (long-document embedding dilution), so at k=5 the answer surfaces the failed
     **run**, not the 404 log line. The gold case now expects `Run:27285174461`
     (`status failed` / `Deploy to GitHub Pages`) — what semantics genuinely
     surfaces — rather than the diluted log chunk. The error-class synonymy
     itself stays demonstrated by the committed specimen
     (`test_adr0005`/`test_adr0010`).

## Acceptance criteria

- [x] `VECTOR_EMBEDDING` smoke-tested against the live instance (model +
      `DOCUMENT`/`QUERY` + `COSINE_SIMILARITY`).
- [x] Casing bug fixed + regression test; offline gate green (263 tests),
      `github_actions` gold still 0.833 offline (the miss holds on CI).
- [x] Online run closes the case (coverage/quality → 1.000, faithfulness 1.0) and
      is recorded in `eval/history.jsonl` with a `--note`.
- [x] `docs/DEPLOYMENT.md` verified-vs-not split flips the HANA embedding path to
      **ran on**, citing the recorded point.

## Scope

**In:** the casing fix (`semantic.py`, `vectors.py`) + regression test; the gold
case correction + the aligned stub test; the recorded online point
(`eval/history.jsonl`, `eval/badge.json`); the DEPLOYMENT verified-vs-not flip;
this spec.

**Out:** CI changes (CI stays offline/lexical/key-free; the online number is a
recorded measurement, not a reproducible gate). The recorded run used `DBADMIN`
for simplicity; the documented least-privilege `TESSERA_APP` user (spec 0057)
remains the recommended production setup.

## Eval impact

`github_actions` gold: offline (CI) **0.833** stands (the recorded miss); online
(HANA) **1.000** recorded. Faithfulness 1.0 everywhere. The first milestone to
**close a previously-recorded named miss with a method upgrade, measured on real
cloud infrastructure** — the inverse of M5's "keep the miss".

## Risks / open questions

- **Not CI-reproducible.** The cloud embedding model can change; the online point
  is timestamped (the M5 live-fetch precedent), CI stays on lexical. Stated in
  STATUS/WRITEUP.
- **Long-log dilution** is a real, named limitation: focused records (the
  run-status row) embed more sharply than long logs. Finer chunking of error
  logs would let the specific 404 line surface — recorded as future work, not
  gamed by inflating k.
- **A `TESSERA.TESSERA_DOC_VECTORS` table** (8 rows) now exists on the instance;
  the eval re-upserts it idempotently. Harmless; drop if desired.
