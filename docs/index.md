# Tessera

**The agent can only say what it can prove — and only do what you approve.**
An open, deterministic evidence layer for AI agents: claim-level provenance,
principled refusals, approval-gated actions with receipts — and faithfulness
as a number in CI, not a vibe.

**Try it live:** <https://robert-vetter-tessera.hf.space>

Tessera ingests heterogeneous enterprise data (tables, spreadsheets, documents,
logs, tickets), resolves the entities scattered across those sources into a
single knowledge graph, and answers questions through a conversational interface
in which **every individual claim is grounded in a traceable path back to the
source records that support it**. A built-in benchmark harness turns "do you
trust this AI?" from a feeling into a measured **faithfulness** score.

## Start here

- **[Benchmark — The Faithfulness Floor](BENCHMARK.md)** — evidence-gated vs.
  the same engine ungated; CI-pinned; how to attack it.
- **[Demo & Hosting](DEMO.md)** — the live surface, the 3-minute script.
- **[Pilot in a Day](PILOT.md)** — grounded answers on your own repo or CSVs
  in under 30 minutes.
- **[Project Brief](PROJECT_BRIEF.md)** — motivation, the gap, vision,
  principles, scope, and what "excellent" means.
- **[Capabilities](CAPABILITIES.md)** — the four pillars at feature level and
  what each must guarantee.
- **[Technical Write-up](WRITEUP.md)** — the whole story in one sitting:
  approach, the recorded results trail, limitations, lessons.
- **[Roadmap](ROADMAP.md)** — the phased build plan across ~3–4 months.
- **[SAP Alignment](SAP_ALIGNMENT.md)** — how the work maps onto SAP's teams and
  platform.
- **[Deployment (SAP)](DEPLOYMENT.md)** — the AI Core / GenAI Hub / HANA Cloud
  path, and why local mode is the default.

## Build and operate

- **[Engineering Handbook](ENGINEERING.md)** — workflow, tooling, quality gates,
  and anti-drift discipline.
- **[Setup](SETUP.md)** — from docs to a running, gated project.
- **[Status](STATUS.md)** — the living session journal.
- **[Architecture Decision Records](adr/README.md)** — why it was built this way.

---

*This site is generated from the `docs/` folder. The source lives on
[GitHub](https://github.com/robert-vetter/tessera).*
