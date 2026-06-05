# Capabilities — Tessera

This document describes **what the system can do, at the level of features and behaviors.** It stays above implementation: it says *what* each part is responsible for and *what it must guarantee*, not *how* it is coded. Read it as the functional contract the build has to satisfy.

---

## Pillar 1 — Universal ingestion

**Responsibility:** bring heterogeneous enterprise data into the system through one consistent intake path, regardless of shape.

Capabilities:
- Accept **structured sources**: relational tables, spreadsheet exports, CSV/TSV, and structured API payloads.
- Accept **unstructured sources**: documents (PDF, office formats, markdown), plain-text runbooks, log files, ticket exports, and chat/thread transcripts.
- Normalize every incoming source into a common internal representation so that downstream components never need to care where a fact originated.
- Preserve, for every ingested unit of information, **enough origin metadata to reconstruct provenance later** (which source, which row/page/line, when it was ingested).
- Be incremental: re-ingesting an updated source should update the graph, not duplicate it.

Guarantees:
- No information enters the system without an attached, retrievable origin.
- Structured and unstructured data arrive at the graph through the *same* door — neither is privileged.

## Pillar 2 — Cross-source entity resolution and the knowledge graph

**Responsibility:** discover that the same real-world entity appears under different names and forms across sources, and assemble all sources into one unified, queryable graph.

Capabilities:
- Identify candidate entities across heterogeneous sources (a customer in a table, the same customer named differently in a contract, the same customer as a tag in a log).
- Decide, with a confidence judgment, whether two candidates are the same entity, and **record that decision and its confidence** rather than collapsing silently.
- Build a graph in which entities are nodes, relationships are edges, and **every node and edge points back to the source evidence that established it.**
- Support both structured relationships (foreign-key-like links) and relationships extracted from unstructured text.
- Make the unified graph queryable as a single object — a question can traverse from a database-derived node to a document-derived node in one path.

Guarantees:
- Every merge decision is inspectable and reversible — entity resolution is treated as fallible and auditable, not as ground truth.
- The graph is the single source of truth that all reasoning draws on.

*(This pillar is the direct analogue of Singapore's "any data matching for tabular AI" — generic matching across structured and unstructured data, unified through a knowledge graph.)*

## Pillar 3 — Grounded conversational reasoning with provenance

**Responsibility:** answer natural-language questions using only what the graph supports, and make the support visible.

Capabilities:
- **Question routing:** distinguish a simple lookup from a question that needs multi-step reasoning across several entities and sources, and handle each appropriately rather than over- or under-thinking.
- **Evidence assembly:** gather the relevant subgraph and source records before composing an answer, so the answer is built *from* evidence rather than decorated with citations after the fact.
- **Claim-level provenance:** attach to **each individual claim** in the answer a traceable path back to the specific records that justify it — visible to the user, not buried.
- **Principled refusal:** when the graph does not contain enough evidence, say so clearly instead of guessing. The ability to decline is a feature, not a failure.
- **Conversational continuity:** support follow-up questions that refine or build on the previous answer while keeping provenance intact.

Guarantees:
- No claim appears in an answer without a provenance path.
- A user can always get from any sentence of the answer to the evidence behind it in one step.

*(This pillar is the direct analogue of Palo Alto's Joule work — a conversational assistant with intelligent routing and reasoning, grounded in knowledge substrates to minimize errors.)*

## Pillar 4 — Quantified trust (the evaluation harness)

**Responsibility:** turn "do we trust this system?" into measured, repeatable numbers, and make those numbers part of the development loop.

Capabilities:
- **Synthetic data generation:** programmatically produce realistic question/evidence/answer scenarios over a known graph, including deliberately tricky cases (ambiguous entities, missing evidence, conflicting sources) so the metric stresses the hard parts.
- **Curated gold set:** a smaller, human-checked set of questions with known correct, fully-sourced answers, used to keep the synthetic metric honest.
- **Faithfulness metric:** measure whether every claim in an answer is actually supported by its cited evidence — the core trust number.
- **Coverage metric:** measure whether the system found the evidence that *was* available, versus declining or missing it.
- **Quality metrics:** measure answer correctness and usefulness against the gold set.
- **Regression tracking:** run the whole battery automatically so the team can see each change's effect on trust over time.

Guarantees:
- The metric definitions and the synthetic-data process are transparent and documented — the score is auditable, not a black box.
- No capability is considered finished until its effect on these numbers is known.

*(This pillar is the direct analogue of Palo Alto's "standardized benchmarking and data augmentation to assess solution quality" and Singapore's synthetic data generation.)*

## The conversational surface

**Responsibility:** present all of the above through an interface that feels like talking to a knowledgeable, honest colleague.

Capabilities:
- Natural-language question input and conversational answers.
- Inline, explorable provenance — the user can open any claim and see its evidence.
- A visible trust signal so the user knows when the system is confident versus stretching.
- Designed to resemble the interaction model of a Joule-style enterprise assistant.

## Agentic mode and interoperability

**Responsibility:** go beyond answering — take grounded, multi-step actions — and interoperate with the surrounding tool ecosystem the way 2026 enterprise AI is expected to.

Capabilities:
- **Grounded agentic workflows:** for tasks that require more than retrieval, plan and execute a sequence of steps, with each step's inputs and outputs still tied to evidence. The bar that distinguishes this from a generic agent is that *the chain of actions remains auditable* — every step's justification traces to the graph.
- **Reliable, goal-driven behavior:** the agent pursues a stated goal and can report honestly when it cannot complete it with the available evidence, rather than fabricating a result. Reliability is measured, not assumed.
- **MCP interoperability (both directions):** consume external tools and data sources through the Model Context Protocol, and expose Tessera's own grounded-query capability as an MCP-accessible tool so other agents can call it. This mirrors SAP's 2026 direction (MCP servers, Agent-to-Agent interoperability) and means Tessera is a *participant* in an agent ecosystem, not an island.

Guarantees:
- An agentic action is never taken on un-grounded reasoning; the audit trail covers actions, not just answers.
- The agent can decline a goal it cannot achieve faithfully.

*(This section reflects SAP's 2026 push into agentic AI — Joule Studio, domain agents, Agent-to-Agent, and MCP. See [`SAP_ALIGNMENT.md`](SAP_ALIGNMENT.md).)*

## Reference vertical A — Business Data Copilot

**Demonstrates** the engine on business records + documents.

- Answer questions that require combining structured records (customers, contracts, transactions) with unstructured documents (agreements, policies, correspondence).
- Example class: questions about contract terms, renewals, obligations, and aggregate values that no single source can answer alone.
- Every figure and claim sourced to its row or clause.

## Reference vertical B — DevEx Copilot

**Demonstrates** the same engine on developer/operations data.

- Ingest CI/CD pipeline logs, pull-request diffs, and ticket history into the same kind of graph.
- Answer *"why did this pipeline fail, and has it happened before?"* with root-cause hypotheses grounded in the logs and linked to prior incidents.
- Summarize *"what does this change actually do?"* by tying a diff to the ticket that motivated it.
- Every hypothesis and summary sourced to the specific log lines, diff hunks, and tickets behind it.

*(This vertical is the direct analogue of Newport Beach's developer-experience work — RCA on failed pipelines, PR summarization from diffs, enriched with ticket context.)*

---

*What each pillar must guarantee is fixed here. The order of construction is in [`ROADMAP.md`](ROADMAP.md). How it maps to SAP is in [`SAP_ALIGNMENT.md`](SAP_ALIGNMENT.md).*
