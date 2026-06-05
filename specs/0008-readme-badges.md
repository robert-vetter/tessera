# 0008. README badges

- **Phase / milestone:** Phase 0 — Foundation and frame (visible health)
- **Issue:** (none yet)
- **Status:** implemented

## Problem

`docs/ENGINEERING.md` §3 calls badges "visible health": the first thing a
reviewer sees, signalling that the project is gated and serious. The machinery
that backs honest badges now exists — a CI `gate` workflow and a live docs site
— so the README should surface them. Critically, the project's own rule is **no
overclaiming**: a badge must reflect something real, so the headline
**faithfulness/eval** badge (the genuine differentiator) and **coverage** badge
are *deliberately deferred* to Phase 1 when the harness and coverage actually
exist, rather than shown as decorative placeholders.

## Acceptance criteria

- [ ] A badge row near the top of `README.md` with badges that each reflect a
      real, current fact and link to their source:
      - **CI** — the `gate` workflow status, linking to the Actions tab.
      - **Docs** — links to the live site (https://robert-vetter.github.io/tessera/).
      - **License** — MIT (matches `LICENSE`).
- [ ] Every badge image URL resolves and every link target is correct
      (workflow path, Pages URL, license).
- [ ] **No badge for a capability that does not exist yet** — no coverage and no
      faithfulness/eval badge; their absence is noted as an explicit Phase 1
      follow-up (in the spec and/or a brief README comment).
- [ ] Pre-commit and the `gate` check stay green; the docs build is unaffected.

## Scope

**In:** a small, honest badge cluster (CI, Docs, License) in `README.md`, plus a
one-line note reserving the coverage and faithfulness badges for Phase 1.

**Out:** the **coverage** badge (needs coverage measurement — Phase 1), the
**faithfulness/eval** badge (needs the harness — Phase 1), dynamic/custom badge
endpoints, code-coverage tooling itself, and any change to CI or the eval. Also
out: a full README restructure — this only adds the badge row.

## Eval impact

None. Presentation only; it touches no faithfulness/coverage/quality metric (the
eval harness arrives in Phase 1). The *faithfulness badge* this enables later is
where the eval becomes visible — but that is explicitly future work.

## Risks / open questions

- **Badge set** — **confirmed minimal**: CI + Docs + License only (each a real,
  current fact). Leaves visual room for the faithfulness badge to stand out when
  it lands in Phase 1. Cheap to reverse — **no ADR**.
- **Badge provider** — GitHub-native badges (CI status) + shields.io (license,
  docs) is standard; shields.io is an external image dependency, acceptable and
  widely used.
- **Overclaiming guardrail.** The whole point is that badges stay truthful;
  faithfulness/coverage badges must wait until the numbers are real.
