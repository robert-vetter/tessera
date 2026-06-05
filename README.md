# Tessera

**A trust layer for enterprise AI agents.**
Every answer traceable to its evidence — across structured *and* unstructured data — with a number that tells you how much to trust it.

> *Working name. A `tessera` is a single tile in a mosaic: many small, heterogeneous pieces assembled into one coherent, verifiable picture. That is exactly what this system does with enterprise data. Rename freely.*

---

## The one-paragraph version

Enterprise AI rarely fails because the language model is weak. It fails because nobody can trust the answer: the system silently mixes incompatible sources, invents details that sound plausible, and offers no way to trace a claim back to where it came from — let alone to *measure* how faithful it was. **Tessera** is an open framework that ingests heterogeneous enterprise data (database tables, spreadsheets, documents, logs, tickets), resolves the entities scattered across those sources into a single unified knowledge graph, and answers questions through a conversational interface in which **every individual claim is grounded in a traceable path back to the source records that support it**. On top of that, Tessera ships a benchmark harness that turns "do you trust this AI?" from a feeling into a metric — a faithfulness score, measured on synthetic and curated data, that you can watch go up as the system improves.

## Why this matters (and why it maps onto SAP's actual problems)

Three of SAP's AI groups are, underneath the surface, working on the *same* problem from three angles:

- **Palo Alto (GenAI / Joule):** make a digital assistant reason over business data and "minimize errors" using knowledge substrates and knowledge graphs; benchmark solution quality.
- **Singapore (Tabular AI):** perform generic *data matching* across any tabular and unstructured data using a foundation model + knowledge graph + LLMs; generate synthetic data; fine-tune.
- **Newport Beach (Developer Experience):** ground an assistant in CI logs, pull-request diffs, and Jira context to surface root-cause analyses and summarize changes for up to 20,000 developers.

All three reduce to: *take messy, multi-source enterprise data; unify it; reason over it; and do so in a way people can actually trust.* Tessera is a single, coherent take on that problem — built deliberately so that a slice of it speaks directly to each of those three teams.

See [`docs/SAP_ALIGNMENT.md`](docs/SAP_ALIGNMENT.md) for the explicit, location-by-location mapping.

## What Tessera does — four pillars

1. **Universal ingestion.** Pull in structured sources (relational tables, CSVs, exports) and unstructured ones (documents, runbooks, logs, tickets, chat threads) through one consistent intake path.
2. **Cross-source entity resolution → one knowledge graph.** Recognize that "Acme Corp" in a database, "ACME" in a contract PDF, and "acme-prod" in a deployment log are the same entity, and weave all sources into a single graph that can be queried as one.
3. **Grounded conversational reasoning with provenance.** Answer questions in natural language where the system routes simple lookups and multi-step reasoning differently, and where **every sentence in the answer is backed by a citation path** through the graph to the underlying records. No untraceable claims.
4. **Quantified trust.** A built-in evaluation harness — driven by synthetic data generation and a curated gold set — that scores *faithfulness* (is every claim supported by evidence?), *coverage*, and *answer quality*, so improvements are measurable rather than vibes.

## Two reference verticals, one engine

The same core engine powers two deliberately different demonstrations, to prove the engine generalizes:

- **Business Data Copilot** — ask questions across a company's structured records and documents and get grounded, cited answers. *(Speaks to Palo Alto / Singapore.)*
- **DevEx Copilot** — point it at CI/CD logs, pull-request diffs, and ticket history; get root-cause hypotheses for failed pipelines and grounded summaries of what a change actually does. *(Speaks to Newport Beach.)*

## What makes it genuinely hard (the honest version)

Grounded RAG exists. Knowledge graphs exist. Entity resolution exists. What is rare — and what this project is actually about — is **doing all of them together, across structured and unstructured data at once, with a uniform provenance model and a faithfulness metric that holds the whole thing accountable.** Most systems pick one modality, skip provenance, and never measure faithfulness at all. Tessera treats *measurable trust* as the headline feature, not an afterthought. That framing is what a senior engineer recognizes as the real, unglamorous, valuable problem.

## Built with (and toward) the SAP stack

Designed to run on SAP's own AI infrastructure rather than around it — SAP AI Core and the Generative AI Hub for model orchestration, SAP HANA Cloud for the graph and vector layer, and a Joule-style conversational surface. Beyond answering, Tessera supports **grounded agentic workflows** and speaks **MCP** (consuming external tools and exposing its own grounded-query capability), in line with SAP's 2026 move toward agentic AI, Joule Studio, and Agent-to-Agent interoperability. Details in [`docs/SAP_ALIGNMENT.md`](docs/SAP_ALIGNMENT.md).

## Repository map

| File | What's in it |
|------|--------------|
| [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md) | The deep brief: motivation, the gap, vision, principles, scope, success criteria |
| [`docs/CAPABILITIES.md`](docs/CAPABILITIES.md) | Feature-level breakdown of what each pillar can do |
| [`docs/SAP_ALIGNMENT.md`](docs/SAP_ALIGNMENT.md) | Location-by-location mapping + SAP systems + how to talk about it |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | The phased build plan across ~3–4 months |
| [`docs/ENGINEERING.md`](docs/ENGINEERING.md) | How the project is run: workflow, tooling, quality gates, anti-drift |
| [`docs/SETUP.md`](docs/SETUP.md) | How to go from these docs to a running, gated project |
| [`CLAUDE.md`](CLAUDE.md) | Working instructions for building this with Claude Code |

## Status

Early development. Vision and scope defined; implementation in progress. This is a long-running project built deliberately over several months — see the roadmap.

## License

MIT (intended).
