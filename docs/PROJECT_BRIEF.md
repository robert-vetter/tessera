# Project Brief — Tessera

*A trust layer for enterprise AI agents.*

This document is the deep description of **what Tessera is, why it exists, what it must do, and what "excellent" means for it.** It deliberately contains **no implementation detail** — no code, no class design, no concrete algorithms. It defines the frame; the build fills it in.

---

## 1. Context and motivation

Large organizations have spent two years connecting language models to their data and discovering the same wall: the models are capable, but the *answers cannot be trusted at the level a business decision requires.* The failure modes are consistent:

- **Silent source mixing.** The system pulls a figure from one document and a definition from another and presents a blended answer that is true in neither place.
- **Confident fabrication.** When evidence is thin, the model fills the gap with something fluent and plausible, and nothing in the output signals that it did so.
- **No traceability.** When an answer *is* right, the user still cannot see *why* — which record, which row, which paragraph it rests on. So they cannot verify it, and verification is the entire point in an enterprise setting.
- **No measurement.** Teams ship these systems on demos and anecdotes because there is no honest, repeatable number for "how faithful is this to our data?"

This is not a model problem. It is a **grounding, provenance, and measurement** problem. The model is necessary but not sufficient. The missing layer is the one that connects the model's fluency to the organization's ground truth and *proves* the connection.

SAP has named this problem out loud, three times, in three places:
- Palo Alto's Joule team wants to "minimize errors" by reasoning over knowledge substrates and knowledge graphs.
- Singapore's Tabular AI team wants generic data matching across any structured and unstructured data, unified through a knowledge graph.
- Newport Beach's Developer Experience team wants an assistant grounded in logs, diffs, and tickets that developers can rely on.

Tessera is one coherent answer to all three.

## 2. The gap — what exists, and what does not

It is important to be precise and honest here, because overclaiming is exactly what makes an experienced engineer stop reading.

**What already exists and is mature:**
- Retrieval-augmented generation over unstructured documents.
- Knowledge graphs and graph databases.
- Entity resolution / record linkage as a classical data-engineering discipline.
- LLM evaluation tooling for generic quality.

**What is rare, fragmented, or missing:**
- A system that treats **structured and unstructured data as first-class citizens of the same graph**, so a question can be answered using a database row and a contract clause *in the same reasoning step*.
- A **uniform provenance model** in which every claim in a generated answer carries a traceable path back to the specific source records that justify it — not a vague "sources" list at the bottom.
- **Faithfulness as a measured, first-class metric**, baked into the development loop from day one, rather than a manual spot-check before a demo.
- All of the above **packaged together as one open, coherent system** rather than stitched from five libraries by each team independently.

Tessera's contribution is the *integration and the discipline*, not the invention of any single component. That is a more credible and more defensible claim — and, not coincidentally, it is also the genuinely hard part.

## 3. Vision

> A user asks a question in plain language. Tessera decides how hard the question is and routes it accordingly. It assembles an answer from a unified graph of the organization's data — structured and unstructured alike. Every sentence of that answer is anchored to the exact records that support it, visible and clickable. And behind the scenes, a benchmark has already told the team how faithful this system is on questions like this one, with a number they trust because they can see how it was computed.

When that experience works across both a business-data scenario and a developer-tooling scenario on the *same engine*, the engine has proven it generalizes — which is the whole game.

## 4. Design principles

These are non-negotiable and should be visible in every decision:

1. **Groundedness over fluency.** A correct, well-sourced "I don't have enough evidence to answer that" beats a fluent guess. The system must be able to *decline*.
2. **Provenance is not optional.** If a claim cannot be traced to evidence, it does not appear in the answer.
3. **Trust must be measurable.** No feature is "done" until its effect on the faithfulness metric is known.
4. **Structured and unstructured are equal.** Neither modality is a second-class add-on bolted onto the other.
5. **The engine is general; the verticals are demonstrations.** Nothing vertical-specific leaks into the core.
6. **Built on the platform, not around it.** Where SAP provides the right primitive (model orchestration, graph store, vector store), use it rather than reinventing it.
7. **Honest scope.** Ship a working vertical slice early and deepen it. No vaporware, no "phase 5 will fix it."

## 5. Scope

### In scope
- Universal ingestion of structured and unstructured sources through one intake path.
- Cross-source entity resolution into a single, queryable knowledge graph.
- A grounded conversational interface with claim-level provenance and explicit routing of easy vs. hard questions.
- An evaluation harness with synthetic data generation, a curated gold set, and faithfulness / coverage / quality metrics.
- Two reference verticals (Business Data Copilot, DevEx Copilot) on the shared engine.
- Deployment path onto SAP AI infrastructure.

### Explicitly out of scope (and why)
- **A general-purpose chatbot.** Tessera answers from *grounded* data; it is not a creative assistant.
- **Fine-tuning a foundation model from scratch.** A small, targeted adaptation may appear for the matching/embedding component, but training base models is neither necessary nor in budget. *(Note: Singapore lists foundation-model fine-tuning experience as preferred — a focused, well-explained adaptation is enough to speak to that credibly without overreaching.)*
- **Production-grade multi-tenant security/governance.** Acknowledged as essential in real deployment; out of scope for a demonstrator, and called out as such honestly.
- **Owning every connector under the sun.** A small number of high-quality connectors that prove the model generalizes beats a long, shallow list.

## 6. Target users and scenarios

- **A business analyst** asking, *"Which of our enterprise contracts auto-renew in Q3, and what's the combined annual value?"* — an answer that needs a database join *and* clause extraction from PDFs, returned with every figure traceable.
- **An on-call engineer** asking, *"Why did last night's deployment pipeline fail, and has this happened before?"* — an answer that reads CI logs, links to the offending change, and surfaces the prior incident, each claim sourced.
- **A reviewer** asking, *"What does this pull request actually change about how we handle refunds?"* — a grounded summary that ties the diff to the ticket that motivated it.

## 7. What "done" and "excellent" mean

A reasonable senior engineer should be able to look at the finished project and conclude, without being told:

- The author understood that the hard part is **trust, not text generation.**
- The author **measured** that trust honestly and improved it on the metric.
- The engine **generalized** — proven by two genuinely different verticals running on it.
- The author can **explain and document** the work clearly (the PoC roles at SAP are explicitly about requirements, user research, and standards — communication is part of the deliverable).
- The work **fits SAP's platform and problems** specifically, not generically.

Success criteria, concretely:
- A working end-to-end demo of each vertical on real or realistic data.
- A faithfulness metric that is defined, computed automatically, and visibly improved over the project's lifetime.
- Documentation a non-author can follow, including an honest write-up of what works, what doesn't, and why.
- A commit history that tells the story of the build over months, not a single drop.

## 8. Risks and how the scope manages them

- **Over-ambition.** Mitigated by the "vertical slice first" principle — one source pair, one vertical, end-to-end, before breadth.
- **Entity resolution is genuinely hard.** Mitigated by starting with a constrained, well-understood domain and being honest about precision/recall rather than claiming perfection.
- **Evaluation can become theater.** Mitigated by making the gold set and synthetic-data process transparent and documented, so the metric is auditable.
- **SAP-stack integration friction.** Mitigated by designing the engine to be platform-portable, with SAP infrastructure as the primary target but not a hard dependency for local development.

---

*This brief defines the frame. [`CAPABILITIES.md`](CAPABILITIES.md) describes what the system can do at feature level; [`ROADMAP.md`](ROADMAP.md) describes the order it gets built in; [`SAP_ALIGNMENT.md`](SAP_ALIGNMENT.md) maps it onto the three target teams.*
