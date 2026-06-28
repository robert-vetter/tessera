# 0081. Milestone 11 plan: agentic / MCP-exposed grounded mode

- **Phase / milestone:** Milestone 11 — Agentic / MCP-exposed grounded mode:
  expose Tessera's grounded answers (claims + claim-level provenance + principled
  refusal) as **read-only MCP tools** an enterprise AI agent can call, and prove
  the trust contract survives the protocol boundary (post-roadmap; ROADMAP phases
  complete and tagged `phase-0`…`phase-4`; hardening `milestone-5`;
  embeddings-on-SAP `milestone-6`; embeddings-beyond-retrieval `milestone-7`;
  deterministic-ER-precision `milestone-8`; multi-field name+address ER
  `milestone-9`; registration-key ER `milestone-10`)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018: decisions recorded here
  instead of asked — except the three project-shaping scope questions below, which
  were asked and answered 2026-06-28)

## Problem

The project's thesis (README, `PROJECT_BRIEF`) is **"a trust layer for enterprise
AI agents."** Yet through ten milestones Tessera only ever answers a *human* — at a
CLI (`tessera`, `tessera-devex`) or in the Joule-style chat surface
(`tessera-chat`). The one capability the thesis names and the engine has never had
is the ability for an **agent** to consume Tessera as its grounded substrate. The
Phase-4 close (spec 0042) even **removed an overclaim** that asserted agentic/MCP
was present, recording it truthfully as future work; the WRITEUP's "Deliberately
deferred" section names *"an agentic / MCP-exposed mode (grounded actions, not just
answers — the 2026-shaped extension of the same trust substrate)."* Milestone 11
takes that named lever.

The ER lever is **spent** (the M10 close: the residual floor is registry-only, not
a heuristic gap), so this milestone deliberately opens a **new dimension** rather
than deepening ER an eleventh time. It is the natural place the still-live
deterministic triggers (ADR 0005 LLM-judge, ADR 0006 semantic routing) *could* come
due — and the milestone records, with a measurement, that neither is forced yet.

Like Milestones 8–10 — and unlike Milestones 6–7 — this is **deterministic,
offline, and fully CI-reproducible**: no embedding on the trust path, no cloud, no
online LLM run, no spend. The claim/faithfulness path stays embedding-free and
LLM-free; the leak-guard is extended, not relaxed.

**Maintainer decisions (asked & answered 2026-06-28 — project-shaping, so asked):**

1. **The thrust — agentic / MCP-exposed grounded mode.** Chosen over a second real
   connector, HANA graph persistence, and BTP serving. It completes the project's
   own thesis and is a new dimension, not a repeat of the Milestone-5 real-connector
   move. The heading-chunk retrieval fix surfaced in Milestone 10 is **folded in as
   the opening unit** (it is one unit's worth of work, not a milestone of its own).
2. **Determinism / cost posture — deterministic, offline, CI-reproducible.** The
   trust path stays deterministic; the whole milestone reproduces in CI with no
   keys and no spend (the M8–M10 posture). Any LLM stays *on-top narration only*
   (ADR 0013); no LLM enters routing, reasoning, retrieval, or the verifier.
3. **MCP surface scope — read-only grounded tools.** The MCP server exposes
   ask / RCA / lookup as tools that **return** claims + provenance + principled
   refusal. **No effectful actions** and **no action proposals** — Tessera is the
   agent's *evidence oracle*, not its actuator. Effectful / proposing tools are
   explicitly recorded as future work (the safe, honest scope for a trust layer; it
   adds no write surface and no new safety posture).

## The design (recorded for ADR 0022)

**The substance already exists; M11 gives it a serializable contract and a
protocol.** `src/tessera/surface/session.py::ChatSession` already does the hard
part: it holds per-vertical context (graph, KB, route fn, the vertical's
`claim_shapes`), routes a question, and **live-verifies every emitted claim with the
eval's own `is_supported` + claim shapes** (ADR 0011). The chat surface is a
*human* renderer over it; an MCP server is a *machine* renderer over the same thing.
So M11 is built in three honest layers:

1. **A vertical-neutral grounded-tool layer** (`src/tessera/agent/`, new — *not* in
   the ADR 0008 frozen core, so additive and unconstrained). Pure-stdlib,
   deterministic functions that take a question (and a vertical/tool selector) and
   return a **JSON-serializable `GroundedResult`**: the route + reason, the ordered
   numbered claims, each claim's **cited evidence** (record ids → origin: source,
   locator kind, locator detail), each claim's **live verifier verdict**, and — for
   a refusal — the refusal reason carried explicitly so *a refusal stays a refusal
   across the boundary* (never silently rendered as an answer). This layer reuses
   `ChatSession`'s routing + verification rather than duplicating it; the chat
   surface is refactored to share it where clean (no behaviour change — pinned by
   the existing surface tests). **The verifier still runs at the boundary**, so a
   tool result that is not fully grounded is *labeled* as such, by construction.
