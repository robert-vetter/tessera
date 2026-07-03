# 0128. S4 — the SAP application kit

- **Phase / milestone:** SAP track S4 (spec 0127 decision 4; ROADMAP2;
  vocabulary and targets verified in MARKET.md §7, 2026-07-02).
  Autonomous; **nothing is submitted** — application material goes out
  under the maintainer's identity (`launch/` publish rule).
- **Issue:** —
- **Status:** approved (autonomous mode).

## Problem

The SAP internship is Act 2's second audience, and the application
window favors the prepared: Germany runs iXp internships and
working-student contracts as **separate tracks** (apply to both), and
the strongest material maps the project onto SAP's **own 2026 words**
(Sapphire's "relevant, reliable, responsible"; Agent Hub "verification
badges"; the DSAG 3% statistic) rather than generic AI vocabulary.
Everything needed exists and is measured; this unit assembles it so
applying costs an evening, not a week.

**Recorded decisions:**

1. **`launch/sap/APPLICATION.md`** carries: the Sapphire-2026 mapping
   table (Tessera ↔ their vocabulary, with the one-line asymmetry
   pitch), the artifact links to lead with (live demo, benchmark,
   recorded agent session, the HANA closes), target teams
   (BTP AI Core / GenAI Hub Walldorf+Berlin, Joule Studio, Business AI
   research, Prior Labs as the long shot), CV bullets with measured
   numbers, and cover-letter drafts — **EN for iXp** and **DE for the
   working-student track** — with `{placeholders}` only for
   posting-specific facts.
2. **`docs/SAP_ALIGNMENT.md` gains a dated addendum, not a rewrite**
   (spec 0127 decision 4): the 2026 section is genuinely stale in one
   honest-to-fix way — it still *recommends* adding an agentic/MCP mode
   ("Tessera should therefore include…") that shipped months ago
   (ADR 0022–0025, the four measured boundaries, the recorded Claude
   session), and it predates Sapphire 2026 (Business AI Platform,
   SAP+Anthropic Claude-via-MCP, Agent Hub verification badges, Prior
   Labs). The addendum updates exactly that; the team-brief sections
   stay as written (they describe the briefs they quoted).
3. **Honesty rules extend to application copy:** every number carries
   its scope (offline vs the recorded online closes); "ran on SAP" is
   claimed only for what ran (HANA `VECTOR_EMBEDDING` — recorded;
   the KG engine is "one toggle away", S2); never "hallucination-free";
   the asymmetry line stays an argument, not a fact claim.

## Acceptance criteria

- [ ] `launch/sap/APPLICATION.md` with all decision-1 contents; links
      resolve; numbers match the recorded state.
- [ ] SAP_ALIGNMENT dated addendum (decision 2).
- [ ] Gate green; eval byte-identical; docs-only diff.

## Scope

**In:** the two files. **Out:** submitting anything; CV/profile editing
beyond suggested bullets; S1/S2/S3 content (S2 is spec 0129); rewriting
SAP_ALIGNMENT's team-brief sections.

## Eval impact

None — documentation.

## Risks / open questions

- Postings churn; the kit links the live jobs.sap.com search rather
  than pinning a single req ID, and the letters keep posting-specific
  facts in `{placeholders}` to fill at submission time.
