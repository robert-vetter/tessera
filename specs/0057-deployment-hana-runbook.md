# 0057. Deployment runbook for HANA-native embeddings + .env.example + app user

- **Phase / milestone:** Milestone 6 — Embeddings on SAP (Unit 7 of 9; plan 0051)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

The recorded run (U8) needs a written, copy-paste path: enable the HANA NLP
feature, create a least-privilege app user (not `DBADMIN`), smoke-test
`VECTOR_EMBEDDING`, and run the online eval. This unit writes that runbook, ships
a secret-free `.env.example`, and tells the honest verified-vs-not story for the
HANA embedding path (verified offline; the live call is U8). Docs-only.

## Acceptance criteria

- [ ] `docs/DEPLOYMENT.md` gains a **"Semantic retrieval on HANA Cloud — the
      recorded path"** section: NLP feature enable, the dedicated-user +
      schema SQL, `uv sync --extra cloud`, the `VECTOR_EMBEDDING` smoke test, and
      the one-shot `TESSERA_EMBEDDINGS=hana tessera-eval --record` command.
- [ ] A committed, **secret-free** `.env.example` (placeholders only) — and
      `.gitignore` un-ignores exactly it (`!.env.example`) while still ignoring
      real `.env*`.
- [ ] The verified-vs-not split states the HANA embedding path is *designed +
      contract-tested* offline; the live call + recorded close are U8.
- [ ] Connecting as a **dedicated least-privilege user** (own schema, no system
      privileges) is the documented default; `DBADMIN` is called out for
      rotation.

## Scope

**In:** `docs/DEPLOYMENT.md` runbook + verified-vs-not update; `.env.example`;
the `.gitignore` exception.

**Out:** running anything against HANA (U8); code (none). The SQL and model
version are confirmed against the live instance at the U8 smoke test — the
runbook says so rather than pretending certainty.

## Eval impact

None — docs only. Batteries unchanged; the github_actions offline miss recorded
in U6 stands until U8's online close.

## Risks / open questions

- **`.env.*` would ignore `.env.example`.** Fixed with `!.env.example`; a test
  isn't warranted but the commit must show `.env.example` actually tracked.
- **Exact privilege for `VECTOR_EMBEDDING`** may vary by instance; the runbook
  says to grant the documented NLP/embedding privilege if a call is refused,
  rather than asserting a grant that may be wrong.
- **gitleaks** must not flag the template — placeholders only, no real secret.