2. **The MCP server** (`tessera-mcp` entry point) — a thin adapter that registers
   the grounded tools over the official Python MCP SDK (stdio transport). The SDK is
   an **opt-in extra** (`uv sync --extra agent`), exactly like `hdbcli` is the
   `cloud` extra (ADR 0015): the default clone-and-run graph and CI **never import
   `mcp`**, pinned by a test mirroring
   `tests/test_vectors.py::test_default_import_graph_has_no_hdbcli`. The server
   contains *no grounding logic* — it serializes layer-1 results and shapes errors;
   its wiring is contract-tested against the SDK (or a fake transport), the pattern
   the GenAI-Hub / vector adapters already use.
3. **The measured trust contract across the boundary** (eval/tests). The existing
   gold cases are run *through the grounded-tool layer* and asserted to be
   **claim-equivalent to the direct engine path** and to **pass the same verifier**
   — faithfulness 1.0 *through MCP*, refusals preserved as refusals. The boundary is
   thus not a place trust can quietly leak; that property is measured, not asserted.

**Why read-only is the right trust scope.** A trust layer's job is to ground, cite,
and refuse — not to act. Returning evidence (with provenance and a verifier verdict)
is exactly the substrate an agent needs and is the honest scope that adds no write
surface. Effectful/proposing tools are recorded as future work in ADR 0022.

## Success criterion

An enterprise AI agent can call Tessera over MCP and receive **grounded, cited,
verifier-checked answers and principled refusals** for both verticals and the real
`github_actions` connector — and the trust contract is **proven to survive the
protocol boundary**, offline and in CI:

- A real MCP client session against `tessera-mcp` returns grounded results for a
  representative question per vertical and a correct **refusal** for an
  insufficient-evidence question — recorded as a committed transcript (the "ran on"
  honesty, no spend), the way the Milestone-5 GitHub-Actions snapshot is committed.
- The grounded-tool layer's results are **claim-equivalent to the direct engine
  path** on every existing gold case (the protocol adds no facts and drops none) and
  **pass the eval's own `is_supported` verifier** — faithfulness 1.0 across the
  boundary, measured.
- **A refusal stays a refusal across the boundary** — pinned by a test: an
  insufficient-evidence question yields a `GroundedResult` flagged as a refusal with
  its reason, never a fabricated answer.
- **The default clone-and-run + CI stay pure-stdlib** — a test pins the default
  import graph has no `mcp`; the MCP SDK is the opt-in `agent` extra; CI is
  key-free, network-free, deterministic.
- **The leak-guard holds and is extended.** `is_supported` stays embedding-free and
  LLM-free; the new tool layer does not pull an embedding/LLM/MCP import toward the
  verifier (guard test extended). Faithfulness stays the single hard gate at 1.0 on
  every battery.
- **The heading-chunk retrieval fragility is closed** (folded-in opening unit): the
  Milestone-10 near-tie (a Markdown section heading competing with its own content
  in BM25) is fixed at the chunking layer, the relaxed `test_retrieval.py` renewal
  test is **tightened back to a strict assertion**, and all three batteries are
  proven to hold (faithfulness 1.0; no gold/synthetic regression).

## Acceptance criteria

