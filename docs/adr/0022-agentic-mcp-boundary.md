# 0022. The agentic boundary: read-only, verifier-checked grounded tools over MCP

- **Status:** accepted
- **Date:** 2026-06-28

## Context

Tessera's thesis is "a trust layer for enterprise AI agents," yet through ten
milestones it only ever answered a *human* (the CLIs and the Joule-style chat
surface). The Phase-4 close (spec 0042) removed an overclaim that asserted an
agentic/MCP mode was present, recording it as future work; the WRITEUP names it
explicitly. Milestone 11 builds it (spec 0081), with three maintainer-set,
project-shaping decisions (asked & answered 2026-06-28): the thrust is agentic/MCP;
the posture is deterministic / offline / CI-reproducible; the surface scope is
**read-only grounded tools**.

The Model Context Protocol (MCP) is the 2026 lingua franca by which an agent calls
external tools. The question this ADR settles: *what* does Tessera expose to an
agent, *how* is the trust contract preserved across the protocol boundary, and how
is the protocol dependency kept off the clone-and-run / CI path.

## Decision

**Tessera exposes read-only grounded tools — it is an agent's evidence oracle, not
its actuator.** The tools *return* claims, claim-level provenance, and principled
refusals; none writes, executes, drafts-for-execution, or *proposes* a
side-effecting action. Grounding, citing, and refusing is exactly the substrate a
trustworthy agent needs, and read-only adds **no write surface and no new safety
posture** — the honest scope for a trust layer.

**The trust contract is enforced at the boundary.** Every tool result is produced
by the existing deterministic engine and **live-verified with the eval's own
`is_supported`** + the domain's claim shapes (ADR 0005/0011) before it leaves the
process. Each claim carries its verifier verdict and its full provenance inline
(record id, source, locator, ingested-at, text), so an agent receives groundedness
*and* its evidence in one stateless call. A **refusal is carried explicitly** and
can never be rendered as an answer across the boundary. The verifier stays
structural and **embedding-/LLM-free**; the leak-guard is extended so the new tool
layer pulls no embedding / LLM / MCP import toward the verifier.

**The layering keeps the protocol off the trust path** (three layers, spec
0081/0083/0084):
1. A vertical-neutral, **pure-stdlib** grounded-tool layer (`tessera/agent/`) —
   the `ground(domain, question)` substance, fully CI-tested, **no MCP dependency**.
2. An MCP server (`tessera-mcp`) that only serializes layer-1 results over the SDK.
3. A measured proof that the boundary preserves faithfulness (gold cases through the
   layer are claim-equivalent to the direct path and pass the verifier).

**The MCP SDK is an opt-in extra** (`uv sync --extra agent`), exactly as `hdbcli`
is the `cloud` extra (ADR 0015): lazily imported only by the server entry point;
the default clone-and-run import graph and CI **never import `mcp`** (pinned by a
test mirroring the hdbcli pin). CI stays pure-stdlib, offline, key-free,
deterministic.

**Deterministic, no LLM on the path.** The agent *client* may itself be an LLM, but
that LLM is **outside** Tessera's boundary, calling deterministic tools; routing,
reasoning, retrieval, ER, and the verifier stay rule-based (ADR 0006). M11 adds no
engine LLM and no new narration. The agent layer uses each domain's **lexical**
path (no embedding index), so it is offline and reproducible.

## Consequences

- **The thesis is realized and provable:** an agent can consume Tessera over MCP and
  get grounded, cited, verifier-checked answers and honest refusals — and the
  boundary is *measured* not to leak trust (Unit 5), not merely asserted.
- **No new safety surface.** Read-only means Tessera guarantees the evidence and the
  refusal; the agent still decides and acts *outside* Tessera. That division is the
  honest edge of a read-only substrate (named in the WRITEUP).
- **Clone-and-run and CI are unaffected.** The substance is stdlib and tested; the
  SDK only transports it and is opt-in.
- **The structural-verifier limit carries across the boundary unchanged** (ADR
  0005): a 1.0 means every claim is mechanically supported by its citation, not that
  the answer is wise. The agent sees per-claim verdicts, not a semantic guarantee.

## Alternatives considered

- **Effectful tools (write/execute).** Rejected for M11: it materially expands the
  project's surface and safety posture for a capability the thesis does not require;
  a trust layer grounds and refuses. Recorded as future work.
- **Action *proposals* (dry-run drafts an agent/human approves).** Rejected for
  M11 as still outside the read-only scope the maintainer set; a natural next step,
  recorded as future work — proposals would themselves be grounded, cited, and
  verifier-checked the same way.
- **Put grounding logic in the MCP server.** Rejected: the server must be a thin
  transport so the substance stays CI-tested without the SDK, and so a future
  transport (HTTP, a different protocol) reuses the same verified layer.
- **Bundle the MCP SDK as a hard dependency.** Rejected: it would break the
  pure-stdlib clone-and-run and the key-free CI the project guarantees; the opt-in
  extra is the established pattern (ADR 0015).
- **An LLM router/judge as part of this milestone (ADR 0005/0006 triggers).**
  Rejected: no measured case forces it, and it would break the deterministic,
  reproducible posture the maintainer chose; the triggers stay live and are
  re-examined in Unit 5.
