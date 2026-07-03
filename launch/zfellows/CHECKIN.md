# Z Fellows check-in — the 5-minute arc

*Audience calibration (MARKET.md §6, verified): generalist-SV builders and
guest founders, not enterprise buyers. They celebrate working artifacts,
committed users, execution speed, and storytelling. Lead with the live
demo; keep SAP for Q&A. The one-axis-outlier frame: the only agent layer
where every claim is auditable and every action is approval-gated — and we
measure it.*

**The morning of the check-in:**

- Fill every `[N]` below from live sources — never projected numbers:
  stars/forks (repo page), merged PRs (`gh pr list --state merged`), tests
  (`uv run pytest` tail), external users/issues (issue tracker), outreach
  counts + calls + pilots (`launch/outreach/targets.csv`), weeks since
  first commit (2026-06-05).
- Warm the demo: open <https://robert-vetter-tessera.hf.space> once (the
  free tier sleeps after ~48h idle).
- Start the offline fallback in a second tab: `uv run tessera-ui`
  (every beat works with no network — a live audience never sees a cold
  start).
- Rehearse twice against a timer. The beats are clicks, not slides.

---

## 0:00–0:40 — The story (the Replit incident)

> Last July, an AI agent at Replit deleted a production database during a
> code freeze. Then it fabricated data to cover it up, and misreported
> whether rollback was possible. Everyone's fix since then is
> permissions — *which tools the agent may call.* Almost nobody gates the
> other thing: **what the agent is allowed to claim.**
>
> I spent the last [N] weeks building the missing layer, in the open: the
> agent can only say what it can prove — and only do what you approve.

## 0:40–2:40 — The live demo (four clicks, script: docs/DEMO.md §2)

1. **Ask** "Why did run R-1042 fail?" → claims, each with a green
   *verifier-checked* chip → open one → the exact log lines, file,
   snapshot date. *"The chip isn't decoration — it's the eval's own
   verifier, live on this answer."*
2. **Ask about a run that passed** → an explicit refusal. *"This is the
   Replit moment: no evidence, no claim. It declines instead of
   confabulating."*
3. **Draft the incident action** → every field cited → preview the
   literal GitHub POST body, `sent: false` → approve → **the receipt**.
   *"Nothing left the machine. The one real send this system ever did is
   a committed, scrubbed receipt behind a human approval."*
4. **The floor** → the home page's trust table. *"Faithfulness is a hard
   1.0 floor in CI — an unsupported claim fails the build. And we
   benchmarked the gate itself: same corpus, same questions, same
   verifier, the engine's own retrieval run ungated gets trustworthy
   outcomes on zero to 25 percent of cases; gated, 80 to 100. On the gold
   sets, offline, reproducible from a clone — no LLM judge."*

## 2:40–3:40 — What shipped in [N] weeks (velocity, receipts)

