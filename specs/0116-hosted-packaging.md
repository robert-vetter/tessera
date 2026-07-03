# 0116. Milestone 17 Unit 5: hosted packaging, demo script, one-pager

- **Phase / milestone:** Milestone 17 Unit 5 (close) — see spec 0112.
- **Issue:** —
- **Status:** implemented (agent's part); the deploy + video are the maintainer's

## Problem

The web surface (Unit 3) and the agent demo (Unit 4) exist; what remains is to
make the surface *hostable* and to hand the maintainer the assets that turn it
into a shareable demo — the Z Fellows "a live demo anyone can try" commitment.

## Acceptance criteria

- [x] **Hostable, key-free:** the existing image already carries the
      `tessera-ui` entry point; `tessera-ui --host 0.0.0.0 --port <p>` binds
      publicly (verified). No secrets on a public instance — narration/HANA/
      GitHub stay off by default (ADR 0027).
- [x] **Deploy runbook** ([`docs/DEMO.md`](../docs/DEMO.md) §1): three
      free/cheap options (Fly.io, Railway/Render, a small VM behind Caddy),
      the exact `docker run` command, and the honest operational note (build-
      per-request compute, no auth/rate-limit → reverse-proxy it, no secrets
      to protect).
- [x] **The 3-minute demo script** (§2): the post-Replit arc — claim proven →
      refusal → gated action/receipt → measured floor — as four clickable
      beats, each one URL, with the closing line and a technical coda
      (the recorded agent transcript).
- [x] **The one-pager** (§3): EN + a DACH-facing DE short form, in the fixed
      positioning ("say what it can prove / do what you approve"; sell the
      receipt; measured faithfulness; on-prem).
- [x] README points at `tessera-ui` + `docs/DEMO.md`; mkdocs nav updated;
      strict docs build green; gate green.

## Scope

**In:** the runbook + demo script + one-pager + the README/nav wiring.
**Out:** the actual deploy and the recorded video (maintainer — hosting is a
spend/account decision, ROADMAP2 #5); any code change (the UI is done);
auth/rate-limiting (the reverse proxy's job, noted).

## Eval impact

None — docs + packaging.

## Milestone 17 close

With Units 2–5 merged, M17's engineering is complete. Per spec 0112 decision 5,
the milestone **tags only when the hosted demo is live** — that step (pick a
host, deploy, record the video) is the maintainer's, so **M17 stays open at
session end**, reported honestly. Everything that does not depend on hosting
(narration live, the UI, the recorded agent session, the runbook + assets) is
landed and green.

## Risks / open questions

- A public instance exposes compute; the runbook says to rate-limit at the
  proxy. Acceptable for a demonstrator (ADR 0027).
- If the maintainer prefers a managed platform's build over the repo Dockerfile,
  the start command is the same (`tessera-ui --host 0.0.0.0 --port $PORT`).
