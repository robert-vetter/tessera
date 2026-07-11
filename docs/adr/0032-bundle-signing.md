# 0032. Bundle signing: Ed25519 over the root, verification stays stdlib-only

- **Status:** accepted (2026-07-10, spec 0135; plan spec 0131)
- **Context:** ROADMAP3 Milestone 21 — binding a trust bundle to its origin
  without breaking the property that made Milestone 20's claim honest.

## Context

Milestone 20 shipped with an honest limit on the record: an unsigned
bundle proves integrity and re-derivability, **not origin**, and a
content tamperer can freely re-seal (recompute the manifest and root).
This unit adds the origin binding. The constraint is that it must not
cost the load-bearing property of the whole act — that a stranger can
verify a bundle **offline with nothing but the standard library**
(spec 0131 D2). Signing needs real cryptography; verification must not.

## Decision

### What is signed

The UTF-8 bytes of `integrity.root`. The root already commits every
sealed section (ADR 0031), so a signature over it is a signature over
the bundle. Signing a second serialization would only introduce a second
canonicalization to get wrong. The signature is an attestation **over**
the root and is structurally excluded from the manifest it attests
(ADR 0031 §4) — a signature inside its own signed content is circular.

### Signature section

```json
{"algorithm": "ed25519", "public_key": "<64 hex>", "signature": "<128 hex>"}
```

No timestamp. Bundles are byte-stable and deterministic by design;
trusted time is a transparency-log property (unit 0138), not a
self-asserted field a bundle can claim about itself.

### Ed25519, and the split that keeps verify stdlib-only

- **Signing** uses libsodium via PyNaCl, behind a new optional extra
  `sign = ["pynacl>=1.5"]` (the `cloud`/`salt`/`agent` opt-in pattern),
  imported lazily in `bundle/signing.py`. A secret key never touches the
  default path.
- **Verification** is an in-repo, **pure-Python RFC 8032**
  implementation (`bundle/ed25519.py`), verify-only. It is pinned
  against the RFC 8032 §7.1 test vectors and cross-checked against
  libsodium-produced signatures (that test skips without the extra). A
  pure-Python Ed25519 is the unit's real risk; making it verify-only
  (no secret handling) and pinning it to the standard's own vectors
  means a wrong implementation fails those pins — it cannot silently
  pass. Speed is irrelevant: one verification is tens of milliseconds.

Ed25519 (not ECDSA/RSA) because it is small to implement correctly, has
no per-signature randomness to mishandle on the verify side, and its
test vectors are canonical.

### Keys

`tessera bundle keygen` writes a 32-byte seed (hex, `0600`) to
`var/keys/bundle_signing.key` and the public key to `…​.pub`, refuses to
overwrite, and prints the public key. `var/` is already gitignored;
keys never enter CI.

### Verify semantics and honest scope

`signature: null` → reported as `UNSIGNED` (not a failure by default;
`--require-signed` makes it exit 4 for consumers whose policy demands
origin). A present signature is verified against the stored root **after**
the root is re-computed from content: a re-sealed tamper breaks the
signature (the keyholder did not sign the new root); a content tamper
without re-seal breaks integrity first. Both are exit 4, named. A
malformed signature section is an envelope error (exit 4).

The binding is to **the holder of this key**, not to an identity. The
report and `--json` carry the public key so a consumer can compare it to
a key they already trust; Tessera never claims "the right person." Key
distribution, transparency, and rotation are deliberately **out of
scope** for this act and stated as such in BUNDLE.md — overreaching into
an identity claim we cannot substantiate would be exactly the kind of
overclaim the project forbids.

## Consequences

- A re-sealed tampered bundle now fails for anyone but the keyholder —
  the origin gap Milestone 20 documented is closed to the extent a
  signature can close it.
- `tessera verify` remains stdlib-only: the leak-guard test asserts the
  verify surface pulls no `nacl`.
- The act gains a real crypto dependency, but only opt-in on the signing
  side; CI stays extra-free and key-free.
- Unsigned bundles remain first-class (integrity + re-derivability),
  so the offline re-execution story does not require a key to be useful.
