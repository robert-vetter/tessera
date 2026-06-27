# 0052. Embedding-provider seam — GenAI Hub embeddings, key-free and contract-tested

- **Phase / milestone:** Milestone 6 — Embeddings on SAP (Unit 2 of 8; plan 0051)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Milestone 6 acts on ADR 0010: real semantic embeddings, generated at SAP
Generative AI Hub, to close the measured, undeclarable error-class-synonymy miss
(spec 0051). Before any retrieval can use them, the engine needs a **seam** to
*ask a model for an embedding* — the exact analogue of the existing
`ModelProvider` chat seam (spec 0039), built the same way: a narrow protocol, a
GenAI Hub adapter that speaks plain stdlib HTTPS, and a fake-transport contract
test so CI verifies our side of the request without any provisioned service or
key. This unit builds that seam and only that seam — no retrieval wiring, no
HANA, no network.

## Acceptance criteria

- [ ] An `EmbeddingProvider` `Protocol` in `tessera/platform/providers.py`:
      `name: str` and `embed(texts: Sequence[str]) -> list[list[float]]` (batch —
      indexing embeds many records at once). Deliberately narrow, like
      `ModelProvider`.
- [ ] A `GenAIHubEmbeddingProvider` adapter: XSUAA OAuth2 client-credentials
      token (shared with the chat adapter via one extracted `_xsuaa_token`
      helper), then `POST {base}/v2/inference/deployments/{id}/{path}` with
      `{"input": [...]}` and the `AI-Resource-Group` header; parses
      `data[].embedding`, **returned in input order** (sorted by `index`). Any
      transport/protocol problem raises `ProviderError`.
- [ ] Config additions in `tessera/platform/config.py`: `TESSERA_EMBEDDINGS`
      selector (`none` | `genai-hub`, default `none`, unknown value fails loudly
      like `TESSERA_NARRATOR`); `TESSERA_GENAI_EMBEDDING_DEPLOYMENT` (the
      embedding deployment id); `TESSERA_GENAI_EMBEDDING_PATH` (default
      `embeddings`, overridable because the exact suffix — `embeddings` vs
      `v1/embeddings` — depends on the deployed model type; the one-shot spend run
      must not fail on a URL suffix).
- [ ] `embedding_provider_from_env(config, transport) -> EmbeddingProvider | None`:
      `None` in the default local mode (no transport touched); a half-configured
      `genai-hub` raises `ProviderError` naming the missing variable at
      construction, not mid-call.
- [ ] Contract tests (key-free, offline, fake transport): local-mode returns
      `None` without touching the transport; half-config fails loudly;
      token-then-embeddings request contract pinned (URL, `Bearer` token,
      `AI-Resource-Group`, `input` payload); out-of-order `data` is re-ordered to
      input order; a malformed response degrades to `ProviderError`.
- [ ] `docs/DEPLOYMENT.md` env table gains the three new variables (documentation
      tracks the config it describes; the provisioning *runbook* steps are U6).
- [ ] **ADR 0015** records the embeddings architecture and the crossing of
      ADR 0010's determinism line.

## Scope

**In:** the embedding provider protocol + GenAI Hub adapter; the `_xsuaa_token`
extraction (within `platform/`, not the frozen core); config + env wiring;
contract tests; the DEPLOYMENT env-table rows; ADR 0015; an ADR 0010 addendum
pointer.

**Out:** the vector store / HANA backend (U3); any retrieval or ER wiring that
*uses* embeddings (U4); the eval cases (U5); the provisioning runbook steps and
`.env.example` (U6); the live run (U7). No `hdbcli`, no network, no key in this
unit. Embeddings never touch the claim / faithfulness path — that boundary is
ADR 0015's core and is enforced from U4 on by a leak-guard test.

## Eval impact

None yet — this unit adds a seam exercised only by fake-transport unit tests.
All batteries stay 1.000; the gate's offline lexical path is untouched. (The
recall gain lands in U5/U7.)

## Risks / open questions

- **Exact GenAI Hub embeddings path/payload is unverified against live SAP**
  (the chat adapter is fake-tested only too). Mitigation: `TESSERA_GENAI_EMBEDDING_PATH`
  override + a documented U7 smoke test before the real eval run. The response
  parser keys on the stable `data[].embedding` shape both Azure- and
  OpenAI-style deployments share.
- **Refactor risk** from extracting `_xsuaa_token`: the existing chat
  `test_genai_hub_request_contract` pins the token-then-infer call order;
  the extraction must preserve it (same transport calls). Guarded by that test
  staying green unchanged.
- **Selector independence:** embeddings are gated by their own `TESSERA_EMBEDDINGS`,
  not by `TESSERA_NARRATOR` — a deployment may want semantic retrieval without
  narration (and vice versa). Mirrors the existing explicit-opt-in pattern.
