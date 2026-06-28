# 0083. The grounded-tool layer

- **Phase / milestone:** Milestone 11, Unit 3 (see spec 0081)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018)

## Problem

Milestone 11 exposes Tessera as a trust substrate an enterprise AI agent can call
(spec 0081). The MCP server (Unit 4) needs a **serializable, deterministic,
verifier-checked** grounded-answer surface to wrap — one that returns claims,
claim-level provenance, and principled refusals as plain data, for *all three*
measured domains (business, devex, and the real `github_actions` connector). The
substance already exists in `surface/session.py::ChatSession` (route + live-verify
each claim with the eval's own `is_supported`), but it is shaped for a *human*
renderer over two verticals and is not serializable. This unit builds the
vertical-neutral grounded-tool layer; Unit 4 transports it over MCP.

## The design

A new package `src/tessera/agent/` — **not** in the ADR 0008 frozen core, so
additive and unconstrained — with three concerns:

1. **A domain registry** (`agent/grounded.py`): the single source of truth for
   *what an agent can ask about*. Each `GroundedDomain` binds a name, an engine
   builder (`() -> (KnowledgeGraph, KnowledgeBase)`), the vertical's router
   (`(question, graph, kb) -> (Route, Answer)`), and its declared `claim_shapes`
   (ADR 0011). Three domains: `business` (business router), `devex` (devex router),
   `github_actions` (the **same** devex router over the committed real snapshot —
   GitHub Actions data *is* CI data, proven reusable). Engines are built once and
   cached (deterministic, no rebuild per call).

2. **`ground(domain, question) -> GroundedResult`**: route the question in the
   named domain, **live-verify every emitted claim** with `is_supported` + the
   domain's claim shapes (the eval's verifier, at the boundary), and return a
   frozen, **JSON-serializable** result:
   - `domain`, `question`, `route` (`{kind, reason}` — the routing decision is part
     of the answer's story, so the agent sees *which* path answered and why);
   - `grounded` / `refused` (exactly one holds) and `refusal` (the reason, carried
     **explicitly** so a refusal stays a refusal across the boundary — never a
     fabricated answer);
   - `claims`: each with its `text`, its **per-claim verifier verdict**, and its
     full `support` inline (every cited record's `id`, `source`, `locator`
     `{kind, parts}`, `ingested_at`, `text`) — so an agent gets complete provenance
     in **one** stateless call, no round-trip;
   - `all_verified`.
   `to_dict()` renders the whole thing to JSON-native types (the MCP server just
   `json.dumps` it).

3. **`assertions(domain, record_id) -> list[...]`** (a second read-only tool): the
   additive resolution/mention trail touching a cited record — the inspectable
   "why is this evidence connected" provenance of the entity-resolution layer,
   serializable the same way. Exposes the graph's reversible-assertion design to an
   agent. (Whether it becomes its own MCP tool is Unit 4's call; the function lands
   here.)

**Sharing with `ChatSession` (no behaviour change).** `surface/session.py` is
refactored so `_business_context` / `_devex_context` build from the shared
`GroundedDomain` registry and `ask()` uses a shared `verify_claims` helper — one
source of truth for the domains and the verify loop. The chat surface keeps its two
verticals and its exact behaviour; the existing `tests/test_surface.py` stays green
**unchanged** (the byte-identical pin). If a clean extraction proved impossible
without behaviour change, the layer would be built standalone and the surface left
as-is, recorded honestly — but it is achievable (the contexts are already this
shape).

**Read-only and deterministic (the recorded scope).** No tool writes, executes, or
proposes a side-effecting action (the maintainer's read-only scope, spec 0081). The
layer is pure-stdlib and offline: it uses each domain's **lexical** path (no
embedding index passed), so importing `tessera.agent` pulls **no** embedding / LLM /
`hdbcli` / `mcp` module toward the verifier — the leak-guard, extended here, holds.

## Acceptance criteria

- [ ] `src/tessera/agent/` exists with `GroundedDomain`, the three-domain registry,
      `ground(domain, question) -> GroundedResult`, `assertions(domain, record_id)`,
      and `GroundedResult.to_dict()` producing JSON-native types.
- [ ] `ground` **live-verifies** every claim with `is_supported` + the domain's
      claim shapes; the per-claim verdict and `all_verified` are in the result; the
      verdicts equal what the direct engine path / `ChatSession` computes.
- [ ] A **refusal is carried explicitly** (`refused=True`, `refusal` set, `claims`
      empty) — pinned by a test (an out-of-scope question never becomes an answer
      across the boundary).
- [ ] **Full provenance inline**: every claim's support serializes its record id,
      source, locator (kind + parts), ingested_at, and text; `to_dict()` round-trips
      through `json.dumps`/`json.loads`.
- [ ] `ChatSession` shares the registry + verify helper with **no behaviour change**;
      `tests/test_surface.py` passes **unchanged**.
- [ ] **Leak-guard extended**: a test pins that importing `tessera.agent.grounded`
      imports no embedding module (`er_semantic`, `semantic`, `platform.vectors`),
      no `hdbcli`, and no `mcp`. The verifier stays embedding-/LLM-free.
- [ ] All three domains answer a representative question (grounded, verified) and
      refuse an out-of-scope one — covered by `tests/test_agent.py`. Faithfulness
      1.0 on all batteries unchanged; deterministic across `PYTHONHASHSEED`.
- [ ] **ADR 0022** records the agentic boundary (read-only grounded tools,
      verifier-at-the-boundary, MCP as an opt-in extra, leak-guard) + the rejected
      effectful/proposing scope.

## Scope

**In:** the `agent/` package (registry, `ground`, `assertions`, `GroundedResult` +
`to_dict`); the `ChatSession` share; the leak-guard extension; `tests/test_agent.py`;
ADR 0022.

**Out:**
- **The MCP server / transport** — Unit 4. This unit's API is plain Python; it has
  no `mcp` dependency.
- **Effectful or proposing tools** — recorded out of scope (ADR 0022); read-only
  only.
- **An LLM / embeddings on the path** — the layer is deterministic and lexical;
  ADR 0005/0006 stay deferred.
- **Multi-turn / stateful agent context** — each `ground` call is answered from
  evidence alone (the stateless property); follow-up context is future work.
- **New gold cases / eval wiring** — the boundary-trust *measurement* (gold cases
  through the layer) is Unit 5; this unit ships the layer + unit tests.

## Eval impact

- **Faithfulness held at 1.0; no battery number moves.** This unit adds a new
  consumer of the engine, not a new answer path — `ground` routes through the same
  routers and verifies with the same `is_supported`. The boundary-equivalence
  *measurement* lands in Unit 5.

## Risks / open questions

- **The `ChatSession` refactor could shift surface behaviour.** Mitigated by the
  byte-identical pin (`tests/test_surface.py` unchanged) and the fallback-to-
  standalone escape hatch, recorded.
- **`github_actions` has no router of its own** — it reuses the devex router. A
  question that routes to `summary` over a snapshot with no PR diffs must **refuse**
  honestly, not error. Verified (the router falls through to a refusing path); a
  test covers an out-of-scope github question.
- **Serialization must not silently drop a verdict.** `to_dict()` includes every
  claim's verdict and the refusal; a result that hid an unverified claim would
  defeat the boundary's purpose. Pinned by a test asserting the verdicts survive the
  round-trip.
- **Leak-guard scope creep.** github_actions `uses_semantic` in the eval; the agent
  layer must use the **lexical** path so no embedding import is pulled in. Pinned by
  the import test.
