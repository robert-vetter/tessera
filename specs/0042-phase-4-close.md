# 0042. Phase 4 close: the stranger pass, the changelog, the tag

- **Phase / milestone:** Phase 4 — platform, polish, and the story (spec 0035 Unit 8)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

The phase milestone is "a senior engineer can clone, run, read, and understand
the project without the author in the room." The capabilities exist; what
remains is making the front door tell the truth about them: the README still
shows the pre-fix devex coverage, doesn't mention `tessera-chat`, the
deployment doc, or the write-up — and one sentence **overclaims** (it asserts
agentic workflows and MCP support that do not exist; CLAUDE.md forbids
exactly this). The CHANGELOG needs its phase-4 section and its stale compare
links fixed; STATUS needs the closing `/wrap` entry; the tree needs the
`phase-4` tag.

## Acceptance criteria

- [ ] README stranger pass: current eval output (both batteries 1.000, with
      the closed-loop story), `tessera-chat` as the flagship door, the
      DEPLOYMENT/WRITEUP links, the gate described as `scripts/gate.sh`, the
      Status section current — and the agentic/MCP **overclaim corrected** to
      the truthful "future work" framing.
- [ ] `docs/index.md` links the write-up and deployment doc.
- [ ] CHANGELOG: `[phase-4]` section covering the six shipped units; the
      footer compare-links completed (`phase-2`/`phase-3` were missing,
      `Unreleased` pointed at `phase-1`).
- [ ] Final verification: gate green; tests under several `PYTHONHASHSEED`
      values; strict docs build; gitleaks; a phase-close `tessera-eval
      --record` checkpoint.
- [ ] STATUS `/wrap` entry appended; `phase-4` tagged on the merged close
      commit and pushed.

## Scope

**In:** the documents above, the record, the tag. **Out:** any code change
(a polish unit that changes behaviour at close would be untested behaviour);
rewriting historical STATUS/CHANGELOG entries (append-only).

## Eval impact

None — the close records the standing numbers as a checkpoint
(business 7/52, devex 7/24, all four batteries' metrics 1.000).

## Risks / open questions

- ADR 0007 trigger 2 (synthetic-battery saturation) is now true of both
  batteries — carried into STATUS as the named open question for the next
  milestone rather than padded mid-close.
