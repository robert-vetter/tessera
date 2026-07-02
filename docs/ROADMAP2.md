# Roadmap — Act 2: From Measured Prototype to Product (July 2026)

Act 1 (Phases 0–4 + Milestones 5–14, [ROADMAP.md](ROADMAP.md), [STATUS.md](STATUS.md))
built and measured the trust substrate: one ingestion door, an explainable
knowledge graph with reversible multi-field entity resolution, grounded answers
with claim-level provenance, a CI-gated faithfulness floor, and an MCP surface
carrying that contract across four measured boundaries (answer → action draft →
payload preview → execution) — deterministic, offline, zero-account
reproducible. The [2026-07-02 audit](AUDIT_2026-07-02.md) confirms it all runs
as documented.

**What Act 1 did not produce:** a product. No UI, no way to point it at your
own data, no users, and documentation drift from the autonomous run. Act 2
fixes that — **without changing what makes the project rare** (the determinism,
the provenance contract, the measured floor).

Act 2 serves two concrete audiences on one build (evidence:
[MARKET.md](MARKET.md)):

- **Z Fellows** (applicant in final selection: a one-month build period with
  **weekly ship-updates**, closing in a **check-in presentation**; the cohort
  week itself comes later). The maintainer has publicly committed, in writing,
  to shipping within the month: an open-source tool where every answer traces
  to its source, **a live demo anyone can try**, documented, with a push for
  **first real external users and feedback**. M17 (hosted demo) and M19
  (launch + users) are that promise, scheduled.
- **SAP internship**: the same system, told in SAP's own 2026 vocabulary and
  run on SAP primitives (HANA KG, SALT, BTP).

---

## The thesis

The market gap is verified ([MARKET.md §1](MARKET.md)): grounding vendors have
no action layer, action/gateway vendors have no evidence layer, and both put an
LLM inside the trust path. Nobody credibly offers **per-claim provenance +
evidence-gated actions with receipts + a self-shipped deterministic
faithfulness benchmark + on-prem determinism**. Tessera already implements
that conjunction on demo data. Act 2's job is to make it *usable, visible, and
wanted*.

**Positioning (fixed, use everywhere):**

> **The agent can only say what it can prove — and only do what you approve.**
> Every claim carries provenance. Every action leaves a receipt. Faithfulness
> is a number in CI, not a vibe.

Rules: sell the *receipt*, not the philosophy; practitioner words (approval,
audit trail, receipts, blast radius) over academic ones; never say
"hallucination-free"; don't compete as an "MCP gateway" (permission layer,
crowded) — Tessera is **the evidence layer**; LLMs may *present* (narration,
ADR 0013) but never *attest*. For SAP specifically: *SAP asserts trust at
platform level; Tessera measures it at claim level — and gates action on it.*

## The build (four milestones + a parallel SAP track)

Discipline unchanged (CLAUDE.md): every unit spec → branch → gate → PR →
CI-green → merge; ADRs for hard-to-reverse choices (UI stack, BYO-connector
boundary, benchmark definition); pre-merge adversarial review for trust-bearing
changes; `/wrap` every session — the audit showed what happens when that slips.
Standing cadence on top: a short **weekly ship-update to Z Fellows** — each
milestone close doubles as update material.

### Milestone 16 — Close & clean (≈2–3 days)

Make the existing thing impeccable before adding anything. Input:
[AUDIT_2026-07-02.md](AUDIT_2026-07-02.md).

