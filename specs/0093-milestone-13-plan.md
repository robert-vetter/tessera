# 0093. Milestone 13 plan: the dry-run executable-payload preview

- **Phase / milestone:** Milestone 13 — Dry-run executable-payload preview: let an
  agent ask Tessera to **render the exact external API payload** an approver would
  send for a grounded action (a GitHub *create-issue* body for an incident, a PR
  *comment* body for a change summary) — **and send nothing**. The trust contract,
  measured across the read boundary (M11) and the action-draft boundary (M12), is
  carried one boundary further: to the **executable payload**. Post-roadmap (ROADMAP
  phases complete and tagged `phase-0`…`phase-4`; hardening `milestone-5`;
  embeddings-on-SAP `milestone-6`; embeddings-beyond-retrieval `milestone-7`;
  deterministic-ER-precision `milestone-8`; multi-field name+address ER
  `milestone-9`; registration-key ER `milestone-10`; agentic/MCP read-only grounded
  mode `milestone-11`; grounded actions over MCP `milestone-12`)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018: decisions recorded here
  instead of asked — except the three project-shaping scope questions below, which
  were asked and answered 2026-06-30)

## Problem

Milestone 12 extended the trust substrate from **answers** to **action drafts**:
`draft_action(kind, domain, question)` returns an `ActionProposal` whose every
`ActionField` carries a recomputed verifier verdict, faithfulness measured 1.0
across the action boundary (`tests/test_actions_boundary.py`), refusals carried, and
**nothing executed**. The proposal literally stamps `requires_approval=True` /
`executed=False`, and its docstring records the honest edge: it "renders **no
executable payload**." An agent that must actually act still composes the wire
payload itself, *outside* Tessera's guarantee — the last ungrounded step.

