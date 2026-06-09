# Tessera

**A trust layer for enterprise AI agents.**
Every answer traceable to its evidence — across structured *and* unstructured data — with a number that tells you how much to trust it.

[![CI](https://github.com/robert-vetter/tessera/actions/workflows/ci.yml/badge.svg)](https://github.com/robert-vetter/tessera/actions/workflows/ci.yml)
[![Docs](https://github.com/robert-vetter/tessera/actions/workflows/docs.yml/badge.svg)](https://robert-vetter.github.io/tessera/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<!-- Coverage and faithfulness/eval badges are deliberately omitted until Phase 1,
     when the evaluation harness and coverage measurement exist. The faithfulness
     badge is the headline signal — it ships only once the number is real. -->

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

## Development setup

The project uses [uv](https://docs.astral.sh/uv/) for Python environment and
dependency management. From a fresh clone:

```bash
uv sync                      # create the environment from uv.lock
uv run pre-commit install    # one-time: enable local commit gates
```

Run the quality gate at any time with `uv run pre-commit run --all-files`
(format, lint, secret scan, hygiene). The fuller gate — types and tests —
runs via `uv run mypy src tests` and `uv run pytest`.

### No toolchain? Use the container

A `Dockerfile` and a [devcontainer](.devcontainer/devcontainer.json) provide a
clean, pinned environment with no host setup beyond Docker:

```bash
docker build -t tessera-dev .          # build the pinned image
docker run --rm tessera-dev pytest     # run the test suite inside it
```

Or open the folder in VS Code / GitHub Codespaces and "Reopen in Container" —
the environment builds and syncs automatically.

### Try the demo

A deterministic slice proves the end-to-end shape — *question → retrieve evidence
→ grounded answer with provenance → render*. The evidence is **ingested** from a
structured dataset and a document corpus; a lexical retriever selects the records
relevant to a question, and every surfaced claim traces back to the specific
source behind it.

```bash
uv run tessera
# Surfaces the records relevant to a customer-orders question — each traced to its
# ingested source row (file + table + row).

uv run tessera "What are the renewal and termination terms of the service agreement?"
# Retrieves a *document* clause; the claim traces to a specific span (file + lines).

uv run tessera "What colour is the sky?"
# No evidence shares its terms → a principled refusal, not a guess.
```

**What the answer is — and isn't.** This slice *retrieves and sources evidence*: it
surfaces the records that match your question, each with provenance. It does
**not** yet synthesize prose or compute aggregates — it shows the relevant sales
rows, not a single "combined value is EUR X"; that synthesis is multi-step
reasoning, a later phase. Surfacing evidence rather than a polished sentence is
the *honest* state of the slice, not a regression. There is no model: retrieval is
lexical, deterministic, and offline
([ADR 0003](docs/adr/0003-lexical-first-retrieval.md)). What is already real is the
ingestion, the retrieval, the provenance, and the principled refusal — exactly
what the evaluation harness will measure.

### The eval harness

Trust is measured, so the eval is runnable from the start:

```bash
uv run tessera-eval
# Eval over 6 gold case(s): faithfulness 1.000 (floor 1.000), coverage 0.929,
# quality 1.000.
```

The numbers are real and **auditable**, scored against the answers the engine
actually produces over a small, hand-curated gold set in [`eval/gold/`](eval/gold/):

- **Faithfulness** — every emitted claim is deterministically supported by its
  cited evidence. It is a **hard floor of 1.0** (an unsupported claim fails the
  build) and is *provably able to fail*: a test injects a known-unfaithful claim
  and confirms the metric catches it — so the 1.0 is earned, not tautological.
- **Coverage** — how much of the available evidence the answers surface. Honestly
  **below 1.0** (the Lumière agreement clause is a known mention miss), so there is
  a real number to improve.
- **Quality** — gold answers correct / refusals refused.

Definition and what the number does (and does not) prove:
[ADR 0005](docs/adr/0005-faithfulness-metric.md).

### Knowledge graph & entity resolution

The ingested records are assembled into an in-process knowledge graph, and a
**non-destructive** resolution layer recognizes when records across the two
sources name the same real entity — e.g. the customer master's "Müller Logistik
GmbH", the address master's "Mueller Logistik Gmbh", and the agreement that names
the same firm. Resolution is **additive and reversible**: a same-entity assertion
records *why* (the matched names + a similarity score) and a confidence, and
withdrawing it leaves the raw records untouched — merges are never destructive.
Matching is deterministic name-similarity (umlaut/case fold + edit-distance), with
a tunable threshold; it is honest about precision/recall and about known misses
(a reference that drops a legal form isn't linked yet). Design and trade-offs:
[ADR 0004](docs/adr/0004-graph-and-entity-resolution.md).

### Cross-source answers

Composing over that graph gives the Phase 1 payoff — one grounded answer that
combines a database **row** and a document **clause** about the *same* resolved
entity:

```bash
uv run tessera-compose "Summarise Müller Logistik: its sales orders and agreement terms."
# Resolves the entity, then answers with its sales total AND its agreement's
# renewal terms — each claim traced to a row or a clause.
```

The one synthesis it performs — the entity's total net order value — is summed
over its sales rows with **every summand cited**, and it **refuses to sum across
different currencies** rather than invent a number (try
`uv run tessera-compose "What is Atlas Trading's total order value?"`). General
multi-step reasoning and question routing are a later phase.

### Data

Both modalities arrive through one ingestion path:

- **Structured** — [`data/salt_synthetic/`](data/salt_synthetic/), **synthetic**
  data generated by `scripts/generate_salt_synthetic.py` using the *schema* of
  SAP's [SALT](https://huggingface.co/datasets/SAP/SALT) (Sales Autocompletion
  Linked Business Tables; arXiv:2501.03413): the same tables, columns, and join
  keys. We generate our own data because real SALT is access-gated and
  redistributing a derived sample is legally unclear; using SALT's real schema
  means ingesting the actual SALT dataset later is a drop-in swap. Regenerate it
  deterministically with `uv run python scripts/generate_salt_synthetic.py`. See
  [`data/salt_synthetic/NOTICE`](data/salt_synthetic/NOTICE).
- **Unstructured** — [`data/business_docs/`](data/business_docs/), a small corpus
  of authored agreements/correspondence that reference the same synthetic
  customers under *variant* name forms (so entity resolution is genuine) and carry
  information the tables lack (renewal clauses, terms, special conditions).

Both deliberately contain entity-resolution difficulty for later phases.

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

Code is **MIT** (intended). The synthetic dataset under `data/salt_synthetic/`
is also covered by the project's MIT license — it is our own generated data and
carries no third-party encumbrance. It is *modeled on* the schema of SAP's SALT
dataset (credited in [`data/salt_synthetic/NOTICE`](data/salt_synthetic/NOTICE));
the real SALT dataset is gated and is **not** redistributed here.