> [N] weeks ago (first commit 2026-06-05) this repo was empty. Since
> then, solo, in public:
>
> - **The full trust chain, measured:** grounded answers with per-claim
>   provenance → evidence-gated action drafts → exact payload previews →
>   execution behind approval with receipts — four boundaries, each with
>   recorded numbers.
> - **[N] merged PRs, [N] tests, 29 ADRs**, every unit spec-first behind
>   a CI gate; the faithfulness floor has held at 1.0 throughout — and
>   it's real: it has failed honestly on un-planted data and been
>   re-earned (the trail is committed).
> - **A live demo anyone can try** — committed in writing, delivered —
>   plus a recorded session of a real Claude agent grounded *only*
>   through these tools: citing, refusing, and getting its action gated.
> - **It works on your data:** point it at any public repo's CI —
>   grounded root-cause in ~20 seconds — or your CSVs and documents, with
>   a per-repo trust battery that honestly failed on one third repo and
>   said so. That failure report is the product working.
> - **Launch state:** [fill live: benchmark published ✓ / registries
>   submitted? / Show HN posted? stars [N], external users/issues [N],
>   outreach [N] messages → [N] calls → [N] pilots]. *(If launch is still
>   pending my go: "the entire launch kit is staged, ready, waiting on my
>   go — that's a deliberate timing call, not a delay.")*

## 3:40–4:30 — The plan (3 / 6 / 12 months)

- **3 months** — convert the outreach wave into **2–3 design-partner
  pilots** (DACH agent consultancies; the "pilot in a day" is scoped and
  written); the benchmark cited in the agent-eval conversation; the OSS
  loop (strangers' repos through `smoke`) feeding the trust batteries.
- **6 months** — pilots → **paid audit instrumentation** (the consultancy
  hands its client an audit artifact; we charge for instrumentation, not
  seats); the receipt schema hardened against one real compliance
  workflow (EU AI Act Art. 12/14 mapping, kept at documentation level);
  the first non-GitHub connector chosen *by pilot demand, not roadmap
  vanity*.
- **12 months** — the boring, valuable position: **the evidence layer
  agents in regulated European deployments pass through** —
  vendor-neutral, on-prem, deterministic. The wedge the incumbents leave
  open: closed platforms won't be open, gateways have no evidence model,
  and model vendors can't sell "don't trust our model's say-so".

## 4:30–5:00 — The asks

1. **Design-partner intros:** teams shipping agents for clients — AI/SAP
   consultancies, MCP platform teams. One warm intro beats fifty cold
   DMs.
2. **One enterprise-AI mentor** who has sold trust/audit infrastructure
   to engineering orgs (not compliance orgs) — I have positioning
   questions with real money attached.
3. **Skeptics:** if you think the benchmark is beatable or the wedge is
   wrong, I want that conversation this week, not in month six.

---

## Q&A pocket answers (don't volunteer; stay inside what's measured)

- **"Why won't OpenAI/Anthropic just do this?"** *(positioning argument,
  not a fact:)* their trust story ultimately asks you to trust their
  model; this layer's value is that nobody has to. A deterministic,
  vendor-neutral verifier is structurally not their product — and they're
  shipping *more* agent autonomy, which makes an external gate more
  necessary, not less.
- **"Why not an MCP gateway?"** Gateways gate on identity and
  permissions — 13+ vendors already. A perfectly permissioned
  hallucination sails through all of them. Evidence is the empty quadrant
  (the market scan with sources is committed: docs/MARKET.md).
- **"Where's the LLM?"** Presenting, never attesting: optional narration
  above canonical claims. The cost is real and published — semantic
  phrasing misses are kept visible (devex 0.950 / gha 0.833 coverage
  offline) instead of papered over with a judge model.
- **"Isn't the benchmark self-serving?"** It computes and publishes its
  own definitional boundary (which cases only the composing engine could
  ever win), pins the tables in CI so they can't drift, and ships the
  seam to swap in any challenger answerer. The honest attack path is
  printed in the doc.
- **"SAP?"** Same system, their vocabulary; internship co-track; two
  misses closed on real HANA in one recorded online run. Deliberately
  Q&A material, not the pitch.
- **"Revenue?"** Not yet, by design: unpaid design partners first (the
  Langfuse/Helicone pattern); the pilot's audit artifact is the future
  product.
- **"Team?"** Solo plus agentic tooling — and the repo is the evidence
  that this works: spec-first units, adversarial reviews, a gate that
  can't be argued with. The month is the résumé.

## Logistics

- Screen: 1280×800, one browser window, bookmarks bar hidden, the four
  demo URLs as bookmarks in beat order; `tessera-ui` local tab as
  fallback.
- If the room wants depth after: the recorded agent session
  (`data/agent_session/TRANSCRIPT.md`) is beats 1–3 done by a real agent
  over MCP, unedited.
- The same arc serves the later in-cohort presentation; re-fill the
  placeholders then.
