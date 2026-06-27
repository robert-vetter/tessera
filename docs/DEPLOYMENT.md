# Deployment — SAP AI Core, Generative AI Hub, HANA Cloud

How Tessera runs on SAP's AI infrastructure — and why, on a fresh clone, it
deliberately doesn't.

**The honest one-liner:** Tessera is *designed to run on* SAP AI Core /
Generative AI Hub (models) and SAP HANA Cloud (graph/vector), **with a
portable local mode as the default**. This page is the deployment design and
runbook; nothing in this repository requires a cloud account, a key, or a
network connection (spec 0039 / ADR 0012 record the decision to ship the
path as documentation + tested code seams, not a provisioned footprint).

---

## The component → service mapping

| Tessera component | Local mode (default) | SAP target | Status |
|---|---|---|---|
| Narration model (rephrases verifier-checked claims; never generates facts — ADR 0006 trigger 2) | none — deterministic rendering | **Generative AI Hub** deployment on **AI Core** | Adapter implemented (`tessera/platform/providers.py`), exercised against fakes in CI; needs a provisioned deployment to go live |
| Embedding / semantic retrieval | none — lexical BM25 (ADR 0003) | GenAI Hub embeddings + **HANA Cloud vector store** | **Deliberately not built.** ADR 0010 refreshed the trigger: embeddings arrive when a measured coverage miss exists that no declarable data can fix |
| Knowledge graph | in-process object model (ADR 0004) | **HANA Cloud** graph workload | Documented design target; the graph is rebuilt deterministically from data on each run, so persistence is an optimization, not a correctness need, at current scale |
| Serving / runtime | `uv run …` or the repository Dockerfile | **AI Core** serving (or any BTP runtime) the container deploys to | The container is the deployable artifact |
| Platform context | — | **SAP BTP** subaccount | Provisioning runbook below |

Two principles govern every row (CLAUDE.md):

1. **Clone-and-run first.** The default configuration uses no cloud service.
   CI runs the entire gate and eval key-free; so can you.
2. **The cloud is configuration, not a rewrite.** Opting in means setting
   environment variables, not changing code.

## Configuration reference

All platform behaviour is controlled by environment variables, read once by
`tessera.platform.config.load_config()`:

| Variable | Meaning | Default |
|---|---|---|
| `TESSERA_NARRATOR` | `none`, `genai-hub`, or `anthropic` | `none` (local mode) |
| `AICORE_AUTH_URL` | XSUAA OAuth2 URL of the AI Core service key | — |
| `AICORE_CLIENT_ID` / `AICORE_CLIENT_SECRET` | OAuth2 client credentials | — |
| `AICORE_BASE_URL` | AI Core API URL (`…ml.hana.ondemand.com`) | — |
| `AICORE_RESOURCE_GROUP` | AI Core resource group | `default` |
| `TESSERA_GENAI_DEPLOYMENT` | GenAI Hub deployment id to call | — |
| `ANTHROPIC_API_KEY` | Anthropic key (the locally demoable fallback) | — |
| `TESSERA_ANTHROPIC_MODEL` | Anthropic model for narration | `claude-haiku-4-5-20251001` |
| `TESSERA_EMBEDDINGS` | `none`, `hana` (in-DB, recorded), or `genai-hub` (alternative) — semantic retrieval (ADR 0015) | `none` (lexical) |
| `HANA_HOST` / `HANA_PORT` | HANA Cloud SQL endpoint (port `443`) | — / `443` |
| `HANA_USER` / `HANA_PASSWORD` | HANA Cloud credentials (use a least-privilege app user, not `DBADMIN`) | — |
| `HANA_DATABASE` | schema that qualifies the vector table | — |
| `HANA_EMBEDDING_MODEL` | in-DB `VECTOR_EMBEDDING` model — **requires the NLP feature enabled** | `SAP_NEB.20240715` |
| `TESSERA_GENAI_EMBEDDING_DEPLOYMENT` | GenAI Hub **embedding** deployment id (alternative path) | — |
| `TESSERA_GENAI_EMBEDDING_PATH` | GenAI Hub inference suffix (`embeddings` / `v1/embeddings`) | `embeddings` |

A misspelled `TESSERA_NARRATOR` fails loudly at startup; a half-configured
provider fails at construction with the missing variable names — never
mid-answer.

**Why an Anthropic fallback?** So narration is demoable on a laptop today
(maintainer decision, spec 0035) with the exact same protocol surface the
GenAI Hub adapter uses. Selecting it is as explicit as selecting GenAI Hub.

## Provisioning runbook (when the time comes)

The steps a BTP admin would follow — written down so going live is an
afternoon, not a research project:

1. **BTP subaccount** (free tier suffices to start): create or reuse one,
   enable Cloud Foundry or Kyma as preferred.
2. **SAP AI Core instance**: subscribe in the subaccount, create a service
   instance + **service key**. The key's JSON carries `url` (→
   `AICORE_AUTH_URL`), `clientid`, `clientsecret`, and `serviceurls.AI_API_URL`
   (→ `AICORE_BASE_URL`).
3. **Resource group**: create one (e.g. `tessera`) via the AI Core API or
   SAP AI Launchpad → `AICORE_RESOURCE_GROUP`.
4. **Generative AI Hub deployment**: in AI Launchpad (or via API), create a
   deployment for a chat-capable foundation model from the model library.
   Note its deployment id → `TESSERA_GENAI_DEPLOYMENT`.
5. **Smoke test**: `TESSERA_NARRATOR=genai-hub` plus the five variables
   above; ask `uv run tessera` a question and confirm the narration line
   appears (claims and provenance are identical with or without it).
6. **HANA Cloud (later, with a measured need — ADR 0010)**: provision a HANA
   Cloud instance in the same subaccount; the graph's persistence and the
   vector store land behind the same configuration discipline.
7. **Serving (optional)**: build the repository's Docker image and deploy it
   to the chosen BTP runtime; the container needs only the variables above.

## What is verified, and what is not — honestly

- **Verified in CI, key-free:** the full engine, both verticals, the eval
  floor; the platform seam's request contracts (URLs, auth headers, payload
  shapes) and failure degradation, against a fake transport
  (`tests/test_platform.py`).
- **Not verified here:** an end-to-end call against a real GenAI Hub
  deployment or the Anthropic API — that requires credentials this
  repository deliberately ships without. The adapters target SAP AI Core's
  `/v2/inference/deployments/{id}/chat/completions` shape and Anthropic's
  Messages API (`2023-06-01`); if either drifts, the adapter is one small,
  visible module per provider.

This split is the point: everything trust-bearing is reproducible by anyone;
everything cloud-bearing is documented, isolated, and optional.
