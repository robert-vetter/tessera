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

## Semantic retrieval on HANA Cloud — the recorded path (ADR 0015)

This is the path actually run and recorded for Milestone 6: HANA Cloud generates
the embeddings *in-database* (`VECTOR_EMBEDDING`) and stores/searches them with
its vector engine — one SAP service, no GenAI Hub. It closes the error-class
synonymy miss (`github_actions` gold coverage 0.833 → 1.000).

1. **HANA Cloud instance**: provision in the subaccount. The vector engine
   (`REAL_VECTOR`, `COSINE_SIMILARITY`) is **core** — no NLP/PAL/data-lake needed
   for storage. The SQL endpoint is host `:443`.
2. **Enable the NLP feature**: edit the instance → *Additional Features* →
   **Natural Language Processing** → save (it restarts). This turns on the
   in-database `VECTOR_EMBEDDING()` function. (It adds memory/licensing cost; it
   is a reversible toggle.)
3. **Dedicated least-privilege app user** (do not connect as `DBADMIN`):
   ```sql
   CREATE USER TESSERA_APP PASSWORD "<strong-password>" NO FORCE_FIRST_PASSWORD_CHANGE;
   CREATE SCHEMA TESSERA OWNED BY TESSERA_APP;
   -- The owner can DDL/DML in its own schema; VECTOR_EMBEDDING and
   -- COSINE_SIMILARITY are built-ins needing no extra grant. If a call returns
   -- an insufficient-privilege error, grant the instance's documented
   -- NLP/embedding usage privilege to TESSERA_APP and retry.
   ```
   Then set `HANA_USER=TESSERA_APP`, `HANA_PASSWORD=…`, `HANA_DATABASE=TESSERA`.
4. **Install the optional driver**: `uv sync --extra cloud` (pulls `hdbcli`; the
   default install stays pure-stdlib).
5. **Smoke test** (confirm the feature + the model version before spending a
   real run):
   ```sql
   SELECT VECTOR_EMBEDDING('hello world', 'QUERY', 'SAP_NEB.20240715') FROM DUMMY;
   ```
   If the instance reports an unknown model, set `HANA_EMBEDDING_MODEL` to the
   version it offers.
6. **Record the close** (one shot, online):
   ```bash
   cp .env.example .env   # then fill in the HANA_* values
   set -a; source .env; set +a
   TESSERA_EMBEDDINGS=hana uv run tessera-eval --record \
     --note "M6 synonymy: online HANA-embedding close"
   ```
   The `github_actions` synonymy gold case closes; the point is appended to
   `eval/history.jsonl`. CI stays offline/lexical and key-free throughout.

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
- **HANA-native semantic retrieval (ADR 0015) — RAN ON SAP.** The SQL contract
  is verified offline against a fake connection (`tests/test_semantic.py`,
  `tests/test_vectors.py`), **and** the live path was actually run: HANA Cloud
  in-database `VECTOR_EMBEDDING` (`SAP_NEB.20240715`, 768-dim) + `COSINE_SIMILARITY`
  KNN closed the `github_actions` synonymy miss (gold coverage 0.833 → 1.000,
  quality 0.800 → 1.000, faithfulness 1.0), recorded in `eval/history.jsonl`
  (spec 0058). This is a **timestamped online measurement**, not a CI-reproducible
  one — CI stays offline on the lexical path; the cloud embedding model can change.

This split is the point: everything trust-bearing is reproducible by anyone;
everything cloud-bearing is documented, isolated, and optional.
