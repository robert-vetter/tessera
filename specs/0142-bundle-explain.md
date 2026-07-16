# 0142. `tessera bundle explain` — a bundle made legible to a human

- **Phase / milestone:** ROADMAP3, a standalone feature on the Act-3 base
  (not one of the M22 units, which are the public-proof track). Improves
  the presentability of the trust-bundle work.
- **Issue:** —
- **Status:** approved (autonomous session).

## Problem

`tessera verify` proves a bundle re-derives; but a person handed a `.tsb`
file — an auditor, a reviewer, a hiring manager — cannot *read* it: it is
a 400 KB canonical-JSON blob. The whole value of a trust bundle is that a
human can follow the chain from an answer down to the exact evidence and
back up to the action. This unit adds a read-only presentation surface:
`tessera bundle explain <file>` renders the chain as a compact, readable
tree — question, each claim with its re-derived verdict, the evidence each
claim cites (source + locator + snippet), and, for an action bundle, the
wire request and its per-slot provenance. It is the demo/audit view that
makes the format's promise visible.

## Decisions

1. **Read-only projection, no new trust.** `explain` renders exactly what
   `verify` computes — it calls `verify_bundle` and presents the
   `VerifyReport` plus the reconstructed chain. It asserts nothing verify
   does not; a tampered/degraded bundle is shown with its real verdict at
   the top, so `explain` can never dress a failing bundle as sound.
2. **Two renderers, one model.** A pure `explain_bundle(bundle) ->
   Explanation` builds a structured, serializable view; a text renderer
   prints the human tree, and `--json` emits the structured view for
   tooling. (No new colour/UI dependency — plain text, the ADR-0027
   stdlib-surface posture.)
3. **What the tree shows.** Header: file, format, engine pins, the verify
   verdict + taxonomy + signature line (reused from the verify report).
   Then, per claim: the verdict chip (`re-derived ✓` / `UNSUPPORTED` /
   recorded-only), the claim text, and each cited record indented beneath
   as `source (locator) — "snippet"` (snippet truncated). For a refusal:
   the refusal reason. For an action bundle: a section rendering method,
   path, the body, and each slot's value → provenance. Evidence not cited
   by any claim (the rest of the packaged closure) is summarized as a
   count, not dumped.
4. **Truncation is honest.** Long snippets/bodies are elided with `…` and
   a character count, never silently cut; `--full` prints untruncated.
5. **CLI:** `tessera bundle explain <file> [--json] [--full]` via the
   existing front-door `bundle` dispatch (a new `explain` subcommand under
   `tessera bundle`, so `tessera bundle "<question>"` — a bare question —
   stays unaffected: `explain` is only taken as the first token after
   `bundle`). Reuses the verify path, so it stays stdlib-only and offline.

## Scope

**In:** `tessera/bundle/explain.py`, the `explain` sub-dispatch in
`tessera/bundle/cli.py`, BUNDLE.md "Reading a bundle" section,
`tests/test_bundle_explain.py`.
**Out:** any change to verify/emit/format; colour/TUI; HTML rendering
(the hosted UI is a separate surface).

## Acceptance criteria

- [ ] `explain` on a grounded answer bundle prints the question, each
      claim with its verdict, and cited evidence with source+locator; on
      a refusal bundle prints the refusal reason; on an action bundle
      prints the wire request + per-slot provenance.
- [ ] The verdict shown equals `verify`'s verdict; a tampered bundle
      shows FAIL/DEGRADED/TAMPERED at the top (explain never launders a
      bad bundle).
- [ ] `--json` emits a structured `Explanation` that round-trips; `--full`
      disables truncation.
- [ ] `tessera bundle "<a bare question>"` still emits (not mistaken for
      explain); `tessera bundle explain <file>` dispatches to explain.
- [ ] Stdlib-only (no extra pulled); gate green; six eval lines
      byte-identical.

## Eval impact

None — additive read-only presentation surface.

## Risks / notes

- `explain` must never imply soundness a bundle lacks — the verdict line
  is rendered first and unmistakably, and a non-PASS verdict is stated in
  the header, tested explicitly.
- Truncation defaults are for readability; `--json`/`--full` give the
  complete data, so nothing is hidden from a machine consumer.
