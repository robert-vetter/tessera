# SAP Alignment — Tessera

This document connects the project to SAP's AI teams and platform. It exists so that anyone can see, in one glance, that this was built *for* SAP's problems — not a generic side project retrofitted with SAP keywords.

---

## The shared insight

Three SAP AI groups are working on three faces of one problem: **take heterogeneous enterprise data, unify it, reason over it, and make the result trustworthy.** Tessera is a single engine built so that one slice of it speaks directly to each team. The point is not "something near your area" — it is: the same core problem, independently arrived at, with a coherent, measured answer.

---

## Palo Alto — GenAI Central Engineering / Joule

**What the team does (publicly stated focus):** advance AI for business-user productivity; build the conversational interface of Joule with intelligent routing and reasoning; use knowledge substrates and knowledge graphs to minimize errors; provide standardized benchmarking and data augmentation to assess quality.

**What in Tessera maps to it:**
- **Pillar 3 (grounded conversational reasoning)** — question routing, multi-step reasoning, a Joule-style conversational surface.
- **Knowledge-graph grounding to minimize errors** — the entire provenance model exists to reduce exactly the errors this team is fighting.
- **Pillar 4 (quantified trust)** — standardized benchmarking and synthetic data augmentation to assess solution quality, which is named almost verbatim in their brief.

**In one sentence:** *"A conversational engine whose every claim is grounded in a knowledge graph and whose faithfulness is continuously benchmarked — because the hard part of an assistant like Joule isn't the conversation, it's not being wrong."*

## Newport Beach — Developer Experience

**What the team does (publicly stated focus):** leverage AI across the DevOps flow; automated retrieval of root-cause analyses when a pipeline fails; a pull-request bot that summarizes a PR from its diff; enrich with context from systems like Jira; PoCs that can roll out to ~20,000 developers.

**What in Tessera maps to it:**
- **Reference vertical B (DevEx Copilot)** — RCA on failed pipelines, PR summarization from diffs, ticket-context enrichment. This is a near-literal match to their listed concrete projects.
- The fact that the *same engine* serves this and the business vertical demonstrates the generalization that a platform team cares about.

**In one sentence:** *"The same grounded-reasoning engine, pointed at CI logs, PR diffs, and tickets, produces sourced root-cause hypotheses and change summaries — the developer-experience use case, built on a general core rather than a one-off script."*

## Singapore — Tabular AI

**What the team does (publicly stated focus):** integrate SAP's Business Foundation Model / knowledge graph / LLMs for generic data matching across any tabular data, structured and unstructured; synthetic data generation; foundation-model fine-tuning; data-relation knowledge graph. Wants strong ML/NLP, Python, PyTorch/TensorFlow, data engineering.

**What in Tessera maps to it:**
- **Pillar 2 (cross-source entity resolution → knowledge graph)** — this *is* generic data matching across structured and unstructured data, unified in a graph.
- **Pillar 4's synthetic data generation** — directly named in their brief.
- A focused, well-explained adaptation of the matching/embedding component speaks to the "foundation-model fine-tuning" preference without overreaching into training base models.

**In one sentence:** *"The matching layer resolves the same entity across a database row, a contract clause, and a log tag into one graph node — generic data matching over any tabular and unstructured data, evaluated with generated synthetic cases."*

---

## SAP systems and platform fit

The project is designed to run *on* SAP's AI infrastructure, which is what turns "relevant project" into "built the way SAP builds." Name these deliberately:

- **SAP AI Core** — as the model orchestration and serving layer for the reasoning components. The intent is to run Tessera's models here rather than on a generic cloud, demonstrating familiarity with SAP's own MLOps surface.
- **SAP Generative AI Hub** — as the access point for the LLM/embedding capabilities, mirroring how SAP itself integrates generative AI into business applications.
- **SAP HANA Cloud** — as the home for the knowledge graph and vector/embedding layer, using HANA's graph and vector capabilities rather than a separate external store.
- **SAP Business Technology Platform (BTP)** — as the surrounding platform context; a free-tier footprint is enough to say, truthfully, "this runs on BTP."
- **Joule** — as the conceptual model for the conversational surface; Tessera's interface is deliberately shaped to resemble a Joule-style assistant.

**Honesty note:** the stated posture is "designed to run on SAP AI Core and HANA Cloud, with a portable local mode as the default" — and where it *ran* on SAP, that is a recorded measurement ([DEPLOYMENT.md](DEPLOYMENT.md), [SALT_REAL.md](SALT_REAL.md)), never a pretense that a free-tier experiment is a production deployment.

---

## Current SAP direction (2026) — and why Tessera is robust to year-to-year drift

Team descriptions shift slightly from year to year; the *underlying problems the labs work on* change far more slowly. The 2026 evidence is that SAP has moved **toward** Tessera's thesis, not away from it. Build for these stable fundamentals and the project survives whatever the exact 2027 listing says:

- **Knowledge graph as the grounding/context layer.** SAP now frames the **SAP Knowledge Graph** as the foundational context layer for the autonomous enterprise, explicitly because graphs give explainability and explainability is the key to enterprise-AI trust. Tessera's KG + provenance model *is* this idea. Use SAP's own language: grounding, context layer, explainability.
- **Trust, accuracy, auditability as THE differentiator.** SAP's stated themes are "AI agent accuracy, embedded domain knowledge," and agents that are "trustworthy, repeatable, and auditable." Tessera's measured faithfulness is the most on-target possible response to this. This is the headline to lead with everywhere.
- **Table-native foundation models + linked tables (Singapore).** SAP's Foundation Model family (table-native, in-context learning) and the **SALT / SALT-KG** datasets (real ERP tables + a curated knowledge graph) are exactly the "tabular + graph" world Tessera's matching layer lives in. Tessera should use in-context / pretrained tabular models rather than training from scratch — which also matches how SAP itself works. The **Reltio** acquisition (master-data unification) confirms entity resolution / data matching is a first-class SAP concern.
- **Agentic everything (the one real update).** SAP in 2026 is all-in on agents: Joule Studio, 50+ domain agents, an Agent-to-Agent (A2A) protocol, and MCP servers. A pure question-answer engine reads as 2024. Tessera should therefore include an **agentic mode** (grounded multi-step actions, not just answers) and speak **MCP** — both consuming external tools/data via MCP and being usable as an MCP-exposed capability. This single addition moves the project from "current-ish" to "obviously 2026."
- **GenAI across the SDLC + measured developer productivity (Newport Beach).** The DevEx team's stable core is applying genAI across the whole software lifecycle — code maintainability, large-scale refactoring/transformation, documentation quality — and *measuring* the impact (DORA / SPACE / DevEx metrics). Frame the DevEx vertical broadly around that, and note the nice parallel: Tessera measures faithfulness the way the DevEx team measures productivity — same evidence-driven mindset.

**Robustness rule:** target the *fundamentals* above (which barely move), keep the per-location framing in a thin layer you can re-tune in an afternoon, and never hard-code the project to one year's exact wording. If a 2027 description shifts emphasis, you adjust a few sentences in `README` and this file — not the engine.

---

## One caution worth keeping

Senior engineers are allergic to overclaiming. The credible, powerful version of this story is *"I integrated hard, usually-separate pieces into one disciplined, measurable system, on your platform, aimed at your problems."* The non-credible version is *"I invented something that doesn't exist."* Stay on the first one — it is both true and more impressive to the people who will actually read it.

---

## Addendum (2026-07-03, spec 0128) — what changed since the section above was written

The "Current SAP direction (2026)" section above has aged in Tessera's
favor, and one of its recommendations is now simply *done*:

- **The "agentic everything" recommendation is DELIVERED, measured, and
  recorded.** The section above says Tessera "should therefore include an
  agentic mode … and speak MCP." It does, since Milestones 11–15: an MCP
  server exposing the grounded tools, evidence-gated action drafts, exact
  payload previews, and execution behind approval with receipts — four
  measured trust boundaries (ADR 0022–0025), one real send on the record,
  and a recorded session of a **real Claude agent grounded only through
  Tessera's MCP tools** (`data/agent_session/`). Read "should add" above
  as historical context, not a to-do.
- **Sapphire 2026 (May 12) sharpened the vocabulary** (verified in
  [MARKET.md §7](MARKET.md)): the **SAP Business AI Platform** with the
  **SAP Knowledge Graph** inside it; "relevant, reliable, responsible";
  **SAP + Anthropic bringing Claude in "via MCP"** — i.e. SAP chose the
  protocol Tessera already speaks; the **AI Agent Hub** (in LeanIX, Q3
  2026) with "verification badges" — *asserted* trust, which is exactly
  the asymmetry to name: **SAP asserts trust at platform level; Tessera
  measures it at claim level — and gates action on it.** Supporting
  hooks: the DSAG 2026 finding (77% run non-SAP AI in production, 3% use
  SAP's own — trust must be earned), **SALT-KG** (SAP-authored: models
  show "gaps in [their] ability to leverage semantics in relational
  context" — this project's thesis), and the **Prior Labs** acquisition
  (frontier tabular lab).
- **"Ran on SAP" is now partially literal**, not aspirational: two
  recorded online closes on HANA Cloud in-database embeddings
  (`VECTOR_EMBEDDING`: github_actions 0.833 → 1.000, devex 0.950 →
  1.000, `eval/history.jsonl`), and knowledge-graph persistence for HANA
  Cloud's KG engine (RDF/SPARQL) built behind a tested seam. (Measured
  2026-07-04: the KG engine is tier-gated — free-tier instances offer no
  Triple Store — so its own recorded run awaits a paid-tier instance, a
  spend decision; spec 0129, DEPLOYMENT.md.)

## Addendum (2026-07-18, specs 0143/0144) — the governance layer

Two additions sharpen the "SAP asserts trust at platform level; Tessera
measures it at claim level" asymmetry into an operational story a
platform/governance team can run:

- **Chained bundles ([CHAIN.md](CHAIN.md))** carry provenance across
  agent hand-offs — the shape a Joule-style landscape actually has
  (agents consuming agents' outputs across systems) — with the whole
  chain re-executable offline from one file.
- **Trust policies ([POLICY.md](POLICY.md))** express the controls an
  enterprise already governs by — four-eyes approval gates, read-only
  (segregation-of-duties-flavored) agents, system-of-record evidence
  allowlists, signed origin, bounded delegation depth — as a small,
  versioned rule file the **verifier re-executes** against any decision,
  including every link of a chain. Where an agent-hub badge *asserts*
  that an agent is trustworthy in general, a policy verdict *proves*
  that one concrete decision satisfied the team's own named rules, and
  can be re-proven offline forever. Mapping language only, as
  throughout: this describes conceptual fit, not a product integration.

The maintainer's application material lives outside the public
repository (see `launch/README.md`).