- [ ] **Heading-chunk retrieval fix (Unit 2, spec 0082, ADR 0021).** The chunker
      (`ingestion.chunk_text`, ADR 0008 frozen core) no longer emits a heading-only
      chunk that competes in BM25 with the content it introduces (a Markdown
      `#`-heading line attaches to the body that follows it). The relaxed
      `tests/test_retrieval.py` renewal test is restored to a **strict** assertion
      (the auto-renewal clause ranks top, not merely top-2). All three batteries
      read byte-identical or better (faithfulness 1.0; coverage/quality not
      regressed) — proven, not assumed. **ADR 0021** records the chunking decision.
      **Pre-merge 5-lens adversarial multi-agent review** (frozen-core change; a
      retrieval-ranking change is a coverage risk until proven).
- [ ] **Grounded-tool layer (Unit 3, spec 0083, ADR 0022).** `src/tessera/agent/`
      — pure-stdlib, deterministic `GroundedResult` + the ask/RCA/lookup tools over
      both verticals + `github_actions`, each **verifier-checked at the boundary**,
      refusals carried explicitly, JSON-serializable. `ChatSession` refactored to
      share the layer with **no behaviour change** (surface tests byte-identical).
      Leak-guard extended (tool layer keeps the verifier embedding-/LLM-free). Full
      stdlib test coverage. **ADR 0022** records the agentic boundary (read-only,
      verifier-at-the-boundary, MCP opt-in extra, leak-guard) + the rejected
      effectful/proposing scope.
- [ ] **MCP server (Unit 4, spec 0084).** `tessera-mcp` entry point over the Python
      MCP SDK (stdio), SDK as the opt-in `agent` extra; the default-import pin (no
      `mcp` in the base graph); contract test of the wiring against the SDK / a fake
      transport; a **committed real MCP-client session transcript** (grounded
      answer per vertical + a refusal). No grounding logic in the server.
- [ ] **Trust across the boundary (Unit 5, spec 0085).** Every gold case run through
      the grounded-tool layer is **claim-equivalent** to the direct path and passes
      `is_supported` (faithfulness 1.0 through the boundary); the refusal-preserved
      pin; a recorded measurement point (history or a pinned test asserting the
      boundary-equivalence) so the new capability's effect on the metric is *known*,
      per principle 3. ADR 0005/0006 triggers re-examined and recorded as
      **still not forced** (no measured case).
- [ ] **Close (Unit 6, spec 0086).** Gate green under multiple `PYTHONHASHSEED`
      values; WRITEUP "agentic / MCP-exposed grounded mode" section (the layers, the
      boundary-trust measurement, the read-only scope + deferred actions, the still-
      live triggers); README (the new `tessera-mcp` door + `agent` extra); CHANGELOG
      `[milestone-11]`; ADR 0021/0022 nav + index; the ADR 0008 **empty-diff core
      check** run and the engine confirmed empty-diff except the one sanctioned
      heading-chunk delta (Unit 2) and any sanctioned surface-share refactor; STATUS;
      tag `milestone-11`; memory; next-milestone kickoff handed back.

## Scope

**In — the unit breakdown (one PR each, spec each):**

| Unit | Spec | Content |
|---|---|---|
| 1 | 0081 | this plan + the three recorded scope decisions (asked 2026-06-28) |
| 2 | 0082 | heading-chunk retrieval fix (chunker no longer emits a competing heading-only chunk); restore the strict renewal assertion; prove batteries hold; **ADR 0021**; pre-merge adversarial review |
| 3 | 0083 | `src/tessera/agent/` grounded-tool layer (`GroundedResult` + ask/RCA/lookup, verifier-checked at the boundary, refusals carried, JSON-serializable); `ChatSession` shares it (no behaviour change); leak-guard extended; **ADR 0022** |
| 4 | 0084 | `tessera-mcp` MCP server over the SDK (opt-in `agent` extra); default-import pin; wiring contract test; committed real client-session transcript |
| 5 | 0085 | trust across the boundary: gold cases through the tool layer are claim-equivalent + verifier-pass (faithfulness 1.0 through MCP); refusal-preserved pin; recorded measurement; ADR 0005/0006 triggers re-examined and recorded unforced |
| 6 | 0086 | close: WRITEUP/README/CHANGELOG/STATUS, ADR nav/index, empty-diff core audit, tag `milestone-11`, memory, kickoff |

**Out (explicitly):**

- **Effectful actions and action *proposals*.** The maintainer scoped M11 to
  read-only grounded tools. No tool writes, executes, drafts-for-execution, or
  proposes a side-effecting action. Recorded as future work in ADR 0022.
