# 0066. The online HANA measurement: record both M7 closes (ran on SAP)

- **Phase / milestone:** Milestone 7 — Unit 7 (of spec 0060)
- **Issue:** —
- **Status:** approved (autonomous mode; the **online run** is the maintainer's
  one-shot — external service + spend, authorized at scope 2026-06-27)

## Problem

Units 2–6 built and recorded the two M7 wins as **offline misses**
(`eval/history.jsonl`): devex gold coverage 0.950 (the `checkout-svc` ER recall
miss) and github_actions gold coverage 0.833 (the de-diluted synonymy case, still
a lexical miss). Both close only on the semantic/HANA path. This unit prepares and
records the **online** measurement — "ran on SAP," the M6 precedent — so the
trust-loop pair (offline miss → online close) is complete.

## Acceptance criteria

- [ ] **`--recorded` flag.** `tessera-eval --recorded YYYY-MM-DD` stamps the
      one-shot online point with an explicit date (passed through to
      `history.record`); default stays today. Tested without touching the real
      history file.
- [ ] **Runbook.** `docs/DEPLOYMENT.md` gains the M7 one-shot: the **single**
      `TESSERA_EMBEDDINGS=hana uv run tessera-eval --record` run records **both**
      closes (devex ER + de-diluted synonymy), the separate `TESSERA_ER_VECTORS`
      table (auto-created), and the expected number movements; CI stays
      offline/lexical/key-free.
- [ ] **Wiring verified offline.** The HANA-native ER path (`propose_…_via_index`
      + `HanaSemanticIndex` over ER stems) and the de-diluted retrieval are proven
      offline against fakes/stubs (Units 4–6); the online run only flips the env.
- [ ] **The online run + recorded points (maintainer).** With `.env` filled and
      `uv sync --extra cloud`, the maintainer runs the one-shot once on HANA; the
      two closes (devex gold → 1.000/1.000, github_actions gold → 1.000/1.000,
      faithfulness 1.0) are appended to `eval/history.jsonl` as a **timestamped**
      point and committed. If the model does not move a number, that is reported
      plainly, not faked.

## Scope

**In:** the `--recorded` flag + its test, the DEPLOYMENT runbook M7 section, and
(maintainer-run) the recorded online history point. **Out:** the WRITEUP/README/
CHANGELOG/STATUS close (Unit 8); any new cloud dependency beyond M6's `hdbcli`
extra + NLP feature.

## Eval impact

- **Online, recorded:** devex gold coverage 0.950 → **1.000**, quality 0.889 →
  **1.000** (checkout-svc resolved by the embedding regime — its stem coincides,
  so the close is robust); github_actions gold coverage 0.833 → **1.000**, quality
  0.800 → **1.000** (the de-diluted `error1` chunk surfaces the 404 line).
- **CI / offline unchanged** — the deterministic path keeps both misses; the
  online numbers are timestamped, not CI-reproducible (the embedding model can
  change). Faithfulness 1.0 at every point.

## Risks / open questions

- **The run is the maintainer's** (their credentials, their spend). The repo ships
  the one-shot and the seam; the recorded numbers land when they run it. This is
  the single external-service hand-off of the milestone.
- **Robustness of the ER close.** `checkout-service` and `checkout-svc` reduce to
  the **identical** stem `checkout` after generic-stripping, so any reasonable
  embedding ranks them top — the ER close does not hinge on a subtle model
  judgment. The de-dilution close depends on the model surfacing the short,
  focused `error1` chunk for the synonymy query — well-posed, but model-dependent;
  measured, not assumed.
- **Cost/security.** One run embeds a few hundred short stems + a handful of KNN
  queries — small; confirm per-run cost before running; do not loop. `.env`
  gitignored; the least-privilege `TESSERA_APP` user is the recommended setup.