1. **Drift repair** (audit D1–D7): backfill STATUS for the 0104–0106 sessions
   (from PRs #115–#117), fix CHANGELOG `[Unreleased]`, rewrite the WRITEUP
   idempotency limitation, fix the DEPLOYMENT embeddings contradiction, README
   count fix + link to this roadmap, reconcile the seven phantom spec numbers
   in `specs/README.md` (document, don't fabricate backdated specs), prune
   merged remote branches.
2. **Trust-path fixes** (audit B1–B5, each spec'd + tested; B2/B4 carry
   adversarial review): recorder never clobbers a receipt (B1); idempotency
   pre-check gains a label-independent fallback + ADR 0026 addendum naming the
   residual (B2); `token` excluded from repr (B3); fence-injection neutralized
   + marker-spoof residual documented (B4); `{pr}` segment allowlist (B5).
3. **Verifier honesty** (audit B6–B7): ADR 0005 addendum naming over-citation
   and cross-boundary containment; score claims on refuse-kind cases. Metric
   *definitions* only change transparently, never to look better.
4. **Milestone 15 close**: after unit 2, the maintainer runs the real one-shot
   (sandbox repo + PAT, runbook in [DEPLOYMENT.md](DEPLOYMENT.md)); commit the
   scrubbed receipt; WRITEUP/README/CHANGELOG; empty-diff audit; tag
   `milestone-15`. **The four-boundary story ends with: it actually acted,
   once, on the record.**

*Done when:* audit findings fixed or explicitly accepted in an ADR; tag
`milestone-15` exists; STATUS current; gate green.

### Milestone 17 — Demoable to humans (≈1 week)

The audit's verdict: strong for an SAP engineer, weak for everyone else. Fix
the *presentation*, not the trust model. The UI renders existing trust objects
(`GroundedResult`, `ActionProposal`, `RenderedPayload`, `ExecutionReceipt`) —
**no new answer path, no new claims**.

1. **Answer presentation**: optional narration (ADR 0013 adapters, Anthropic
   key) on the chat/demo surface so answers read as prose above the canonical
   claims — the verifier and eval stay untouched; label narrated text as such.
   Fix cosmetics: `:trust` float formatting, MCP `serverInfo` version, chunk
   rendering.
2. **Web UI** (new `ui` extra; stack choice is an ADR): one page — ask →
   claims with per-claim verifier chips → click-through provenance (records,
   locators, resolution trail with confidences) → trust panel (history) →
   the action flow: draft → payload preview → **approve** → receipt.
   Local-first; a read-only hosted mode flag.
3. **Hosted demo + assets**: deploy the read-only UI on synthetic data (small
   VM/PaaS, no keys); record the 2–3-minute video; one-pager (EN/DE). The
   video's arc is the Replit-incident counter-story: question → grounded
   answer → provenance walk → refusal → drafted action → dry-run → approval →
   receipt.
4. **The "agent through Tessera" demo**: a scripted session where a real LLM
   agent (Claude over MCP) answers **only** through Tessera's tools — the
   audience watches it cite, refuse, and get its action gated. This is the
   Z Fellows demo and the SAP demo in one.

*Done when:* a stranger can watch the video or click the hosted demo and
understand the product in under 3 minutes; the cohort presentation can run
live offline.

### Milestone 18 — Usable on your data (≈1 week)

The wedge from demo to product; the pilot vehicle for design partners. Reuses
the existing ingestion/connector patterns — engine untouched.

1. **`tessera connect github <owner/repo>`**: generalize the GitHub Actions
   connector (snapshot fetch → graph) to any repository (read-only PAT).
   Grounded RCA over *their* failures; optionally the gated create-issue flow
   on *their* repo. An honest eval note: expectations for foreign data are
   thin at first — say so; a per-repo smoke battery (runs parse, provenance
   resolves, refusals fire) is the floor.
2. **`tessera ingest <dir>`**: CSVs + Markdown/text with declared match-field
   config (what `sources/salt.py` + `documents.py` do, made generic).
   Cross-source questions on *their* data with the same provenance contract.
3. **Pilot runbook** ("pilot in a day"): the consultancy offer — *we
   instrument one agent use case with provenance + action receipts; you keep
   the audit artifact.* Quickstart such that a stranger reaches a grounded
   answer on their own repo in <30 minutes.

*Done when:* Tessera answers with full provenance on ≥2 external repositories
(at least one not ours) and on one foreign CSV+docs corpus; the BYO paths have
their own boundary tests.

### Milestone 19 — Launch & traction (≈1 week, overlaps M18)

Playbook and targets: [MARKET.md §5](MARKET.md). Everything public goes out
under the maintainer's identity — his call on timing.

1. **Be findable**: MCP registry, PulseMCP, mcp.so, awesome-mcp-servers PR.
2. **The benchmark artifact**: "The Faithfulness Floor" — same corpus, naive
   agent vs. evidence-gated Tessera; deterministic, reproducible, no LLM
   judge; published in-repo + as a post. (The credibility substrate; also the
   Z Fellows one-axis-outlier proof.)
3. **Launch**: Show HN ("open-source evidence gate for AI agents — claim
   provenance, approval-gated actions, execution receipts") + r/LLMDevs +
   X thread. After M17's hosted demo exists.
4. **Outreach wave**: 100–150 personalized DE/EN messages to the named DACH
   consultancy/partner list, 3–4 touches, offering the M18 pilot. Target: ≥5
   calls, **≥2 design-partner pilots** with a written 2-week success
   definition. Opportunistic: AI Tinkerers Berlin/Munich demo slot; DSAG
   Jahreskongress (Oct 6–8) and data2day CfPs.
5. **Z Fellows kit**: the check-in presentation — problem (Replit story) →
   live demo → what shipped in 30 days (velocity, receipts) → 3/6/12-month
   plan → asks (design-partner intros, enterprise-AI mentors). The same
   5-minute arc serves the later in-cohort presentation.

*Done when:* launched, benchmark published, outreach sent, ≥2 pilots agreed
(or the honest miss recorded), presentation rehearsed.

### SAP track (parallel, before/around the application)

Ranked by credibility-per-effort ([MARKET.md §7](MARKET.md)):

- **S1 — SALT real-data evaluation**: request gated HF access **now** (lead
  time); the schema-synthetic swap-in was designed for this since Phase 1.
  Run ER + grounding + eval on real SALT; engage SALT-KG (arXiv 2601.07638) —
  its "models can't leverage relational semantics" finding is Tessera's
  thesis, from SAP's own researchers.
- **S2 — HANA Knowledge Graph persistence**: persist the graph to HANA Cloud's
  GA KG engine (RDF/SPARQL) — "runs on SAP Knowledge Graph", beside the
  existing recorded `VECTOR_EMBEDDING` closes.
- **S3 — BTP/AI Core serving**: execute the written runbook (spend decision) —
  turns "designed for BTP" into "ran on BTP".
- **S4 — Application kit**: README/one-pager mapping to Sapphire-2026 language
  ("relevant, reliable, responsible"; Agent Hub "verification badges" ↔ a
  *measured* faithfulness score; receipts ↔ auditability), the DSAG 3% hook;
  apply to **both** iXp and working-student tracks; target BTP AI Core /
  GenAI Hub (Walldorf/Berlin), Joule Studio, Business AI research, Prior Labs
  as the long shot.

## Maintainer decisions & accounts checklist

Only these need the maintainer (everything else proceeds autonomously per
CLAUDE.md):

1. **Run the M15 one-shot** (after M16 unit 2): sandbox repo + fine-grained
   PAT + `TESSERA_EXEC_*` in `.env` (~15 min). Credentialed and irreversible —
   deliberately yours.
2. **HANA instance health**: verify the M6/M7 instance still exists (trial
   instances expire/auto-stop) *before* any live cloud demo; re-provision or
   demo offline otherwise.
3. **SALT access**: request via Hugging Face (personal account) — today;
   approval lead time is the risk.
4. **Anthropic API key** for narration + the M17 agent demo (small spend).
5. **Hosting** for the read-only demo (~€0–20/month) and optionally a domain.
6. **BTP trial/free tier** account for S2/S3.
7. **Z Fellows logistics**: confirm the check-in date (and, if accepted, the
   later cohort week / SF-NYC attendance) — the month plans backwards from
   the check-in.
8. **Launch consent**: Show HN / X / outreach go out under your name and
   timing.

## What Act 2 will NOT do

- No LLM in the trust path (narration presents; the verifier attests) — this
  *is* the differentiator.
- No MCP-gateway feature race (auth, rate limits, policy engines).
- No third connector before the two BYO paths work end-to-end.
- No multi-tenant SaaS, no auth/RBAC theater — pilots run on-prem/local, which
  the on-prem story makes a feature.
- No rename; no "hallucination-free" claims; no weakening or gaming the eval —
  a number that can't fail is decorative (Milestone 5's lesson).
- No paid ads, no spam; 150 *personalized* messages beat 1,500 generic ones.

## Success criteria (end of Act 2, ≈ 2026-08-02)

1. `milestone-15` tagged; the real receipt committed; audit findings closed or
   ADR-accepted; STATUS current at every wrap from here on.
2. Hosted demo + video live; the live demo runs offline end-to-end.
3. BYO works: grounded, provenance-complete answers on ≥2 external repos + 1
   foreign CSV/docs corpus, with boundary tests.
4. Launched (Show HN + registries) and the benchmark report published.
5. ≥150 outreach touches → ≥5 calls → **≥2 design-partner pilots** (or the
   miss honestly recorded with what was learned).
6. Z Fellows presentation delivered; SALT access requested and S1 started;
   S4 application kit ready.

## Risks

- **Solo bandwidth** — the plan over-fills 4 weeks by design; the cut order is
  fixed: M18.2 (ingest dir) → M19.2 (benchmark) → S2/S3 slip. M16, M17.2–3,
  M18.1, M19.3–5 are the spine and don't slip.
- **Launch flops** — design partners come from outreach, not HN; the wedge
  survives a quiet launch.
- **HANA/SALT access delays** — offline demo remains the default; synthetic-
  on-real-schema remains the honest fallback and is documented as such.
- **UI scope creep** — the UI renders existing trust objects only; any feature
  that would need a new answer path is out.
- **Check-in date unknown** — decision #7 above; until known, M16→M17 order is
  robust either way.
