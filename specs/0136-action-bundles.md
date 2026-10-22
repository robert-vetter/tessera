# 0136. Action bundles — the wire request re-derives from the evidence

- **Phase / milestone:** ROADMAP3 Milestone 21, unit 2 (plan: spec 0131).
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0131). Trust-bearing —
  pre-merge 3-lens adversarial review required.

## Problem

Milestone 20 bundles an *answer*. But Tessera's whole point is that it
also *acts* — and an action (a GitHub issue, a PR comment) is where a
wrong claim does damage. This unit packages the action chain into the
bundle's reserved `action` section and extends `tessera verify` to
re-derive it offline: every value that went onto the wire must trace to
a verifier-passing claim, and the exact request must reconstruct from
those values. A bundle that recorded an action whose wire body smuggled
an ungrounded token, or whose request does not match its own slots, must
fail.

## Decisions

1. **The `action` section is the `ExecutionReceipt` dict** (already
   reserved and hashed as a leaf since ADR 0031; serde already
   round-trips it, unit 0132). It carries the wire request
   (method/path/body), the grounded slots (each a value + verdict +
   provenance), the actuator, the approval, and the outcome.
2. **Emit scope: grounded, simulated actions.** `build_action_bundle(
   action, domain, question)` builds the answer bundle for
   `(domain, question)`, runs the action through the **simulated**
   actuator (`execute_action`, sends nothing), and packages the receipt.
   It raises if the action is not fully grounded — a withheld/refused
   action carries no wire request to verify; bundling Tessera's "no" is
   already demonstrated by the answer-refusal bundle (M20) and a
   withheld-action bundle is named future work. No real send is ever
   bundled here (the one recorded real send stays the M15 fixture).
3. **Verify re-derives the WHOLE action from the packaged evidence** —
   the action-layer analogue of the answer re-derivation (b). Re-run the
   frozen drafting + rendering pipeline (`actions._draft_fields` +
   `payloads.render_payload`) over the **re-derived** `result` (bound to
   the packaged evidence by check (b)) and require the recorded receipt's
   `method`, `path`, the **entire** `body` dict, and the `slots` to equal
   it exactly. Because the pipeline is a deterministic function of the
   answer, one equality check binds every wire detail at once: the
   method, the endpoint template, every body key (including `labels` and
   anything an attacker might inject), the per-slot value→claim→role
   attribution, and the slot order. A receipt claiming a real send
   (`sent=true`) is rejected — only simulated actions are bundled.
   **(Design note: the adversarial pre-merge review found that an
   earlier field-by-field version — re-rendering only `body['body']` and
   the title, binding slot values to *any* verified claim — let three
   attacks pass: injected `labels`/`assignees`/`milestone` body keys, a
   repointed method/path, and a cross-claim value splice under the wrong
   section. Reconstructing the entire request through the frozen pipeline
   and requiring full equality closes all three by construction; the
   receipt cannot add or alter anything the evidence does not produce.)**
4. **Failures are semantic (exit 2), named per slot.** Action problems
   join `structural_problems`, so the existing exit precedence
   (4 > 2 > 3 > 0) and the signature/integrity envelope are unchanged.
   An action bundle whose *answer* also fails re-derivation fails for
   both reasons.
5. **CLI:** `tessera bundle --action <incident|pr_summary> "<q>"
   --domain <d>` emits an action bundle (composes with `--sign`); a
   not-grounded action is a clean error (exit 2), never a traceback.
   The verify command is unchanged — it detects the `action` section and
   checks it automatically.
6. **Honesty:** the action re-derivation binds *wire value → verified
   claim → packaged evidence*. It does **not** re-run the actuator or
   the idempotency pre-check (those touch the network seam and the
   module engine); BUNDLE.md states that what a re-executed action
   bundle proves is that every sent value was grounded and the request
   adds nothing — not that the send happened (simulated bundles record
   `sent=false` by construction).

## Scope

**In:** `emit.build_action_bundle`, verify action checks
(`bundle/verify.py`), `--action` on the CLI, BUNDLE.md action section,
`tests/test_bundle_action.py`.
**Out:** withheld/refused-action bundles (future), real-send bundles
(never — the M15 fixture is the one recorded send), the floors artifact
+ CI matrix (0137), Rekor (0138).

## Acceptance criteria

- [ ] An action bundle (incident on devex + github_actions; pr_summary
      on devex) verifies to exit 0: answer re-derives, request
      reconstructs, every slot binds to a verified claim.
- [ ] Tamper a wire slot value to an ungrounded token + re-seal →
      exit 2 naming the slot; tamper the body away from its slots →
      exit 2; a dangling slot evidence id → exit 2 (not a crash).
- [ ] A signed action bundle: re-seal breaks the signature (unit 0135
      composes).
- [ ] Non-action bundles behave exactly as in Milestone 20 (the
      `action` section stays `null`, no action checks run).
- [ ] Gate green; six eval lines byte-identical; the frozen agent code
      is untouched (verify consumes `render_body` and the receipt, adds
      no new answer/action path).

## Eval impact

None — additive verification of an existing serialized object.

## Risks / notes

- The slot-to-claim faithfulness rule is re-implemented in verify (a
  containment predicate); it must match the frozen `_field` rule exactly
  or an honest action bundle could false-fail. Pinned by round-tripping
  every committed action through emit→verify at exit 0.
- `render_body` is imported from the agent layer (pure, stdlib) — verify
  stays extras-free; the leak-guard is extended.

## Addendum (2026-07-11) — post-close audit: the whole receipt is re-derived

The comprehensive M20+M21 review found that binding only the wire
*request* (method/path/body/slots) left the receipt's **execution
outcome** unbound: a re-sealed bundle could set `outcome="created"`,
`simulated=false`, and a fabricated `result` (a real-looking GitHub issue
URL) — or forge `approved=true` — and still verify PASS, because only
`sent` was checked. Fixed by re-running the **simulated execution**
(`execute_payload`) over the re-derived request and requiring the *whole*
receipt to match: outcome, result, simulated/executed/actuator, approval,
and the request. A bundled action is only ever an unapproved, unsent
simulation, so any deviation is a named semantic failure (exit 2). Pinned
by `test_forged_execution_outcome_fails` and `test_forged_approval_fails`,
and by the `outcome_forgery` / `approval_strip` classes in the
Auditability Floor.
