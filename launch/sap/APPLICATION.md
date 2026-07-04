# SAP application kit (iXp + working student) — assembled, not submitted

*Drafted 2026-07-03 (spec 0128). Vocabulary and program facts verified in
[docs/MARKET.md §7](../../docs/MARKET.md) (2026-07-02 snapshot; re-verify
anything time-sensitive at submission). The thesis-level mapping lives in
[docs/SAP_ALIGNMENT.md](../../docs/SAP_ALIGNMENT.md); this file is the
execution kit: where to apply, with which words, linking which artifacts.
Everything goes out under the maintainer's identity — nothing here is
submitted by tooling.*

## The two tracks (apply to BOTH — they are separate pipelines in Germany)

1. **iXp internship** (SAP Internship Experience Program) — EN letter
   below.
2. **Working-student contract (Werkstudent)** — DE letter below; runs
   alongside the degree, which is the natural frame for it.

Live search: <https://jobs.sap.com/go/AI-Jobs/9154301/> — the 2026
Walldorf/Berlin postings ask for exactly this stack ("knowledge graphs,
vectorization, SAP Build, AI Core, GenAI Hub, Joule extensibility").

**Target teams, in order:**

| Team | Why them | Location |
|---|---|---|
| **BTP AI Core / Generative AI Hub** | The platform Tessera is designed-for and partially *ran on* (HANA `VECTOR_EMBEDDING`, ADR 0012/0015 seams, DEPLOYMENT runbook) | Walldorf, Berlin |
| **Joule Studio** | MCP shipped in Joule Studio (GA Dec 2025); Tessera is an MCP evidence layer with a recorded session of Claude grounded through it | Walldorf |
| **Business AI research (KG / tabular)** | SALT-KG (arXiv 2601.07638, SAP authors) finds models "can't leverage relational semantics" — Tessera's exact thesis, built and measured; synthetic-on-SALT-schema since Phase 1 | Walldorf / Berlin |
| **Prior Labs** (long shot) | Frontier tabular lab (SAP acquisition, May 2026); the entity-resolution + tabular-grounding layer is the overlap | Freiburg / Berlin |

## The one-line pitch (use everywhere, verbatim)

> **SAP asserts trust at platform level; Tessera measures it at claim
> level — and gates action on it.**

## The Sapphire-2026 mapping (their words → the measured thing)

| SAP's 2026 vocabulary | Tessera's measured counterpart |
|---|---|
| "Relevant, reliable, responsible" (Sapphire 2026) | Grounded (claim-level provenance) · measured (CI-gated faithfulness floor, benchmark) · accountable (approval-gated actions with receipts) |
| **Agent Hub "verification badges"** (LeanIX, Q3 2026) | A *measured* per-claim faithfulness score a badge could actually carry — asserted trust vs measured trust is the asymmetry to name |
| **SAP + Anthropic: Claude "via MCP"** (Sapphire 2026) | Tessera is MCP-native; `data/agent_session/` is a real Claude agent grounded *only* through its seven tools — citing, refusing, action-gated |
| **SAP Knowledge Graph** (in Business AI Platform) | An explainable, reversible KG with per-merge confidences; HANA Cloud KG-engine persistence built behind a contract-tested seam (spec 0129 — the free tier gates the store itself; the recorded run awaits a paid-tier instance) |
| **SALT / SALT-KG** | Synthetic corpus on SALT's real schema since Phase 1 (drop-in for real SALT, access pending); SALT-KG's finding *is* the thesis |
| **HANA Cloud** | Two recorded online closes: in-database `VECTOR_EMBEDDING` + `COSINE_SIMILARITY` took gha coverage 0.833 → 1.000 and devex 0.950 → 1.000 (`eval/history.jsonl`) |
| **DSAG 2026: 77% run non-SAP AI, only 3% use SAP's own** | The German-audience hook: trust must be earned, not asserted — and here is a system that earns it with numbers |

## Artifacts to link, in this order

1. Live demo (no signup): <https://robert-vetter-tessera.hf.space>
2. The repo: <https://github.com/robert-vetter/tessera>
3. The benchmark ("The Faithfulness Floor," CI-pinned):
   [docs/BENCHMARK.md](../../docs/BENCHMARK.md)
4. The write-up (architecture + earned-numbers trail):
   [docs/WRITEUP.md](../../docs/WRITEUP.md)
5. The recorded Claude-over-MCP session:
   [data/agent_session/TRANSCRIPT.md](../../data/agent_session/TRANSCRIPT.md)

## CV bullets (numbers current 2026-07-03; refresh before sending)

- Built and shipped **Tessera**, an open-source evidence layer for AI
  agents (MIT): claim-level provenance over structured + unstructured
  enterprise data, principled refusals, approval-gated actions with
  execution receipts — live demo, MCP-native.
- **Trust as a number:** deterministic faithfulness verifier with a
  CI-gated 1.0 floor across three eval batteries (145+ PRs, 557 tests);
  published a reproducible gated-vs-ungated benchmark (no LLM judge).
- **Ran on SAP:** closed two recorded retrieval/ER misses with HANA
  Cloud in-database embeddings (`VECTOR_EMBEDDING`, 0.833→1.000 /
  0.950→1.000); knowledge-graph persistence for HANA's KG engine
  (RDF/SPARQL) built behind a tested seam.
- Solo, in ~5 weeks, alongside a founding-engineer role (Certus, YC S25)
  and a degree — spec-first units, adversarially reviewed, every number
  auditable in-repo.

## Cover letter — EN (iXp)

> Dear {team} team,
>
> SAP has supported my studies once already — through the SAP-sponsored
> Deutschlandstipendium — and I'd like to return the favor with working
> code. Over the last five weeks I built, in public, the thing your 2026
> postings describe: a knowledge-graph-grounded answer and action layer
> for enterprise AI agents, measured instead of asserted. Every claim
> carries provenance to exact source records; what can't be proven is
> refused; actions execute only behind approval and leave receipts; and
> faithfulness is a hard 1.0 floor in CI — with a reproducible benchmark
> showing what removing the gate costs.
>
> It already runs on SAP technology where the tier allows: HANA Cloud
> in-database embeddings closed two recorded retrieval misses
> (0.833→1.000, 0.950→1.000, `eval/history.jsonl`), and the knowledge
> graph ships a contract-tested RDF/SPARQL mirror for HANA's KG engine.
> The corpus is synthetic on SALT's real schema, ready to swap in the
> real dataset. It speaks MCP — the
> protocol SAP chose for Claude in the Business AI Platform — and there
> is a recorded session of a Claude agent answering only through it.
>
> I'd like to bring exactly this to {team}: {one sentence tying to the
> posting's named responsibility}. Live demo:
> https://robert-vetter-tessera.hf.space — repo, benchmark, and write-up
> linked from there. I'm based in {city}, available from {date},
> currently a founding engineer at Certus (YC S25) alongside my degree.
>
> Robert Vetter

## Cover letter — DE (Werkstudent)

> Sehr geehrtes {team}-Team,
>
> SAP hat mein Studium bereits einmal unterstützt — über das
> SAP-geförderte Deutschlandstipendium — und ich möchte mich mit
> funktionierendem Code revanchieren. In den letzten fünf Wochen habe
> ich öffentlich gebaut, was Ihre 2026-Ausschreibungen beschreiben: eine Knowledge-Graph-gestützte
> Antwort- und Aktionsschicht für Enterprise-KI-Agenten — gemessen statt
> behauptet. Jede Aussage trägt Provenance bis zu den Quell-Datensätzen;
> was sich nicht belegen lässt, wird verweigert; Aktionen laufen nur
> über Freigaben und hinterlassen Receipts; und die Faithfulness ist ein
> harter 1.0-Grenzwert in CI — inklusive eines reproduzierbaren
> Benchmarks, der zeigt, was der Verzicht auf das Evidence-Gate kostet.
>
> Es läuft bereits auf SAP-Technologie, wo die Tier-Stufe es erlaubt:
> HANA Cloud In-Database-Embeddings (`VECTOR_EMBEDDING`) schlossen zwei
> dokumentierte Retrieval-Lücken (0.833→1.000, 0.950→1.000), und der
> Knowledge Graph bringt einen contract-getesteten RDF/SPARQL-Mirror
> für die HANA KG-Engine mit. Das Korpus ist synthetisch auf dem echten
> SALT-Schema — bereit für den Austausch gegen den realen Datensatz. Die Schnittstelle ist MCP, das
> Protokoll, das SAP für Claude in der Business AI Platform gewählt hat.
>
> Als Werkstudent bei {team} würde ich genau daran arbeiten:
> {ein Satz zur ausgeschriebenen Aufgabe}. Live-Demo:
> https://robert-vetter-tessera.hf.space — Repo, Benchmark und Write-up
> sind dort verlinkt. Ich studiere {Studiengang, Uni, Semester}, bin
> Founding Engineer bei Certus (YC S25) und ab {Datum} verfügbar.
>
> Mit freundlichen Grüßen
> Robert Vetter

## Submission checklist (the evening it goes out)

1. Re-run `uv run tessera-benchmark` + `uv run tessera-eval`; refresh
   any number quoted above.
2. Warm the demo Space (sleeps after ~48h idle).
3. Fill `{placeholders}` from the specific posting; one sentence per
   letter must name *their* stated responsibility.
4. Apply to **both** tracks; note req IDs + dates in a local file (not
   committed).
5. If a paid-tier instance has run the KG one-shot by then (spec 0129
   runbook — the free tier gates the Triple Store), upgrade the KG line
   with the recorded measurement.
