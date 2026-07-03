# 0127. SAP track plan — the post-M19 build surface

- **Phase / milestone:** ROADMAP2 "SAP track (parallel)" — the remaining
  Act 2 build surface after the M19 build share. M19's public acts
  (registries, launch posts, outreach, tag) stay the maintainer's;
  "keep building" means the S-track. Autonomous per CLAUDE.md; decisions
  recorded here.
- **Issue:** —
- **Status:** approved (autonomous mode).

## Problem

Act 2's success criteria (ROADMAP2, ≈2026-08-02) include the SAP track:
S1 SALT real-data evaluation, S2 HANA Knowledge Graph persistence, S3
BTP/AI Core serving, S4 the application kit. Ranked by
credibility-per-effort, gated differently by access/spend. This plan
fixes what this stretch builds, on measured facts.

**Recorded decisions:**

1. **Scope: S4 + S2 now; S1/S3 recorded as blocked, not attempted.**
   - **S1 (SALT)** is access-gated: the maintainer has not yet requested
     gated HF access (his account, one click — standing item since M17).
     The schema-synthetic swap-in has been designed-for since Phase 1;
     nothing buildable until access exists.
   - **S3 (BTP/AI Core serving)** is a spend/account decision —
     deliberately his (ADR 0012 posture unchanged).
2. **S2 shape is fixed by today's measurement.** Probed 2026-07-03 with
   the existing `.env` credentials (sanctioned: the ROADMAP2 maintainer
   checklist itself asks for the instance-health check; no new account,
   no spend, nothing published): the M6/M7 HANA Cloud instance is
   **ALIVE** (connects, cloud version 2026.14.7) but the **Knowledge
   Graph triple store is NOT enabled** — `SYS.SPARQL_EXECUTE` exists and
   answers `No active TripleStore found in landscape`. Enablement is an
   instance-configuration checkbox (HANA Cloud Central → instance →
   Advanced Settings → **Triple Store**) available only to the account
   owner. Therefore S2 ships **the full seam now** — RDF mapping, store
   protocol, injection-safe serializer, HANA adapter over
   `SPARQL_EXECUTE(<sparql>, <headers>, ?, ?)` (signature verified
   against SAP's tutorial and empirically against the live instance),
   fake-backed contract tests, runbook, staged one-shot — and the online
   "ran on SAP Knowledge Graph" measurement pends that one toggle
   (exactly the M17 Pages-toggle pattern).
3. **Persistence is a mirror, never a source of truth.** The
   deterministic in-process graph remains canonical; HANA KG persistence
   is an export for SAP-native interop and SPARQL access. **No answer
   path reads from HANA**; the trust path, the verifier, the eval, and
   the frozen core are untouched. This is the load-bearing boundary and
   carries an ADR (0030) with the RDF-mapping decisions (S2's spec).
4. **S4 lives in `launch/sap/`** (application material goes out under
   the maintainer's identity → the `launch/` publish rule applies):
   the Sapphire-2026 vocabulary mapping, cover-letter drafts (EN + DE)
   for **both** the iXp and working-student tracks, the target-team
   list, and the artifact links to lead with. `docs/SAP_ALIGNMENT.md`
   gets a currency check; if stale against the verified 2026 landscape
   (MARKET.md §7), it gains a dated addendum, not a rewrite.
5. **Discipline unchanged:** one spec per unit before code, branch →
   gate → PR → CI-green → squash-merge; S2 is trust-adjacent (a
   serializer over evidence text; a new cloud surface) → pre-merge
   adversarial review; eval lines stay byte-identical; CI stays
   key-free.

## Unit breakdown

1. **This plan** (spec 0127) — its own small PR (M17/M18 precedent).
2. **S4 — the application kit** (spec 0128): `launch/sap/APPLICATION.md`
   (+ SAP_ALIGNMENT addendum if needed).
3. **S2 — HANA KG persistence** (spec 0129, ADR 0030):
   `tessera/platform/kg.py`, tests, `scripts/persist_knowledge_graph.py`
   (staged one-shot), DEPLOYMENT.md runbook section.

## Acceptance criteria

- [ ] Decisions above recorded before any unit code; specs 0128/0129
      land before their code, per discipline.
- [ ] Gate green throughout; all six eval lines byte-identical; frozen
      core untouched.

## Scope

**In:** the three units. **Out:** S1/S3 (blocked/spend — recorded);
enabling the triple store (maintainer's toggle); any answer-path or
engine change; any submission of application material.

## Eval impact

None — platform/docs additions only.

## Risks / open questions

- The triple-store toggle may restart the instance — noted in the
  runbook so the maintainer times it away from demos.
- `.env`'s HANA user is **DBADMIN**, not the least-privilege
  `TESSERA_APP` of `.env.example` — runbook gets a least-privilege note
  for the KG schema (no blocker for the staged one-shot).
- The KG engine is young (GA QRC1 2025); if `SPARQL_EXECUTE` behaves
  differently than documented once the toggle is on, the one-shot
  records what actually happened (honesty rules over expectations).