- **An LLM anywhere on the trust path.** Routing, reasoning, retrieval, ER, and the
  verifier stay deterministic (ADR 0006). An LLM may *narrate* on top (ADR 0013) but
  M11 adds no new narration and no engine LLM. ADR 0006's semantic-routing trigger
  is re-examined (Unit 5) and recorded as not forced — an agent client may itself be
  an LLM, but that LLM is *outside* Tessera's boundary, calling deterministic tools.
- **LLM-judged faithfulness (ADR 0005).** The verifier stays structural and
  embedding-/LLM-free; the leak-guard is extended, not relaxed. Re-examined and
  recorded as not forced (no measured case the structural check misses through the
  boundary).
- **Embeddings / the M6–M7 cloud regime.** `er_semantic.py`, `semantic.py`,
  `TESSERA_EMBEDDINGS`, HANA — all untouched. No cloud, no online run, no spend.
- **A second real connector / HANA graph persistence / BTP serving.** The other M11
  candidates; remain named future work.
- **A new gated eval metric.** Faithfulness stays the single hard CI floor at 1.0;
  the boundary-equivalence measurement is a pinned test / recorded point, not a new
  gate.
- **Statefulness / multi-turn agent context.** Each tool call is answered from
  evidence alone (the stateless property the WRITEUP already records); follow-up
  context remains future work.

## Eval impact

- **Faithfulness — held at 1.0, now *also across the MCP boundary*.** The headline
  is not a number that moves but a property that is *preserved under a new
  projection*: the same verifier passes on results delivered through the tool layer.
  Measured (Unit 5), not assumed — a boundary that dropped or fabricated a claim
  would fail the equivalence pin.
- **Coverage / quality — held, with the heading-chunk fix a small *honest gain*.**
  Unit 2 improves retrieval ranking (the renewal clause ranks top again); the
  batteries must not regress. Any battery number that moved unexpectedly is a
  regression the unit must catch (cluster/answer signatures, the M8–M10 discipline).
- **No new gated metric.** ER precision/recall and the boundary-equivalence stay
  *reported/pinned*, not gated; faithfulness remains the single invariant floor.

## Risks / open questions

- **The MCP SDK is a real third-party dependency (the central reproducibility
  risk).** Mitigated exactly as `hdbcli` was: it is the **opt-in `agent` extra**,
  lazily imported only by the server entry point, and the default import graph is
  **pinned free of it** by a test. CI installs the base graph and stays
  pure-stdlib/offline. The grounded-tool *substance* (layer 1) carries **no** MCP
  dependency and is fully CI-tested; the SDK only transports it.
- **Refactoring `ChatSession` to share the tool layer could change surface
  behaviour.** Mitigated by treating the surface tests as a byte-identical pin
  (the M8–M10 "numbers must not move" discipline applied to the chat surface): the
  refactor is a pure extraction, proven by the existing tests staying green
  unchanged. If a clean shared layer cannot be extracted without behaviour change,
  the layer is built standalone and the surface left as-is (recorded honestly).
- **The heading-chunk fix is a frozen-core change and a coverage risk.** A chunking
  change reshapes every document chunk's ids/spans; gold cases that cite a chunk id
  could shift. Mitigated by re-pointing any affected gold ids deliberately (as M7's
  finer chunking did), proving the batteries hold, and the pre-merge adversarial
  review. ADR 0021 records the decision; lands behind a measured "batteries hold".
- **"Verifier at the boundary" must not become decorative.** The tool layer runs
  `is_supported` and *reports* the verdict; it must not *gate* (drop) claims
  silently — that would hide a miss. The verdict is surfaced per claim (as the chat
  surface already does), so an agent sees groundedness, and the eval (Unit 5)
  asserts the boundary path equals the gated direct path. The structural-check limit
  (ADR 0005) carries across the boundary unchanged and is recorded.
- **The new floor / honest boundary.** Read-only grounding means an agent must still
  *decide and act* outside Tessera; Tessera guarantees the evidence and the refusal,
  not the agent's downstream action. Named in ADR 0022 and the WRITEUP — the honest
  edge of a read-only trust substrate.
