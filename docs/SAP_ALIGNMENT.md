# SAP Alignment — Tessera

This is the document that connects the project to the three target teams and the SAP platform. It exists so that anyone reading the application can see, in one glance, that this was built *for* SAP's problems — not a generic side project retrofitted with SAP keywords.

---

## The shared insight

Three SAP AI groups are working on three faces of one problem: **take heterogeneous enterprise data, unify it, reason over it, and make the result trustworthy.** Tessera is a single engine built so that one slice of it speaks directly to each team. The point to make in the application is not "I built something near your area" — it is "I independently arrived at the same core problem you are solving, and built a coherent answer to it."

---

## Palo Alto — GenAI Central Engineering / Joule

**What the team does (from the program brief):** advance AI for business-user productivity; build the conversational interface of Joule with intelligent routing and reasoning; use knowledge substrates and knowledge graphs to minimize errors; provide standardized benchmarking and data augmentation to assess quality.

**What in Tessera maps to it:**
- **Pillar 3 (grounded conversational reasoning)** — question routing, multi-step reasoning, a Joule-style conversational surface.
- **Knowledge-graph grounding to minimize errors** — the entire provenance model exists to reduce exactly the errors this team is fighting.
- **Pillar 4 (quantified trust)** — standardized benchmarking and synthetic data augmentation to assess solution quality, which is named almost verbatim in their brief.

**The sentence for the application:** *"I built a conversational engine whose every claim is grounded in a knowledge graph and whose faithfulness is continuously benchmarked — because the hard part of an assistant like Joule isn't the conversation, it's not being wrong."*

## Newport Beach — Developer Experience

**What the team does (from the program brief):** leverage AI across the DevOps flow; automated retrieval of root-cause analyses when a pipeline fails; a pull-request bot that summarizes a PR from its diff; enrich with context from systems like Jira; PoCs that can roll out to ~20,000 developers.

**What in Tessera maps to it:**
- **Reference vertical B (DevEx Copilot)** — RCA on failed pipelines, PR summarization from diffs, ticket-context enrichment. This is a near-literal match to their listed concrete projects.
- The fact that the *same engine* serves this and the business vertical demonstrates the generalization that a platform team cares about.

**The sentence for the application:** *"The same grounded-reasoning engine, pointed at CI logs, PR diffs, and tickets, produces sourced root-cause hypotheses and change summaries — the developer-experience use case, built on a general core rather than a one-off script."*

## Singapore — Tabular AI

**What the team does (from the program brief):** integrate SAP's Business Foundation Model / knowledge graph / LLMs for generic data matching across any tabular data, structured and unstructured; synthetic data generation; foundation-model fine-tuning; data-relation knowledge graph. Wants strong ML/NLP, Python, PyTorch/TensorFlow, data engineering.

**What in Tessera maps to it:**
- **Pillar 2 (cross-source entity resolution → knowledge graph)** — this *is* generic data matching across structured and unstructured data, unified in a graph.
- **Pillar 4's synthetic data generation** — directly named in their brief.
- A focused, well-explained adaptation of the matching/embedding component speaks to the "foundation-model fine-tuning" preference without overreaching into training base models.

**The sentence for the application:** *"The matching layer resolves the same entity across a database row, a contract clause, and a log tag into one graph node — generic data matching over any tabular and unstructured data, evaluated with generated synthetic cases."*

---

## SAP systems and platform fit

The project is designed to run *on* SAP's AI infrastructure, which is what turns "relevant project" into "this person already works the way we do." Name these deliberately:

- **SAP AI Core** — as the model orchestration and serving layer for the reasoning components. The intent is to run Tessera's models here rather than on a generic cloud, demonstrating familiarity with SAP's own MLOps surface.
- **SAP Generative AI Hub** — as the access point for the LLM/embedding capabilities, mirroring how SAP itself integrates generative AI into business applications.
- **SAP HANA Cloud** — as the home for the knowledge graph and vector/embedding layer, using HANA's graph and vector capabilities rather than a separate external store.
- **SAP Business Technology Platform (BTP)** — as the surrounding platform context; a free-tier footprint is enough to say, truthfully, "this runs on BTP."
- **Joule** — as the conceptual model for the conversational surface; Tessera's interface is deliberately shaped to resemble a Joule-style assistant.

