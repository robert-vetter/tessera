# 0111. Milestone 16 Unit 4: one-shot preparation + the Milestone-15 close checklist

- **Phase / milestone:** Milestone 16 (Act 2 opener), Unit 4 — see spec 0107.
  Also the execution contract for **Milestone 15's remaining Units 4–5** (the
  real send + close), whose planned numbers (0106/0107 in spec 0103) were
  consumed otherwise (see the `specs/README.md` numbering ledger).
- **Issue:** —
- **Status:** implemented (preparation); the send + close await the maintainer

## Problem

Everything before the one real send must be so prepared that the maintainer's
part is: mint a PAT, run two commands, verify one URL. The audit gated the send
behind the B1–B4 fixes (landed: specs 0109/0110); the runbook still described
the pre-0109 recorder behavior; the sandbox repo did not exist.

## What this unit did

- [x] **Sandbox repo created (public):**
      <https://github.com/robert-vetter/tessera-exec-oneshot>, with a README
      explaining its purpose — the one real issue lands somewhere harmless,
      public, and verifiable. (Recorded decision, spec 0107 #5.)
- [x] **`.env` prefilled** (gitignored, not in this diff):
      `TESSERA_EXEC_OWNER=robert-vetter`,
      `TESSERA_EXEC_REPO=tessera-exec-oneshot`, and a commented
      `TESSERA_GITHUB_TOKEN` placeholder with the mint URL. `.env.example`
      already documents all four variables.
- [x] **DEPLOYMENT runbook rewritten for the post-0109 recorder** (this was
      review finding F2, known-deferred to here): the concrete sandbox repo;
      the PAT recipe with the labels-silently-dropped note (harmless — dedup
      is label-independent since 0109); non-consummated approved attempts
      print + exit non-zero + persist nothing; **verify the printed issue URL
      is yours before committing** (the marker-spoof honesty step); once
      recorded, the recorder refuses re-runs — `exists` is the crash-recovery
      case, not a live demonstration; renderer-version key-stability note.
- [x] **`data/execution/README.md`** updated to the same persistence policy.

## The maintainer's two commands (after minting the PAT into `.env`)

```bash
set -a; source .env; set +a
uv run python scripts/record_real_execution.py                             # rehearsal
TESSERA_EXEC_APPROVE=true uv run python scripts/record_real_execution.py  # the send
```

Then: open the printed `html_url`, confirm it is your issue in your sandbox
repo.

## The Milestone-15 close checklist (any session executes this after the send)

1. `git checkout -b m15-close && git add data/execution/ && bash scripts/gate.sh`
   (gitleaks runs in pre-commit; the receipt is scrubbed by construction).
2. STATUS entry: the recorded real send (date, outcome, issue URL), in the
   M6/M7 "ran on X" style.
3. WRITEUP: the "actually sending behind approval" section — the send, the
   idempotency mechanism and its honest limits (ADR 0026 + addendum), the
   0109 hardening that preceded it.
4. README: the MCP/status wording flips from "nothing has been sent yet" to
   "sent exactly once, on the record" (link the receipt + issue); CHANGELOG
   rolls `[Unreleased]` into `[milestone-15]` (and the 0107–0111 items into
   `[milestone-16]`).
5. The ADR 0008 **empty-diff frozen-core audit** over `milestone-14..HEAD`
   (expected deltas outside the frozen list only: `agent/*`, `scripts/`,
   `eval/harness.py` — the sanctioned 0110 accounting change; everything on
   the frozen list must be empty-diff).
6. Tag `milestone-15`, then close Milestone 16 (STATUS wrap; tag
   `milestone-16` — spec 0107 decision 6), update memory, hand back the M17
   kickoff.

## Scope

**In:** the preparation above + this checklist. **Out:** the send itself
(maintainer-only, credentialed, irreversible — never performed by the agent);
any code change (0109/0110 landed them); M17+ work.

## Eval impact

None — docs + external preparation only; gate re-run green.

## Risks / open questions

- The sandbox repo is public: anyone can open issues there. The runbook's
  verify-the-URL step covers the (remote) marker-spoof case; running the
  one-shot soon after creation minimizes exposure.
- If the maintainer prefers a different sandbox repo, only `.env` changes —
  the runbook names the variables, not just the values.
