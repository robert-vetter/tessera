# Roadmap — Tessera

A deliberately paced plan across roughly **3–4 months**, built so that the commit history reads as a genuine, deepening engineering effort rather than a single drop. The guiding rule is **vertical slice first**: get one thin path working end-to-end before adding breadth, so there is always something real to show.

This is a scope-and-sequence document, not a schedule with implementation tasks. Each phase states *what becomes true* by the end of it.

---

## Principles for the build

- **Always shippable.** At the end of every phase there is a working demo, however small.
- **Eval green.** The faithfulness metric exists early and stays meaningful; no phase "breaks trust to add a feature."
- **One thing at a time.** Breadth (more connectors, more sources) comes only after the thin path works.
- **Document as you go.** Each phase ends with notes on what works, what doesn't, and why — this material becomes the write-up.
- **Commit honestly.** Small, frequent, well-described commits that reflect the actual progression of the work.

---

## Phase 0 — Foundation and frame (≈ week 1)

*What becomes true:* the project exists as a real, navigable repository with its vision written down and its development environment reproducible.

- Repository, license, and these design docs in place.
- A reproducible local environment so anyone can run what exists.
- The smallest possible "hello world" of the conversational surface answering a hardcoded grounded question — proves the skeleton end-to-end before any real data.

## Phase 1 — The thin vertical slice (≈ weeks 2–5)

*What becomes true:* one structured source and one unstructured source are ingested, partially unified, and queryable with grounded, sourced answers — for the **Business Data Copilot** vertical.

- Universal ingestion working for **one** structured and **one** unstructured source.
- A first version of the knowledge graph with basic cross-source entity resolution between those two sources.
- Grounded conversational answers with claim-level provenance for a narrow class of questions.
- The **first version of the evaluation harness**: a small gold set and a working faithfulness number, even if crude.

*Milestone:* a person can ask one realistic cross-source question and get a sourced answer, and there is a number describing how faithful it was.

## Phase 2 — Deepen trust and reasoning (≈ weeks 6–9)

*What becomes true:* the system handles genuinely hard questions and the trust metric is rigorous enough to defend.

- Question routing distinguishes simple lookups from multi-step reasoning.
- Multi-step reasoning across several entities and both modalities.
- Principled refusal when evidence is insufficient.
- Synthetic data generation feeding the harness, including the deliberately tricky cases (ambiguous entities, missing evidence, conflicting sources).
- Faithfulness, coverage, and quality metrics all defined, automated, and tracked over time.

*Milestone:* the trust metric is auditable and has visibly improved since Phase 1; the system can correctly say "I don't have enough evidence."

## Phase 3 — Prove generalization with the second vertical (≈ weeks 10–13)

*What becomes true:* the **same engine** serves the **DevEx Copilot**, proving the core is general and not secretly business-data-specific.

- Ingest CI/CD logs, PR diffs, and ticket history into the same graph machinery.
- Root-cause hypotheses for failed pipelines, grounded in logs and linked to prior incidents.
- PR change-summaries tying diffs to motivating tickets.
- The evaluation harness extended to this vertical so trust is measured here too.

*Milestone:* two genuinely different verticals run on one unchanged core, both measured.

## Phase 4 — Platform, polish, and the story (≈ weeks 14–16)

*What becomes true:* the project runs on SAP infrastructure, is presentable to a stranger, and has a written narrative.

- Deployment path onto **SAP AI Core / Generative AI Hub** for the models and **SAP HANA Cloud** for the graph/vector layer, with the portable local mode preserved for development.
- The conversational surface polished into a Joule-style experience with explorable provenance and a visible trust signal.
- A clear technical write-up / blog post: the problem, the approach, the honest results (including limitations), and what was learned.
- Documentation a non-author can follow end-to-end.

*Milestone:* a senior engineer can clone, run, read, and understand the project — and a non-technical reader can grasp why it matters — without the author in the room.

---

## What is intentionally left for "future work"

Naming these honestly *strengthens* the project — it shows judgment about scope:

- Production-grade security, multi-tenancy, and access governance.
- A broad catalog of source connectors.
- Training or large-scale fine-tuning of foundation models from scratch.
- Real-time / streaming ingestion at enterprise scale.

These belong in a "Future work" section of the write-up, framed as known and deliberately deferred — not as gaps the author missed.

---

## On the commit history

The roadmap is paced the way it is partly so the repository's history is itself evidence: months of steady, thoughtful commits with clear messages, each tied to a phase. That history is a more honest signal of genuine, early interest than any timestamp claim — and it is the kind of signal an engineer trusts because it cannot be faked after the fact.
