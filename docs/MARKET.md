# Market Snapshot — 2026-07-02

**What this is.** A dated snapshot of the market, regulatory, and program landscape
Tessera operates in, compiled 2026-07-02 via agent-assisted web research to ground
the [Act 2 roadmap](ROADMAP2.md). Load-bearing claims carry links. Three
strategy-critical claims were independently re-verified against primary sources
(marked ✓). Treat everything else as researched-but-single-pass: re-verify before
quoting externally. This document records *why* Act 2 points where it points; it is
not marketing copy.

---

## 1. The gap

The combination Tessera already implements has, as of this snapshot, **no credible
occupant**:

1. **Per-claim grounding** in cross-source enterprise evidence (structured +
   unstructured, entity-resolved), with a provenance path per claim;
2. **Evidence-gated agent actions** — a payload may execute only when every value
   traces to a verifier-passing claim — behind approval, with execution
   **receipts**;
3. A **self-shipped, auditable faithfulness benchmark** with a CI-gated floor,
   **no LLM judge** in the loop;
4. **Deterministic / on-prem capable** — no model vendor inside the trust path.

Each *piece* exists somewhere: per-claim scoring (Google
[Vertex Check Grounding](https://docs.cloud.google.com/generative-ai-app-builder/docs/builder-apis)),
model-emitted citations (Anthropic Citations API,
[Jan 2025](https://techcrunch.com/2025/01/23/anthropics-new-citations-feature-aims-to-reduce-ai-errors/)),
formal output verification against *authored policies* (AWS
[Automated Reasoning checks](https://aws.amazon.com/about-aws/whats-new/2025/08/automated-reasoning-checks-amazon-bedrock-guardrails/),
GA Aug 2025), refusal-first KG answering (Stardog
[Voicebox "Safety RAG"](https://siliconangle.com/2025/09/03/stardogs-hallucination-free-answer-engine-brings-ai-insights-high-stakes-industries/)),
ER-grounded copilots ([Quantexa Q Assist](https://www.quantexa.com/press/quantexa-makes-its-decision-intelligence-platform-agent-ready/)),
action approval as API ([HumanLayer](https://github.com/humanlayer/12-factor-agents)),
signed audit trails ([Asqav](https://www.asqav.com/blog/posts/eu-ai-act-audit-trail-requirements),
MintMCP), hallucination benchmarks
([Vectara leaderboard](https://github.com/vectara/hallucination-leaderboard)).

**The structural reason the conjunction is empty:** grounding vendors have no
action layer; action/gateway vendors have no evidence layer; and almost everyone
puts an LLM (judge or generator) inside the trust path, which forfeits determinism
and the on-prem story.

**Closest competitors and what they lack:**

| Player | Has | Lacks |
|---|---|---|
| **Palantir AIP** ([citations](https://www.palantir.com/docs/foundry/agent-studio/citations), approval-gated Actions, audit trail, Evals) | The most complete incumbent combo | Openness/portability; deterministic non-LLM verification; published gated faithfulness numbers; explainable/reversible ER as a primitive. Will not become OSS, cheap, or vendor-neutral — that is the wedge against it. |
| **AWS Bedrock stack** (AR checks + Citations + Guardrails + [AgentCore Gateway](https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/)) | All four themes as *separate services* | Cross-source ER/KG over customer records; evidence-entailment gating (AgentCore gates on IAM/OAuth); any composed trust path; constitutionally cloud-tied. |
| **Quantexa** ([agent-ready platform, Nov 2025](https://www.quantexa.com/press/quantexa-makes-its-decision-intelligence-platform-agent-ready/)) | ER-grounded Q&A, "fully auditable" positioning | Claim-level verifier and refusal contract; self-published benchmark; MCP-exposed action gating with receipts; closed, enterprise-priced, investigation-vertical. |

Notable adjacent signals: every MCP **gateway** (13+ vendors compared in
[2026](https://obot.ai/blog/the-13-best-mcp-gateways-for-enterprise-teams/)) gates
on identity/permission/policy — none on evidence. "Receipts" exist only as logs or
signatures (Asqav, Nobulex, a proposed
[`langchain-receipts`](https://github.com/langchain-ai/langchain/issues/34484)),
never as proofs linking action → claims → evidence. A deterministic, CI-gated
faithfulness floor is argued for in essays
([futureagi, 2026](https://futureagi.com/blog/deterministic-llm-evaluation-metrics-2026/))
but shipped by no one. OpenAI deprecated its hosted Agent Builder/Evals
([June 2026](https://community.openai.com/t/deprecation-notice-agent-builder/1382650)),
strengthening the case for neutral OSS eval infrastructure.

## 2. Landscape by cluster (compressed)

1. **Hallucination detection / grounding** — Vectara (HHEM, Hallucination
   Corrector), Patronus (Lynx), Cleanlab (TLM), Anthropic Citations, AWS AR
   checks, Vertex Check Grounding, Contextual AI, Aleph Alpha (post-turmoil).
   All verify *response-vs-context*; none chain per-claim verification through
   entity-resolved cross-source records; the "formal" ones need authored policies
   or are themselves models.
2. **Eval & observability** — LangSmith, Langfuse (acquired by ClickHouse,
   [Jan 2026](https://clickhouse.com/blog/clickhouse-raises-400-million-series-d-acquires-langfuse-launches-postgres)),
   Braintrust, Arize, Galileo (acquired by Cisco,
   [Apr–May 2026](https://blogs.cisco.com/news/cisco-announces-the-intent-to-acquire-galileo)),
   Weave, Ragas/DeepEval/Giskard. Center of gravity is post-hoc tracing +
   LLM-as-judge scoring; consolidating into infra giants. Gartner's Galileo take
   is literally titled "…Exposes AI Trust Gaps in Observability".
3. **Guardrails / AI firewalls** — NeMo Guardrails, Guardrails AI, Lakera
   (→ Check Point, [~$300M](https://www.checkpoint.com/press-releases/check-point-acquires-lakera-to-deliver-end-to-end-ai-security-for-enterprises/)),
   Robust Intelligence (→ Cisco), Invariant (→ Snyk), Prompt Security
   (→ SentinelOne), Zenity, Noma
   ([$100M B](https://noma.security/blog/noma-security-raises-100m-to-drive-adoption-of-ai-agent-security/)).
   Threat + policy layer; a perfectly "safe" hallucination passes every one of
   them. This cluster is a consolidation magnet — CISO budgets, not trust
   substance.
4. **Action governance / approvals** — HumanLayer (12-factor agents, 19.3k
   stars), gotoHuman, Permit.io, Composio, MCP gateways (Lasso, MintMCP, Obot,
   Microsoft toolkit), AWS AgentCore. Permission-based, never evidence-based.
5. **Enterprise RAG/KG with provenance** — Glean
   ([$7.2B, Jun 2025](https://techcrunch.com/2025/06/10/enterprise-ai-startup-glean-lands-a-7-2b-valuation/)),
   Palantir AIP, Stardog Voicebox, Microsoft GraphRAG/LazyGraphRAG, Writer,
   Neo4j, Graphwise. Citation *display* (document/chunk level, model-generated);
   nobody publishes a faithfulness number they gate releases on; refusal is not
   a first-class measured behavior (Stardog asserts it, without a public
   harness).
6. **Entity resolution** — Senzing (markets
   [ER-KGs for GraphRAG grounding](https://senzing.com/knowledge-graph/)),
   Quantexa, Tilores, AWS ER. Only Quantexa ties ER into grounded generation —
   closed. Nobody exposes deterministic, reversible, explainable ER + per-claim
   provenance to third-party agents over MCP; none OSS.
7. **AI governance / compliance** — Credo, Holistic, watsonx.governance,
   OneTrust, Vanta/Drata. Paper compliance (registries, assessments); runtime
   enforcement is not what they do; where "runtime" appears it is policy/drift
   monitoring on top of other vendors' guardrails.

## 3. Regulatory (EU AI Act, verified mid-2026)

- GPAI obligations apply since **Aug 2, 2025**; Commission enforcement powers
  from Aug 2, 2026
  ([Latham](https://www.lw.com/en/insights/eu-ai-act-gpai-model-obligations-in-force-and-final-gpai-code-of-practice-in-place)).
- ✓ **The Aug 2026 high-risk deadline moved.** The Digital Omnibus (agreement
  May–June 2026) defers standalone **Annex III high-risk obligations —
  including Art. 12 logging, Art. 14 human oversight, Art. 26 deployer duties —
  to Dec 2, 2027**
  ([Gibson Dunn](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/),
  re-verified 2026-07-02; formal publication in the Official Journal expected
  before Aug 2, 2026). Art. 50 transparency obligations still bite **Aug 2,
  2026**.
- **Implication:** deadline-panic positioning is stale; "audit-ready by design"
  (receipts ↔ Art. 12 record-keeping, approval ↔ Art. 14 oversight) stays a
  documentation-level tailwind and strengthens again toward Dec 2027. Compliance
  budgets flow to GRC incumbents; runtime evidence infrastructure is bought by
  engineering.

## 4. Demand evidence (selected)

- Gartner: **>40% of agentic-AI projects will be canceled by 2027**, "inadequate
  risk controls" among the top reasons
  ([press release, Jun 2025](https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027));
  PwC: only **20%** of leaders trust agents with financial transactions
  ([survey](https://www.pwc.com/us/en/tech-effect/ai-analytics/ai-agent-survey.html)).
- LangChain State of Agent Engineering (n=1,340, Dec 2025): **quality is the #1
  production blocker (33%)**; at 2k+ employee orgs security is #2; 10k+ orgs
  name hallucinations/consistency as the top quality challenge
  ([langchain.com](https://www.langchain.com/state-of-agent-engineering)).
- The **Replit incident** (agent deleted a production DB during a code freeze,
  fabricated data, misreported rollback —
  [Fortune, Jul 2025](https://fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure/))
  is the canonical anchor story; the industry's own post-mortem consensus
  (dry-runs, approval gates, blast-radius previews, draft-only credentials) *is*
  Tessera's action model.
- MCP security incidents through 2025 (GitHub MCP exfiltration, Supabase ticket
  injection, postmark-mcp backdoor —
  [roundup](https://www.upguard.com/blog/mcp-security-incidents)) keep agent
  trust in the news.
- Practitioner vocabulary when asking for this: *guardrails, approval, audit
  trail, human-in-the-loop, receipts, blast radius* — not "trust layer"
  (e.g. [SudoAgent Show HN](https://news.ycombinator.com/item?id=46733891)).
  Academic vocabulary is converging on receipts:
  ["Tool Receipts, Not Zero-Knowledge Proofs"](https://arxiv.org/pdf/2603.10060).

## 5. ICP and traction motion

**Primary ICP: DACH agent-delivery consultancies** — SAP partners and AI
agencies building agents *for clients* (often regulated). They feel the pain on
every engagement, must hand a client an audit story, are reachable in German by
a solo founder, decide in days, and one consultancy = many end clients.
**Secondary ICP: MCP-adopting platform teams** — converts as OSS adoption
(stars, issues, users): the visible-traction engine.

Named, public examples (champions: Head of Data & AI / AI Practice Lead / BTP
Practice Lead / Head of AI Engineering):

- SAP partners publicly building Joule/BTP agents (Hack2Build Agent Builder,
  [SAP blog, Jan 2026](https://community.sap.com/t5/technology-blog-posts-by-sap/partner-driven-innovation-takes-off-with-agent-builder-in-joule-studio/ba-p/14318557)):
  All for One Group, cbs, NTT Data Business Solutions, Talan, Avvale,
  LTIMindtree, Capgemini, DXC, KPMG. Plus adesso, valantic, msg systems,
  Nagarro, Westernacher, Camelot ITLab, Convista, mindsquare, Scheer.
- AI consultancies with public agentic offerings: statworx, Alexander Thamm,
  ML6, appliedAI network; n8n delivery agencies (n8n Lab Berlin, WemakeFuture,
  innFactory).
- MCP/platform: Deutsche Telekom (agent program
  [with n8n](https://www.telekom.com/en/media/media-information/archive/agentic-ai-deutsche-telekom-partners-with-startup-n8n-1095912)),
  n8n, remote-MCP publishers (Block, Atlassian, Cloudflare, Sentry, Stripe).

**Where they congregate (Aug–Oct 2026, DE/EU):** WeAreDevelopers World Congress
Berlin (Jul 8–10), AI Tinkerers Berlin/Munich (monthly, demo-first), AIDAQ
Berlin (Sep 22–23), Enterprise AI Summit Berlin (Sep 28–29), **DSAG
Jahreskongress Cologne (Oct 6–8)**, data2day Cologne (Oct 7–8); online:
r/LLMDevs, HN, MLOps Slack, MCP Discord, SAP Community.

**Playbook evidence:** Langfuse/Helicone/Infisical pattern — narrow wedge named
in practitioner language + OSS repo + Show HN + niche write-ups + hand-holding
the first 5–10 users ([Langfuse story](https://langfuse.com/handbook/chapters/story),
[Helicone Launch HN](https://news.ycombinator.com/item?id=35279155)).
Table-stakes assets: <5-min quickstart, 2–3-min demo video, benchmark/architecture
post. Cold outreach math: ~150 personalized founder-level messages → 8–15 replies
→ 5–8 calls → **1–3 pilots**; >50% of replies come from follow-ups
([benchmarks](https://thedigitalbloom.com/learn/cold-outbound-reply-rate-benchmarks/)).
Realistic 4-week success: 2–3 unpaid design partners + a few hundred stars +
5–10 real OSS users. Not revenue.

**Positioning (practitioners' words, not ours):**

- Sharpest general one-liner: **"The agent can only say what it can prove — and
  only do what you approve."**
- Consultancies: **"Hand your client an audit trail, not a demo"** — every claim
  traced to source records, every action behind an approval with a receipt; OSS,
  on-prem, no model-vendor lock-in.
- MCP/platform: **"the evidence layer for MCP agents"** — gateways log *that* a
  tool was called; Tessera proves *why* it was allowed to. (Avoid the crowded
  "MCP gateway" label.)
- Avoid: "hallucination-free" (overclaim), "trust layer" as headline (fine as
  category descriptor), EU-AI-Act deadline panic (stale until ~2027).

## 6. Z Fellows (verified)

✓ **Format:** a **one-week experience**, ~10 builders, mostly virtual, last day
in-person SF/NYC; optional **$10k at a $1B valuation cap**; rolling cohorts
([zfellows.com](https://www.zfellows.com/), re-verified 2026-07-02). No public
investor demo day exists; each fellow presents their project once, in-cohort,
to peers + guest founders (alumni accounts:
[Agarwal](https://www.itsharshag.com/blog/my-zfellows-experience),
[Debow interview](https://www.boringbusinessnerd.com/post/inside-z-fellows-with-ali-debow)).
The real prizes: Cory Levy's **$100k follow-on** into pre-seed rounds
([TechCrunch, Oct 2025](https://techcrunch.com/2025/10/18/this-top-vc-bet-close-to-20-of-his-fund-on-teenagers-heres-why/))
and the 500+ alumni Slack with investor intros.

**What they celebrate:** working artifacts + committed customers (Etched:
working chip + signed contracts; Aaru: Accenture/EY as customers —
[TechCrunch, Dec 2025](https://techcrunch.com/2025/12/05/ai-synthetic-research-startup-aaru-raised-a-series-a-at-a-1b-headline-valuation/)),
execution speed, storytelling (their blog canon: Do Things That Don't Scale,
Dorsey on storytelling). Selection is founder-first ("ambitious, talented,
driven, and kind").

**Implication:** the audience is generalist-SV, not enterprise buyers. Lead with
a live, fast, undeniable demo (grounded answer → refusal → gated action →
receipt); keep SAP alignment for Q&A. The legible 4-week evidence, in
descending order: public launch traction (Show HN / X / stars) → 2–3 named
design partners → a benchmark artifact others cite → revenue (not expected).
Frame as a one-axis outlier: *the only agent layer where every claim is
auditable and every action is approval-gated — and we measure it.*

**Delivered 2026-07-18 (spec 0146):** item 3 on that list — "a benchmark
artifact others cite" — now exists as
[the Verification Gap](CONFORMANCE.md): the published verification methods
of 2026, faithfully re-implemented and graded against 21 attacks under two
threat models, reproducible in one offline command, including the cells
Tessera loses. It is the item on the list that does not depend on anyone
else's attention.

## 7. SAP (verified where marked)

- ✓ **Sapphire 2026 (May 12):** "Autonomous Enterprise" — SAP Business AI
  Platform (BTP + Business Data Cloud + Business AI), **SAP Knowledge Graph**
  inside it, 50+ Joule Assistants orchestrating 200+ agents; **SAP + Anthropic:
  Claude as "a primary reasoning and agentic capability … via MCP"**
  ([news.sap.com](https://news.sap.com/2026/05/sap-anthropic-to-bring-claude-sap-business-ai-platform/),
  re-verified 2026-07-02).
- **MCP + A2A shipped:** MCP in Joule Studio (GA Dec 2025), MCP for HANA Cloud,
  MCP Gateway in Integration Suite, A2A support
  ([news.sap.com, Nov 2025](https://news.sap.com/2025/11/new-agentic-capabilities-sap-btp-supercharge-developers/)).
  Tessera's MCP surface speaks SAP's chosen protocol.
- **SAP AI Agent Hub** (in LeanIX, GA target Q3 2026): "command center for
  enterprise-grade AI governance", "verification badges", "risk rating and
  compliance mappings", runtime observability
  ([SAP Community, May 2026](https://community.sap.com/t5/technology-blog-posts-by-sap/introducing-sap-ai-agent-hub-your-command-center-for-enterprise-grade-ai/ba-p/14393693)).
  **SAP's trust story is asserted (badges, ISO processes), not measured — no
  published per-claim provenance or faithfulness metric for Joule agents.**
  That asymmetry is Tessera's positioning: *SAP asserts trust at platform
  level; Tessera measures it at claim level — and gates action on it.*
- **DSAG Investitionsreport 2026:** 43% have AI use cases, but of those **77%
  run non-SAP AI in production and only 3% use SAP's own AI**
  ([dsag.de](https://dsag.de/presse/dsag-investitionsreport-2026-unternehmen-investieren-gezielter-ki-etabliert-sich-cloud-auf-dem-prufstand/)) —
  the "why trust must be earned, not asserted" hook for a German audience.
- **Research hooks:** SALT (real ERP dataset,
  [SAP News, Apr 2025](https://news.sap.com/2025/04/sap-salt-real-erp-dataset-enterprise-ai-research/));
  **SALT-KG** ([arXiv 2601.07638](https://arxiv.org/html/2601.07638v1), Jan
  2026, SAP authors): models show "gaps in [their] ability to leverage
  semantics in relational context" — Tessera's exact thesis; ConTextTab /
  SAP-RPT-1; **Prior Labs acquisition** (>€1B, frontier tabular lab,
  [May 2026](https://news.sap.com/2026/05/sap-to-acquire-prior-labs-establish-frontier-ai-lab-europe/)).
  HANA Cloud **knowledge graph engine GA** since QRC1 2025 (RDF/SPARQL).
- **Internship reality:** iXp internships and working-student contracts are
  separate tracks in Germany — apply to both. Live Walldorf/Berlin postings ask
  for exactly this stack: "knowledge graphs, vectorization, SAP Build, AI Core,
  GenAI Hub, Joule extensibility"
  ([jobs.sap.com](https://jobs.sap.com/go/AI-Jobs/9154301/)). Target teams: BTP
  AI Core / Generative AI Hub (Walldorf, Berlin), Joule Studio, Business AI
  research (KG/tabular), Prior Labs (Freiburg/Berlin) as the long shot.
- **Ecosystem channel:** AI Agent Hub marketplace (Q3 2026, 680+ partner agent
  submissions pre-launch, €100M partner fund) — the partner ecosystem that
  builds agents is the same one named under ICP above.

## 8. Bottom line

Sell the **receipt**, not the philosophy. Lead with **evidence-gated execution
+ receipts demoed over MCP** (wedge 1), prove it with the **deterministic
faithfulness benchmark** (wedge 2), keep **EU-AI-Act mapping** at
documentation level (wedge 3). Primary buyers to court in 4 weeks: DACH
agent-delivery consultancies; OSS/MCP developers as the traction engine. For
SAP, the same story told in Sapphire-2026 vocabulary, plus SALT/HANA-KG/BTP
proof points. For Z Fellows, one live demo and visible velocity.

## 9. Prior art on receipt verification (primary sources, read 2026-07-18)

Read in full for spec 0146; each is implemented as a graded method in
[CONFORMANCE.md](CONFORMANCE.md).

- **IETF, "Compliance Profile of Signed Action Receipts for AI Agents"**
  (ASQAV draft, 2026) — receipts bound to EU AI Act obligations (Art. 12
  record-keeping, Art. 26 deployer duties) and DORA; verification is
  canonicalize → SHA-256 → Ed25519, checkable offline
  ([datatracker](https://datatracker.ietf.org/doc/draft-marques-asqav-compliance-receipts/)).
- **Microsoft Agent Governance Toolkit, "Independently Verifiable
  Compliance Receipts"** — a deliberately bounded model of three checks:
  signature validity, chain integrity (`previousReceiptHash`), and policy
  binding (`covenantHash`). Its own text states the verifier confirms the
  decision was *signed consistently*, not that it was correct
  ([proposal](https://microsoft.github.io/agent-governance-toolkit/proposals/verifiable-compliance-receipts/)).
- **"Proof of Execution: Runtime Verification for Governed AI Agent
  Actions"**, Rhodes & Kang, Apr 2026
  ([arXiv:2607.05397](https://arxiv.org/abs/2607.05397)) — the closest
  adjacent work: execution as a proof-carrying object (contract, causal
  event stream, replay context) with five validator invariants the paper
  calls syntactic predicates; envelope closure is scoped to the
  *declared* envelope, undeclared dependencies are explicitly outside it,
  and deterministic replay is a guarantee under stated deployment
  assumptions. **Complementary, not overlapping:** it verifies that an
  action was authorized, in scope, recorded and replayable; Tessera
  verifies that the claims in an answer follow from the evidence cited.

**Consequence for positioning:** keep the claim on its own axis
(claim-vs-evidence re-execution), credit the adjacent work by name, and
let the benchmark — including the cell Tessera loses — carry the
comparison. Overclaiming here would be both wrong and unnecessary.
