# 0135. Bundle signing — Ed25519 over the root, verify stays stdlib-only

- **Phase / milestone:** ROADMAP3 Milestone 21, unit 1 (plan: spec 0131).
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0131).

## Problem

Milestone 20 closed with an honest limit on the record (BUNDLE.md):
unsigned bundles prove integrity and re-derivability, **not origin** —
and a content tamperer can freely re-seal (recompute manifest + root).
This unit adds the origin binding: an Ed25519 signature over the sealed
root, so re-sealing is no longer free for anyone but the keyholder —
while keeping the promise that made Milestone 20's claim honest:
**`tessera verify` stays stdlib-only** on a clean clone.

The dependency and byte-level choices are hard to reverse (ADR 0032).

## Decisions (rationale in ADR 0032)

1. **What is signed: the UTF-8 bytes of `integrity.root`.** The root
   already commits every sealed section (ADR 0031), so signing it signs
   the bundle; signing a second serialization would only add a second
   canonicalization to get wrong. The signature is an attestation OVER
   the root and never enters the manifest (ADR 0031 §4).
2. **Signature section shape:**
   `{"algorithm": "ed25519", "public_key": "<64 hex>", "signature": "<128 hex>"}`.
   No timestamp — bundles stay byte-stable and deterministic by design;
   trusted time is unit 0138's job (transparency anchoring), not a
   self-asserted field.
3. **Signing needs the `sign` extra (PyNaCl); verification never does.**
   `pyproject` gains `sign = ["pynacl>=1.5"]` (the `cloud`/`salt`/`agent`
   opt-in pattern); `bundle/signing.py` imports it lazily. Verification
   is an in-repo, pure-Python RFC 8032 Ed25519 implementation
   (`bundle/ed25519.py`, verify-only — no secret ever touches the
   stdlib path), tested against the RFC 8032 §7.1 vectors and against
   PyNaCl-produced signatures (that cross-check test is skipped without
   the extra, like the MCP tests). Slow is fine; one verify is
   milliseconds-to-tens-of-milliseconds.
4. **Keys:** `tessera bundle keygen` (requires the extra) writes
   `var/keys/bundle_signing.key` (32-byte seed, hex, `0600`) and
   `…​.pub` (hex), refuses to overwrite, prints the public key. `var/`
   is already gitignored; keys never enter CI.
5. **CLI:** `tessera bundle … --sign [--key <path>]` signs after
   sealing (default key path from decision 4; a missing key or missing
   extra is a clean error, exit 2). `tessera verify` gains
   `--require-signed` (unsigned ⇒ envelope failure, exit 4) for
   consumers whose policy demands origin; the default stays report-only.
6. **Verify semantics.** `signature: null` → reported plainly:
   `UNSIGNED — integrity proves the file is the file, not who made it`;
   exit unchanged. Signature present → verified pure-Python against the
   *stored* root **after** the root itself re-computed: a re-sealed
   tamper breaks the signature (the keyholder didn't sign the new
   root), a stale root breaks integrity first — both exit 4, named.
   Malformed signature section (wrong lengths, unknown algorithm) →
   `BundleFormatError`, exit 4. The verify report and `--json` carry
   the public key so a consumer can compare it against a key they
   trust; verify itself never claims "the right person" — only "the
   holder of this key" (the honest scope; key distribution is out).

## Scope

**In:** `bundle/ed25519.py` (pure-Python verify), `bundle/signing.py`
(sign + keygen, lazy extra), CLI extensions (`--sign`, `--key`,
`keygen`, `--require-signed`), verify integration, pyproject extra,
ADR 0032, BUNDLE.md signature section update,
`tests/test_bundle_signing.py`.
**Out:** action bundles (0136), the floors artifact + CI matrix (0137),
Rekor anchoring and any trusted-time story (0138), key
distribution/rotation (documented as out of scope).

## Acceptance criteria

- [ ] RFC 8032 §7.1 test vectors (TEST 1–3) pass against
      `bundle/ed25519.py`; a flipped bit in message, signature, or key
      fails.
- [ ] PyNaCl-signed bundle verifies pure-Python (test skipped cleanly
      without the extra); tamper-then-reseal breaks the signature
      (exit 4, named); stale root breaks integrity (exit 4).
- [ ] Unsigned bundles behave exactly as in Milestone 20; the report
      labels them; `--require-signed` fails them with exit 4.
- [ ] `keygen` round-trip: keygen → sign → verify green; second keygen
      refuses to overwrite.
- [ ] Verify path stays extras-free (leak-guard test extended: importing
      the verify surface pulls no `nacl`).
- [ ] Gate green; six eval lines byte-identical; CI stays key-free and
      extra-free.

## Eval impact

None — additive signing surface; the eval and Milestone-20 floors are
untouched.

## Risks / notes

- A pure-Python Ed25519 is the unit's real risk; it is verify-only
  (no secrets), pinned to the RFC vectors, and cross-checked against
  libsodium — a wrong implementation fails those pins, it cannot
  silently pass.
- The signature binds a bundle to a *key*, not to an identity — stated
  in BUNDLE.md; anything stronger (key transparency, identity binding)
  is deliberately out of scope for this act.
