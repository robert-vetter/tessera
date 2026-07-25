# tessera-verify.mjs — an independent verifier

A second implementation of the Tessera trust-bundle contract, in
JavaScript, with **zero dependencies** (Node standard library only).

```console
$ node tessera-verify.mjs ../../data/challenge/honest.tsb
$ node tessera-verify.mjs ../../data/challenge/forged.tsb --json
$ node tessera-verify.mjs bundle.tsb --approval approval.json
```

Exit codes mirror the reference verifier: `0` pass · `2` semantic failure ·
`3` not evaluable here · `4` envelope broken.

It was written from the format contract (ADR 0031/0032/0033/0035 and
`docs/BUNDLE.md`), not translated from the Python, so that agreement
between the two says something about the *format*.

**It cannot report a full PASS.** Answer re-derivation and action
re-derivation need the engine; this implementation declines them openly
and its best verdict is `PASS-PARTIAL`. The full scope table, the
differential contract and the measured cross-implementation results are in
[`docs/PORTABLE.md`](../../docs/PORTABLE.md).

Requires Node ≥ 21 (JSON source-text access is needed to reproduce
canonical bytes; on older runtimes it refuses rather than guesses).