**Honesty note for the application:** it is fine — better, even — to say "designed to run on SAP AI Core and HANA Cloud, with a portable local mode for development." That reads as a real engineer who understands platforms, not someone who pretends a free-tier experiment is a production deployment.

---

## Current SAP direction (2026) — and why Tessera is robust to year-to-year drift

The internship project descriptions change slightly from year to year; the *underlying problems the labs work on* change far more slowly. The 2026 evidence is that SAP has moved **toward** Tessera's thesis, not away from it. Build for these stable fundamentals and the project survives whatever the exact 2027 listing says:

- **Knowledge graph as the grounding/context layer.** SAP now frames the **SAP Knowledge Graph** as the foundational context layer for the autonomous enterprise, explicitly because graphs give explainability and explainability is the key to enterprise-AI trust. Tessera's KG + provenance model *is* this idea. Use SAP's own language: grounding, context layer, explainability.
- **Trust, accuracy, auditability as THE differentiator.** SAP's stated themes are "AI agent accuracy, embedded domain knowledge," and agents that are "trustworthy, repeatable, and auditable." Tessera's measured faithfulness is the most on-target possible response to this. This is the headline to lead with everywhere.
- **Table-native foundation models + linked tables (Singapore).** SAP's Foundation Model family (table-native, in-context learning) and the **SALT / SALT-KG** datasets (real ERP tables + a curated knowledge graph) are exactly the "tabular + graph" world Tessera's matching layer lives in. Tessera should use in-context / pretrained tabular models rather than training from scratch — which also matches how SAP itself works. The **Reltio** acquisition (master-data unification) confirms entity resolution / data matching is a first-class SAP concern.
- **Agentic everything (the one real update).** SAP in 2026 is all-in on agents: Joule Studio, 50+ domain agents, an Agent-to-Agent (A2A) protocol, and MCP servers. A pure question-answer engine reads as 2024. Tessera should therefore include an **agentic mode** (grounded multi-step actions, not just answers) and speak **MCP** — both consuming external tools/data via MCP and being usable as an MCP-exposed capability. This single addition moves the project from "current-ish" to "obviously 2026."
- **GenAI across the SDLC + measured developer productivity (Newport Beach).** The DevEx team's stable core is applying genAI across the whole software lifecycle — code maintainability, large-scale refactoring/transformation, documentation quality — and *measuring* the impact (DORA / SPACE / DevEx metrics). Frame the DevEx vertical broadly around that, and note the nice parallel: Tessera measures faithfulness the way the DevEx team measures productivity — same evidence-driven mindset.

**Robustness rule:** target the *fundamentals* above (which barely move), keep the per-location framing in a thin layer you can re-tune in an afternoon, and never hard-code the project to one year's exact wording. If a 2027 description shifts emphasis, you adjust a few sentences in `README` and this file — not the engine.

---

## How to actually use this in the motivation letter

- **Lead with the SAP-sponsored Deutschlandstipendium.** That is a genuine, verifiable prior connection to SAP — far stronger than any constructed proof of interest. Open with it.
- **Frame the project as convergence, not coincidence.** "I set out to solve the trust problem in enterprise AI, and discovered I had independently built toward the exact problems your Palo Alto, Newport Beach, and Singapore teams describe."
- **Pick the two or three target projects and tailor.** Do not gesture at all of SAP. Name the specific projects you want and show the matching slice of Tessera for each.
- **Let the metric do the bragging.** "Faithfulness improved from X to Y over the project" is more impressive to a senior engineer than any adjective. Numbers age well; superlatives don't.
- **Point to the write-up, not just the repo.** A clear technical post about the project demonstrates the requirements-and-communication side the PoC roles explicitly ask for.

---

## One caution worth keeping

Senior engineers are allergic to overclaiming. The credible, powerful version of this story is *"I integrated hard, usually-separate pieces into one disciplined, measurable system, on your platform, aimed at your problems."* The non-credible version is *"I invented something that doesn't exist."* Stay on the first one — it is both true and more impressive to the people who will actually read it.
