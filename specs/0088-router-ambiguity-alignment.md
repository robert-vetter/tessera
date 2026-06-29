# 0088. Router-ambiguity alignment: a bare ambiguous term refuses, as compose does

- **Phase / milestone:** Milestone 12, Unit 2 (plan: spec 0087)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

`tests/test_boundary.py` pins two honest router-vs-engine divergences (Milestone 11,
spec 0085). One is **deterministic and closable offline** — the recorded "next lever":

> `business/05` — the bare term **"Logistik"**: the eval's `compose` engine refuses it
> as ambiguous (it ties across *Müller Logistik* and *Nordwind Logistik*), while the
> production business **router** routes a bare term to lexical lookup and **grounds**
> (surfacing both firms' rows). Pre-existing router-vs-engine gap; next lever = align
> the router's ambiguity handling with `compose`.

The asymmetry is exact and mechanical:

- `find_named_entities` (the router's `classify`, `tessera.business.reasoning`) requires
  the longest common run with an entity name to be **≥ 6 chars AND ≥ 0.6 of the name**.
  `"Logistik"` (8) vs `"müller logistik"` (norm len 15) → 8/15 = 0.53 < 0.6 → **0
  entities** → `classify` falls through to `lookup` → grounds.
- `resolve_entity` (`compose`, `tessera.business.composition`) requires only the
  **absolute ≥ 6**. `"Logistik"` clears it against both firms → equal best → a **tie
  between distinct entities** → `status="ambiguous"` → `compose` refuses.

So `compose` treats a bare shared token as an ambiguous *entity reference* and refuses;
the router treats it as *no entity* and lexically looks it up. Grounding an ambiguous
term as if it were unambiguous is the weaker behaviour — the honest answer is the
refusal `compose` already gives. This unit closes the gap by making the router **defer
to `compose`'s own resolver** for the no-named-entity case, so the two agree by
construction.

## The fix (surgical, vertical-side)

In `tessera.business.routing.classify`, after the existing checks (≥2 entities → multi;
superlative → multi; exactly 1 entity → entity), add one branch **before** the lookup
fallthrough: if `resolve_entity(question, graph).status == "ambiguous"`, return a
`Route(kind="entity", …)` with an honest reason naming the tied candidates. The existing
`route` dispatch sends `kind="entity"` to `compose`, which — calling the same
`resolve_entity` — refuses with its ambiguity message. No new dispatch branch; the
router and `compose` share the resolver, so they cannot disagree on ambiguity again.

Only the **ambiguous** case changes. `resolve_entity` returning `"none"` (no 6-char
overlap — e.g. *"When does the service agreement renew?"*, *"What colour is the sky?"*)
still routes to lookup, unchanged; `"ok"` (a clean single partial match the stricter
`find_named_entities` missed) also still routes to lookup, unchanged. The behaviour
change is precisely: **a bare term that ties across ≥2 distinct entities now refuses as
ambiguous instead of being lexically grounded.**

This is **vertical-side** (`tessera/business/routing.py`), not ADR 0008 frozen core.
But it changes a shared production router (the chat surface and the agent path both use
it), and refusing is a recall risk, so it carries a **pre-merge adversarial review**.

## Acceptance criteria

- [ ] `classify` routes a bare ambiguous entity term (`"Logistik"`, `"Trading"`) to the
      compose path with an honest, candidate-naming reason; `route` returns a refusal for
      it (matching `compose`).
- [ ] A non-ambiguous single term still grounds via lookup (`"When does the service
      agreement renew?"` stays `kind="lookup"` and grounds), and a no-overlap question
      still refuses via lookup — a targeted test pins both, so the fix does not
      over-refuse.
- [ ] The `("business", "05_ambiguous_refusal")` pin is **removed** from
      `_EXPECTED_ROUTER_DIVERGENCES` in `tests/test_boundary.py`; the boundary test now
      asserts `business/05` routes to a **refusal** (matching its gold `kind="refuse"`),
      and passes. `github_actions/05` remains the one pinned (embeddings-only) divergence.
- [ ] **No battery number moves.** business gold (11) and synthetic (53) stay
      `1.000 / 1.000 / 1.000`; devex and github_actions unchanged. Proven by an eval
      before/after, not assumed (the `business/05` gold case is scored via `compose`, and
      no `engine="route"` gold/synthetic case is a bare ambiguous term, so the router
      change moves nothing the harness scores).
- [ ] The existing `tests/test_routing.py` assertions still hold (none asserts a bare
      ambiguous term grounding); a new assertion pins the ambiguous-refusal route.
- [ ] Gate green under multiple `PYTHONHASHSEED` values; pre-merge adversarial review
      clean (or its findings fixed and pinned).

## Scope

**In:** the one-branch `classify` change; the boundary-pin removal + the tightened
boundary assertion; a targeted routing test (ambiguous refuses, non-ambiguous still
grounds); a docstring refresh where the closed divergence is referenced
(`test_adr_0005_0006_triggers_not_forced_by_the_boundary`).

**Out:** changing `resolve_entity` or `find_named_entities` themselves (the router defers
to the existing resolver; the matchers are untouched); moving the synthetic
`_ambiguous_token_cases` from `engine="compose"` to `engine="route"` (a possible future
tightening — kept out so **no number moves** this unit); the `github_actions/05`
divergence (offline synonymy, embeddings-only — out of scope, stays pinned); any
frozen-core change.

## Eval impact

**None — proven.** The change only affects the router path for bare ambiguous terms.
`business/05` is scored by the harness via `engine="compose"` (already refuses), and no
`engine="route"` gold/synthetic case is a bare ambiguous term, so every battery number
stays byte-identical. The *property* that improves is measured in `tests/test_boundary.py`:
one of the two pinned router divergences is closed, and the router path now matches the
gold disposition for `business/05` with no new divergence introduced.

## Risks / open questions

- **Over-refusal (recall) risk.** Mitigated by defining ambiguity as *exactly*
  `resolve_entity`'s tie condition (router and compose agree by construction), a targeted
  test that a non-ambiguous single term still grounds, an eval before/after proving no
  number moves, and the pre-merge adversarial review.
- **No ADR.** This aligns two existing deterministic components; it introduces no new
  hard-to-reverse decision (ADR 0006's deterministic-routing posture is unchanged — the
  router stays rule-based; it simply consults the existing resolver). Recorded here.