ADR 0023 named the two future scopes precisely: **effectful execution** ("outside
the honest scope of a trust layer") and a **dry-run executable-payload preview**
(declined for M12 only — "a step toward execution … adds a transport surface the
trust story does not need yet"). Milestone 13 takes the *smaller, in-character* of
the two: render the exact payload that *would* be sent, with **every value in it
traced to a verifier-passing field**, and send nothing. This is the strongest honest
claim a trust layer can make about action — *here is byte-exactly what would leave
the system, and all of it is grounded; you approve and send* — without crossing into
credentials, irreversibility, or breaking clone-and-run. It is the same measured
boundary pattern a third time (read → action draft → executable payload).

Execution itself, done honestly in a clone-and-run / CI project, would need a
simulated default actuator (no credentials in CI) plus an opt-in real path — i.e.
**this renderer plus an execution receipt**. So the preview is the verifiable core of
execution regardless; building it first is the disciplined vertical slice, and leaves
real execution as a later, separate, larger posture decision.

**Maintainer decisions (asked & answered 2026-06-30 — project-shaping, so asked):**

1. **The thrust — the dry-run executable-payload preview.** Chosen over effectful
   execution behind approval, a second real connector (Jira), HANA graph
   persistence, and BTP serving. It extends the measured trust contract one more
   boundary while keeping Tessera a **trust layer, not an actuator** (ADR 0023's
   recorded position). It revisits ADR 0023's *declined dry-run* with a fresh
   decision recorded in **ADR 0024**, whose honest edge is stated plainly: **render
   ≠ send.**
2. **The target — GitHub.** A single, real target system: `incident` →
   GitHub REST *create an issue*; `pr_summary` → GitHub *issue-comment on the PR*
   (the GitHub-native "post the summary"). The `github_actions` connector is already
   real and in-scope, so the target contract is authentic and `incident`→issue is the
   natural mapping. Jira / multi-target was offered (the "both" option) and declined
   to keep the surface small; a second target is future work.
3. **Posture — offline / CI-reproducible / no-spend** (the M8–M12 default). The
   renderer is deterministic, pure-stdlib, fully provable in CI; **nothing is sent,
   no cloud, no credentials.** For a render-only thrust nothing needs to leave the
   machine, so the whole milestone stays CI-reproducible (unlike the M6/M7 online
   excursions). LLM-narrated payload prose (the ADR 0005/0006 triggers, ADR 0013
   narration) was implicitly available and not taken; the triggers are re-examined at
   the payload boundary and recorded **still not forced**.

**Finer decisions (not project-shaping — decided and recorded here, per autonomous
mode):**

- **Both catalog kinds get a renderer**, not just `incident`. M12's measured property
  covers *every* drafted action (incident per failed run, PR summary per PR); M13's
  payload property mirrors it (a rendered payload per drafted action) — so
  `pr_summary` is rendered too, as a GitHub PR comment. Single target system; full
  catalog coverage; symmetric with M12.
- **A payload is rendered iff `proposal.all_grounded`.** The payload-level analogue
  of "a refusal never becomes an answer" (M11) / "a refusal is carried, never drafted
  over" (M12): a refused, route-incompatible, wrong-domain, or partially-grounded
  proposal yields **no payload** (a carried "withheld" result), never a payload over
  an unverified field.
- **Grounded values vs. fixed scaffolding, named honestly.** The payload's *content*
  comes only from verified `ActionField` values; the JSON keys, the section labels
  (`"Failing run"`, ` ``` ` fences), the fixed `"labels": ["incident"]`, and the
  target binding (`{owner}`/`{repo}`, a deployment config, not evidence) are
  **template scaffolding**, declared as such. The body is built **only** by joining
  (fixed label + verified field value) sections, so it is byte-reconstructable from
  the verified fields plus the known template — the provably-failable "added nothing"
  check (the M12 concatenated-seam lesson, generalized to the body string).

## The design (recorded for ADR 0024)

**A rendered payload is a grounded artifact, built strictly from a verifier-checked
`ActionProposal` (ADR 0023).** A new layer `src/tessera/agent/payloads.py` (additive,
*not* ADR 0008 frozen core) consumes the M12 boundary and never reads raw text, never
grounds a second way, never invents content. It maps a fully-grounded proposal into a
`RenderedPayload` — the **exact** GitHub wire request (method, path template, and a
JSON body) — in which:

1. **Every content slot is one verified field, re-checked.** The issue `title` is the
   proposal's verified `title` field; each body section is one verified `ActionField`
   (value + its inline provenance + its `verified` verdict), placed under a fixed
   label. A slot is built **only** from a field with `verified=True`; field
   verification already reduces to claim faithfulness (gated 1.0) plus the M12
   "added-nothing" check, so the payload introduces **no second verifier**.
2. **The body adds nothing.** The wire `body` string is a pure, deterministic
   template over the verified field values — `label + value`, joined by a fixed
   separator, in role order. It is byte-reconstructable from the proposal's verified
   fields, so a renderer that smuggled an ungrounded sentence into the body fails the
   byte-equality check. **Provably failable**, not tautological (ADR 0005 discipline).
3. **Rendered iff `all_grounded`; otherwise withheld.** A refused / route-incompatible
   / wrong-domain / partially-grounded proposal yields a `RenderedPayload` carrying
   `rendered=False` and the carried reason, with **no request** — an executable
   payload is never rendered over ungrounded ground.
4. **Render ≠ send; nothing executed.** The result declares `sent=False` /
   `requires_approval=True`. Tessera builds no transport, opens no socket, holds no
   credential; `{owner}`/`{repo}` is an unbound deployment placeholder. A human or
   agent takes the rendered request and sends it *outside* Tessera. The honest edge,
   named in ADR 0024 and the WRITEUP.

**The GitHub target (small, declared).** Two mappings, each from an existing
`ActionProposal` kind (no new grounding, no new answer path):

- **`incident` → `POST /repos/{owner}/{repo}/issues`** — `title` from the verified
  title field; `body` from the verified RCA fields (failing run, error log, prior
  occurrence, documented incident, resolving change, …) under fixed labels;
  `labels: ["incident"]` (fixed scaffolding). Domains: `devex`, `github_actions`.
- **`pr_summary` → `POST /repos/{owner}/{repo}/issues/{pr}/comments`** — `body` from
  the verified change-summary fields (PR metadata, diff hunks, motivating ticket, …);
  the `{pr}` path segment is derived from the verified subject field (the PR id) and
  traced. Domain: `devex`. (GitHub treats PRs as issues for comments — the native,
  least-destructive "post the summary".)

**Where it lives.** `src/tessera/agent/payloads.py` (new; additive). The MCP server
gains one thin tool — `preview_payload(action, domain, question)` — transporting the
layer verbatim; the SDK stays the opt-in `agent` extra; the default import graph stays
free of `mcp`. The payload layer is pure-stdlib and **pulls no embedding / LLM /
`hdbcli` / `mcp` import** (the leak-guard, `tests/test_agent.py`, is extended to call
`preview_payload`). The verifier (`eval/metrics.py`), `graph.py`, `resolution.py`,
`ingestion.py`, and the rest of the ADR 0008 frozen core are **untouched** — M13
expects a **zero-line frozen-core delta** (as M12).

## Success criterion

An enterprise AI agent can ask Tessera over MCP to **preview the exact payload** for a
grounded action and receive a byte-exact GitHub request whose every value is
field-grounded — or a carried "withheld" result — offline and in CI:

- A real MCP client session against `tessera-mcp` previews a GitHub **create-issue**
  payload for an incident and a **PR comment** payload for a change summary, plus a
  **withheld** payload for an action requested on insufficient/incompatible grounding
  — committed as a transcript (the "ran on" honesty, no spend), the way the M11/M12
  MCP sessions are committed.
- **Every content value of every rendered payload is field-grounded** and the body is
  **byte-reconstructable** from the proposal's verified fields plus the known template
  (adds nothing) — measured over cases **derived from the data** (a pinned CI test,
  `tests/test_payloads_boundary.py`, the M11/M12 boundary pattern), so the new
  capability's effect on the metric is *known* (principle 3).
- **Faithfulness is 1.0 across the payload boundary** — counted over every value of
  every rendered payload; a renderer that fabricated or over-claimed a value fails it.
- **A withheld payload is never a rendered payload** — a refused/incompatible/partial
  proposal yields `rendered=False` with no request (pinned by a test, provably
  failable).
- **The default clone-and-run + CI stay pure-stdlib** — the no-`mcp` import pin still
  holds; the payload layer adds no embedding/LLM/MCP import toward the verifier
  (leak-guard extended). Faithfulness stays the single hard gate at 1.0 on every
  battery; no battery number moves (the layer is a consumer, not a new answer path).
- **Zero frozen-core delta** — the ADR 0008 empty-diff audit over `milestone-12..HEAD`
  is empty (the payload layer is additive; the MCP tool is thin transport).

## Acceptance criteria

- [ ] **Phase plan (Unit 1, spec 0093).** This plan + the three recorded scope
      decisions (asked 2026-06-30) + the finer decisions + the design for ADR 0024.
- [ ] **GitHub payload renderer + ADR 0024 (Unit 2, spec 0094).**
      `src/tessera/agent/payloads.py` — `RenderedPayload` + the `incident`→create-issue
      and `pr_summary`→PR-comment renderers, built strictly from a verifier-checked
      `ActionProposal`, **rendered iff `all_grounded`**, every content slot a verified
      field, the body byte-reconstructable from the verified fields (added-nothing,
      provably-failable test), `sent=False`/`requires_approval=True`, JSON-serializable.
      Leak-guard extended. Full stdlib coverage. **ADR 0024** records the payload
      boundary (dry-run, render≠send, field-traced, revisiting ADR 0023's declined
      dry-run) + the rejected scopes (real execution; multi-target; LLM-narrated body).
      **Mandated pre-merge adversarial multi-agent review** (the new trust-bearing
      surface).
- [ ] **MCP preview tool + session (Unit 3, spec 0095).** `preview_payload` on
      `tessera-mcp` — thin transport, no render logic; the no-`mcp`-in-base-graph pin
      holds; contract test of the wiring; the committed `data/mcp_session/` session
      regenerated to add a rendered create-issue payload, a rendered PR-comment
      payload, and a withheld payload.
- [ ] **Trust across the payload boundary (Unit 4, spec 0096).** A pinned CI test
      (`tests/test_payloads_boundary.py`): over cases derived from the data (every
      failed run, every PR), every rendered payload is field-grounded + lossless + the
      body byte-reconstructable; faithfulness 1.0 across the payload boundary; a
      withheld payload carries no request. ADR 0005/0006 re-examined at the payload
      boundary and recorded **still not forced**.
- [ ] **Close (Unit 5, spec 0097).** Gate green under multiple `PYTHONHASHSEED`
      values; WRITEUP "dry-run payload preview" section (the renderer, the
      field-grounding measurement, render≠send + deferred execution, the still-live
      triggers); README (the preview tool + the corrected scope: payloads are
      *rendered* not *sent*); CHANGELOG `[milestone-13]`; ADR 0024 nav + index; the
      ADR 0008 **empty-diff core audit** run and confirmed empty; STATUS; tag
      `milestone-13`; memory; next-milestone kickoff handed back.

## Scope

**In — the unit breakdown (one PR each, spec each):**

| Unit | Spec | Content |
|---|---|---|
| 1 | 0093 | this plan + the three recorded scope decisions (asked 2026-06-30) + finer decisions + the design for ADR 0024 |
| 2 | 0094 | `src/tessera/agent/payloads.py` GitHub renderer (`RenderedPayload` + `incident`/`pr_summary`, rendered iff `all_grounded`, field-grounded + body byte-reconstructable, JSON-serializable); leak-guard extended; **ADR 0024**; **adversarial review** |
| 3 | 0095 | `tessera-mcp` `preview_payload` tool (thin transport); no-`mcp`-in-base pin holds; wiring contract test; committed real client-session transcript (rendered + withheld) |
| 4 | 0096 | trust across the payload boundary: rendered payloads field-grounded + lossless + body byte-reconstructable; withheld-never-rendered pin; pinned CI measurement; ADR 0005/0006 re-examined and recorded unforced |
| 5 | 0097 | close: WRITEUP/README/CHANGELOG/STATUS, ADR nav/index, empty-diff core audit, tag `milestone-13`, memory, kickoff |

**Out (explicitly):**

- **Effectful execution / actually sending anything.** Render-only. Tessera builds no
  transport, opens no socket, holds no credential, sends nothing. Real execution
  behind approval (with a simulated default + opt-in real actuator) stays the named
  future step, recorded in ADR 0024 (it would *consume* this renderer).
- **A second target system (Jira) or multi-target abstraction.** One target: GitHub.
  A `PayloadRenderer`-style multi-target interface and a Jira renderer are future work
  (the maintainer declined the "both" option).
- **An LLM anywhere on the payload path.** Rendering is deterministic templating over
  verified fields (ADR 0006 holds). No narrated cover prose (ADR 0013 unused).
  ADR 0005/0006 triggers re-examined at the payload boundary and recorded not forced.
- **A `business` action / payload kind.** Out of scope (as M12): the catalog stays the
  two DevEx-shaped kinds grounded in existing RCA/summary paths.
- **Embeddings / the M6–M7 cloud regime.** Untouched. No cloud, no online run, no
  spend.
- **A new gated eval metric.** Faithfulness stays the single hard CI floor at 1.0; the
  payload field-grounding measurement is a *pinned* test, not a new gate (the M11/M12
  pattern).
- **A new frozen-core change.** M13 expects a zero-line frozen-core delta; if one
  proves necessary it gets its own ADR and a pre-merge review (none is anticipated).

## Eval impact

- **Faithfulness — held at 1.0, now *also across the payload boundary*.** As in
  M11/M12, the headline is a property preserved under a new projection: every value of
  a rendered payload is backed by a verifier-passing field and the body adds nothing.
  Measured (Unit 4), not assumed — a renderer that fabricated or over-claimed a value,
  or smuggled content into the body, would fail the pin.
- **Coverage / quality — unchanged.** The payload layer is a consumer of existing
  groundings/proposals, not a new answer path; the batteries' numbers must not move
  (proven at close, not assumed).
- **No new gated metric.** Payload field-grounding stays *pinned*, not gated;
  faithfulness remains the single invariant floor.

## Risks / open questions

- **"Field-grounded" payload must not become decorative.** The renderer could assemble
  a body that *contains* the field values but also smuggles ungrounded text, or pass a
  lenient verdict. Mitigated by (a) deriving every content slot from a `verified`
  `ActionField` (no second verifier), (b) the **body byte-reconstruction** check — the
  rendered body must equal the deterministic template over exactly the verified field
  values, so any smuggled token fails byte-equality, (c) an injection test that an
  over-claimed/extra-content body fails, and (d) the **mandated pre-merge adversarial
  review** on this trust-bearing surface (the M12 review caught exactly this class of
  seam bug).
- **Path parameters and target binding.** `{owner}`/`{repo}` are a deployment binding,
  not evidence — declared as unbound scaffolding, never asserted grounded. The `{pr}`
  segment for a PR comment *is* content (it identifies the target resource), so it is
  derived from the verified subject field and traced; a test pins it.
- **Render ≠ send is the whole honesty.** The result carries `sent=False`; nothing is
  executed. The named, larger next step (real execution) is recorded in ADR 0024 with
  its posture implications, not built here.
- **The MCP SDK dependency.** Unchanged from M11/M12: opt-in `agent` extra, lazily
  imported, default import graph pinned free of it; the payload *substance* carries no
  MCP dependency and is fully CI-tested; the SDK only transports it.
- **Adversarial review scope.** The maintainer mandates a review on *frozen-core or
  trust-bearing* changes; M13 has no frozen-core change, but the payload renderer is a
  new trust-bearing surface (it decides what content is "grounded enough to send"), so
  it carries a pre-merge adversarial multi-agent review — honoring the mandate where
  the real risk lives.
