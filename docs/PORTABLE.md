# Two implementations, one format — verify it in JavaScript

*Milestone 22 (spec 0148, ADR 0038). The guarantee is the format, not my
Python — and here is the second implementation that proves it.*

```console
$ node verifier/js/tessera-verify.mjs data/challenge/honest.tsb
integrity: intact — every leaf and the root re-computed
claims:    3/3 re-executed and matched
verdict:   PASS-PARTIAL (exit 0)

$ node verifier/js/tessera-verify.mjs data/challenge/forged.tsb
claims:    1/3 re-executed and matched
  ! claim 0: recorded verified=true but re-execution says false
  ! claim 2: recorded verified=true but re-execution says false
verdict:   FAIL (exit 2)
```

Zero dependencies, Node standard library only, ~600 lines. It was written
from the format contract — [ADR 0031](adr/0031-trust-bundle-format.md)
(format), [0032](adr/0032-bundle-signing.md) (signing),
[0033](adr/0033-chained-bundles.md) (chains),
[0035](adr/0035-verifiable-approvals.md) (approvals) and this document's
sibling [BUNDLE.md](BUNDLE.md) — **not** by translating the Python.

## Why this exists

The strongest objection to everything in Milestones 20–22 is not about
cryptography. It is: *the benchmark, the proof and the verifier were all
written by the same person.* No further work by that person answers it. A
second implementation does — if two verifiers in different languages agree
case by case, the property lives in the format.

## What the portable verifier does — and what it cannot

| check | portable? |
|---|---|
| canonical bytes, leaf manifest, Merkle root | ✅ |
| section-set commitment, reserved `anchor` refusal | ✅ |
| Ed25519 signature over the root | ✅ (`node:crypto`) |
| detached approval artifacts (ADR 0035) | ✅ |
| referential integrity of citations | ✅ |
| **claim-level re-execution** (aggregate, compare, superlative, count, refuse-to-sum, shared-fragment, containment, chain citation) | ✅ |
| **recursive chain verification** of embedded upstreams | ✅ |
| answer re-derivation (re-run the domain router) | ❌ needs the engine |
| action re-derivation (re-run the drafting pipeline) | ❌ needs the engine |
| `conflict_disclosure` grammar (document date parsing) | ❌ reported `NOT-EVALUABLE` |
| duplicate-JSON-key rejection | ❌ host parser is last-wins |

Because of the two ❌ engine-bound checks, this implementation **can never
report a full PASS**. Its best verdict is **`PASS-PARTIAL`**: *everything I
can check passes; those two were not performed* — and it prints that line
every run. A silent scope gap would look like agreement while proving
nothing; the taxonomy makes the gap impossible to hide.

## The differential contract, enforced in CI

| rule | meaning |
|---|---|
| `TAMPERED` ⟹ reference exits 4 | envelope failures agree |
| `FAIL` ⟹ reference exits 2 or 4 | **the portable verifier never rejects what the reference accepts** |
| `PASS-PARTIAL` + reference failure | allowed **only** when every named reference cause is one of the two non-portable checks — verified per case against the reference's own problem strings |

Measured over the committed kit (`data/kit/expectations.json`): **25 cases
— the committed artifacts crossed with the CI-pinned attack battery — 12
caught by both implementations, 7 declined by design, 6 honest baselines
passing in both, 0 disagreements.** The declined seven are exactly the
attacks that need the router or the drafting pipeline; if that set ever
grows, a test fails.

## What writing it found

An independent implementation is also a specification review, and this one
found a real defect within an hour: **`tessera-canonical-json-1` was
under-specified for numbers.** Python writes a float `1.0` as `1.0`; a
language without an int/float distinction re-emits `1` after parsing — and
the resolution/mention sections carry float confidence scores, so a
portable verifier computed different digests and reported a **false
TAMPERED** on a perfectly honest bundle.

The fix is in the specification, not in one program: canonical bytes
preserve a number's **lexical form**, and an implementation that cannot
recover it must refuse to verify rather than guess. Recorded in the
[ADR 0031 addendum](adr/0031-trust-bundle-format.md). No emitted byte
changed — every committed root is untouched — but the recipe is now
implementable *from the document*, which is the property that makes a
format portable instead of a description of one program.

## The same verifier, in a browser tab

Because the core has zero imports, the *same file* runs in a page:
[**verify.html**](verify.html) — drop a `.tsb` on it and the verdict
appears in a second. It is generated from `verifier/js/verify-core.mjs`
(so it cannot drift), ships as **one self-contained file** with no CDN and
no build step, and — the property that matters for a trust tool —
**contains no network API at all**: no `fetch`, no `XMLHttpRequest`, no
form, no external reference. Your file never leaves your device, and that
sentence is a pinned test rather than a promise. Disconnect your network
and it still works.

Two example bundles are embedded (honest and forged, ~37 KB each) so the
demo needs no download either. Ed25519 signature checking is the one thing
the browser build omits, and it says so when it meets a signed bundle.

## Reproduce it

```console
$ node verifier/js/tessera-verify.mjs <bundle.tsb> [--approval a.json] [--json]
$ uv run python scripts/build_conformance_kit.py   # regenerate the kit
$ uv run pytest tests/test_portable_verifier.py    # the differential harness
```

Node ≥ 21 is required (the verifier needs JSON source-text access to
reproduce canonical bytes; on older runtimes it refuses rather than
guesses). CI installs Node and runs the harness, so a disagreement fails
the build like any other red test.

**Named future work:** a third implementation (Rust or Go), and publishing
the format as an RFC-style document so the contract stands entirely on its
own.
