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
3. **Verify re-derives the action from the packaged evidence**, three
   deterministic checks, all pure functions over the file's content:
   - **Request reconstruction (added-nothing).** Re-render the wire body
     from the receipt's own slots with the engine's own `render_body`
     (a pure template) and require it to equal the recorded body; for an
     incident, the recorded `title` must equal the title slot's value;
     for a PR comment, the recorded path must carry the resource slot's
     value. A body that adds anything beyond its slots fails.
   - **Slot-to-claim binding.** Every wire slot's value must be faithful
     to a **re-derived, verified** claim — identical to a claim's text,
     or a normalized-containment fragment of one of that claim's cited
     records (exactly the frozen `_field` faithfulness rule, re-run
     here against the re-derived claims, not the recorded ones). A slot
     value backed by no verified claim is a fabricated wire value and
     fails.
   - **Referential.** Every slot's cited evidence id resolves to a
     packaged node (the M20 referential rule, extended to slots) — no
     dangling wire provenance, no crash.
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
