# 0140. The forged-bundle challenge — a downloadable "spot the lie"

- **Phase / milestone:** ROADMAP3 Milestone 22 (the public proof), unit 3
  of that milestone. Trust-bearing — pre-merge adversarial review.
- **Issue:** —
- **Status:** approved (autonomous session, per spec 0131 D10/D12).

## Problem

The act's claim is easiest to *show*: here are two trust bundles. One is
honest. One is a **cryptographically perfect fake** — a valid hash chain,
a recomputing manifest, an internally plausible answer — that is
nonetheless *false*. Every signature-style verifier passes both. One
offline command tells them apart. This unit ships that challenge as a
committed, reproducible artifact plus the doc that frames it, so a
stranger can download the two files and separate them with
`tessera verify` (and see, with the foil, that integrity-checking
cannot).

## Decisions

1. **Deterministic, committed forgery — the forgery is itself
   auditable.** `scripts/forge_challenge_bundle.py` builds the honest
   bundle from a committed **synthetic** corpus and derives the forgery
   from it by a single, documented edit, then re-seals. It is committed
   and deterministic, so anyone can re-run it and confirm exactly how the
   fake was made — the forgery hides nothing. **No SALT-derived values
   ever** (spec 0130 rule): the challenge uses the business synthetic
   corpus only.
2. **The forgery is subtle and evidence-clean.** The edit nudges the
   *stated conclusion* of the aggregate claim (e.g. a customer's total by
   a few thousand) while leaving every cited evidence row **untouched and
   plausible**. So `explain` on the forged bundle reads as a normal,
   well-sourced answer; only re-summing the cited rows exposes the lie.
   This is the honest hard case: the fake is not a garbled file, it is a
   confident, well-cited, wrong answer — exactly what an ungated agent
   produces.
3. **Both bundles are committed** under `data/challenge/`
   (`honest.tsb`, `forged.tsb`), each byte-stable (the canonical-bytes
   guarantee), so the challenge is a fixed target a reader can diff. A
   test pins that `honest.tsb` verifies PASS and `forged.tsb` verifies
   FAIL naming the broken claim, that the foil (integrity-only) reports
   **both** intact, and that the two files are regenerable byte-for-byte
   from the script (so they can never silently drift from the forge
   logic).
4. **`docs/CHALLENGE.md`** frames it: the two files, the one command, the
   foil contrast, what each outcome means, "build a better forgery" (the
   invited attack — a fake that survives `tessera verify` is a reportable
   finding), and the honest scope (synthetic corpus; the claim is
   offline claim-vs-evidence re-execution, not world truth). README gains
   a short challenge pointer.
5. **The LLM-judge contrast is run once (Q2 = yes) and reported honestly,
   whatever it shows.** `scripts/llm_judge_contrast.py` scores the forged
   bundle's claims with an LLM faithfulness judge (Claude via the existing
   `ANTHROPIC_API_KEY`). **The LLM is the measured subject, never a
   component of the trust path.** The recorded result (docs/CHALLENGE.md)
   is the *actual* one: with a fair, attributed context a capable model
   re-summed the small 3–5-row aggregates correctly (so the naive "LLM is
   fooled" slogan does **not** hold at toy scale), but the same claim
   earned the opposite verdict under a slightly different context framing,
   and at 0.95 confidence rejected a true claim. The honest, durable point
   is therefore **non-determinism + prompt-framing dependence + no
   re-runnable recomputation**, not "LLMs are dumb." The script is
   import-guarded (no key → guidance, exit 0, never CI); the result is one
   measurement with the model + prompt disclosed, never a CI-gated claim.
   (The project's ethos applied to itself: report what the experiment
   shows, not what would sound best.)
6. **No network or spend in CI or the gate.** The committed bundles + the
   verify/foil pins are the CI surface; the LLM contrast is a manual
   one-shot.

## Scope

**In:** `scripts/forge_challenge_bundle.py`,
`scripts/llm_judge_contrast.py`, `data/challenge/{honest,forged}.tsb`,
`docs/CHALLENGE.md`, README pointer, mkdocs nav,
`tests/test_challenge.py`.
**Out:** Rekor anchoring (0138), the compliance mapping (0139), the
write-up (0141); any non-synthetic data; any CI network/spend.

## Acceptance criteria

- [ ] `data/challenge/honest.tsb` verifies **PASS** (exit 0);
      `forged.tsb` verifies **FAIL** (exit 2) naming the broken claim.
- [ ] The foil (`scripts/foil_integrity_only.py`) reports **both**
      `INTACT` — integrity-checking cannot tell them apart.
- [ ] Both committed bundles are byte-identical to a fresh
      `forge_challenge_bundle.py` run (the forgery cannot drift from its
      script).
- [ ] The forged bundle's cited evidence is untouched vs the honest one
      (the lie is in the conclusion, not the evidence) — pinned.
- [ ] `llm_judge_contrast.py` runs without a key (prints guidance,
      exit 0) and, with a key, scores the forged claims + records the
      result; it never enters CI or the gate.
- [ ] No SALT-derived values anywhere in the challenge.
- [ ] Gate green; six eval lines byte-identical.

## Eval impact

None — committed artifacts + scripts + docs.

## Risks / notes

- **The forgery must be a true false-PASS for integrity-only, not a
  broken file.** If the foil reported anything but INTACT on the forged
  bundle, the challenge would be dishonest — pinned by the foil test.
- **Reproducibility vs drift:** committing the bundles risks them
  drifting from the script; the byte-identity test forbids that.
- **LLM contrast honesty:** it is an LLM-judge in the evaluator mold
  (Claude), not the RAGAS package; `docs/CHALLENGE.md` says exactly what
  was run and why (reproducibility/robustness over a heavy, network-flaky
  dependency), and scopes the result as one measurement, not a benchmark.
