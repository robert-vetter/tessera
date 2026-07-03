# Submission copy (PulseMCP / mcp.so / any form-based directory)

Verified against the code 2026-07-03 (seven tools; `agent` extra; simulated
actuator). Keep the honesty rules from `RUNBOOK.md` when adapting.

**Name:** Tessera

**Tagline (≤80 chars):**
The evidence layer for MCP agents — provenance, refusals, receipts.

**Short description (≤160 chars):**
Grounded answers with claim-level provenance; refuses without evidence;
actions drafted from verified claims, executed behind approval with
receipts.

**Long description:**

Tessera is an evidence gate for AI agents. Where MCP gateways decide
*whether* an agent may call a tool, Tessera proves *why* an answer or
action is justified — and refuses when it can't.

- **ground** — ask a question, get claims that each carry a provenance
  trail to specific source records (rows, log lines, document spans),
  live-checked by a deterministic verifier. No supporting evidence → an
  explicit refusal, never a guess. **list_domains** shows what can be
  asked; **assertions** explains why two records were linked (explainable,
  reversible entity resolution with confidences).
- **list_actions / draft_action → preview_payload → execute_action** — an
  action is drafted only when every field traces to a verifier-passing
  claim; the exact wire request is previewed before anything happens;
  execution is behind approval and returns an auditable receipt. This
  server ships the **simulated** actuator only (`sent: false`, holds no
  credential); real sends are a local, credentialed opt-in.

It works on your own data today: `tessera connect github <owner>/<repo>`
(root-cause analysis over your real CI failures, offline after a bounded
snapshot) and `tessera ingest <dir>` (CSV + Markdown with cross-source
entity resolution and ambiguity refusal). Faithfulness is measured, not
asserted: a CI-gated 1.0 floor plus a reproducible gated-vs-ungated
benchmark (`docs/BENCHMARK.md`). Deterministic, stdlib-first, MIT — no LLM
in the trust path.

**Categories/tags:** knowledge, provenance, trust, evaluation, devtools,
entity-resolution, audit

**Install / run:**

```bash
uv sync --extra agent
uv run tessera-mcp        # stdio
```

**Links:** repo <https://github.com/robert-vetter/tessera> · live demo
<https://robert-vetter-tessera.hf.space> · benchmark
[`docs/BENCHMARK.md`](../../docs/BENCHMARK.md) · pilot runbook
[`docs/PILOT.md`](../../docs/PILOT.md)
