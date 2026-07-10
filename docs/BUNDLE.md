# Trust bundles — receipts a third party re-checks by re-execution

*Milestone 20 (specs 0131–0134, ADR 0031). One file per grounded answer;
`tessera verify` re-derives its verdicts offline, from the file alone.*

Every Tessera answer is claims with provenance, checked by a
deterministic verifier. Until now that check was only observable where it
ran: on the machine, with the corpus, inside the engine. A **trust
bundle** makes it portable — a single `.tsb` file carrying the answer,
the evidence it stands on, and everything needed for a stranger, offline,
to run the verification **again** and re-derive every verdict from the
file's own content.

That last part is the point, so it is worth stating against the obvious
alternative. Signed audit trails, hash chains, and Merkle-committed logs
prove *integrity*: the file was not altered since sealing. They prove
nothing about whether the content was ever true — a perfectly sealed
record of a false claim seals just as well. A trust bundle carries both
layers, and `tessera verify` reports them separately:

| layer | question it answers | how |
|---|---|---|
| integrity | is the file the file? | recompute every leaf hash + the root (names the exact record on mismatch) |
| semantic | is the record **true**? | re-execute the verification: re-run the deterministic verifier and the router over the packaged evidence |

## Quickstart

```console
$ uv run tessera bundle "Compare Müller Logistik and Nordwind Logistik totals." \
    --domain business -o answer.tsb
outcome: grounded — 3/3 claim(s) verified
root:    sha256:bd34…1383
wrote:   answer.tsb (404,168 bytes)

$ uv run tessera verify answer.tsb
bundle:    answer.tsb — tessera-trust-bundle v1
engine:    domain business, sealed under tessera 0.0.0 (installed: 0.0.0)
integrity: intact — every leaf and the root re-computed
semantic:  RE-DERIVED — 3/3 recorded claim verdict(s) re-executed and matched
  [ok] claim 0: supported — 'Nordwind Logistik GmbH': total net order value across 3 order(s): EUR 84,500.00.
  [ok] claim 1: supported — 'Mueller Logistik Gmbh': total net order value across 5 order(s): EUR 77,500.00.
  [ok] claim 2: supported — 'Nordwind Logistik GmbH' (EUR 84,500.00 across 3 order(s)) exceeds …
answer:    re-derives — the packaged corpus yields exactly this answer for this question
verdict:   PASS (exit 0)
```

No network, no engine cache, no credentials: `verify` reads the file,
rebuilds the claims and the graph from it, re-sums the cited rows with
the same `is_supported` the CI-gated eval runs, and re-routes the
question over the packaged corpus. It works identically on a machine in
airplane mode.

## The flip-a-byte walkthrough

Tamper one digit of one packaged sales row **that a claim cites**, then
*re-seal* — recompute the manifest and root, which is exactly what a
content-blind attacker can always do to an unsigned artifact:

```console
$ uv run python - <<'EOF'
import json
from tessera.bundle.format import seal

bundle = json.load(open("answer.tsb"))
cited = bundle["result"]["claims"][0]["support"][0]["id"]
for node in bundle["evidence_closure"]["graph"]["nodes"]:
    if node["record"]["id"] == cited:
        old = dict(node["attributes"])["net_amount"]
        new = str(int(float(old)) + 30000) + ".00"
        node["attributes"] = [[k, new if k == "net_amount" else v]
                              for k, v in node["attributes"]]
        node["record"]["text"] = node["record"]["text"].replace(old, new)
del bundle["integrity"]
with open("tampered.tsb", "w") as out:
    json.dump(seal(bundle), out, sort_keys=True, ensure_ascii=False,
              separators=(",", ":"))
EOF
```

Integrity-only verification — the whole of what signature/hash-chain
receipt systems check, packaged here as an honest foil — is satisfied:

```console
$ uv run python scripts/foil_integrity_only.py tampered.tsb
INTACT — every hash checks out. (Nothing here checked the content.)
```

Re-execution is not:

```console
$ uv run tessera verify tampered.tsb
…
integrity: intact — every leaf and the root re-computed
semantic:  RE-DERIVED — 1/3 recorded claim verdict(s) re-executed and matched
  [!!] claim 0: UNSUPPORTED — 'Nordwind Logistik GmbH': total net order value across 3 order(s): EUR 84,500.00.
  [ok] claim 1: supported — 'Mueller Logistik Gmbh': total net order value across 5 order(s): EUR 77,500.00.
  [!!] claim 2: UNSUPPORTED — 'Nordwind Logistik GmbH' (EUR 84,500.00 across 3 order(s)) exceeds …
answer:    DOES NOT RE-DERIVE — the recorded claims are not the answer this packaged corpus yields …
verdict:   FAIL (exit 2)
```

One changed digit; the exact dependent claims fail — the aggregate whose
cited rows no longer sum, **and** the comparison conclusion that rested
on it — while the untouched claim still re-derives. Per-claim
localization like this is the tell that verdicts are recomputed, not
pattern-matched; it is a property of the **business** grammar, whose
shapes recompute over the packaged graph (see the domain note under
honest limits). (Tamper without re-sealing and the integrity layer names
the exact record instead: `leaf 'node:I_SalesDocument:…' does not match
its content`, exit 4.)

## What verify actually re-executes

Two semantic checks, both against the file's own content (spec 0134):

1. **Claim-vs-evidence re-verification.** Every recorded claim is rebuilt
   and re-checked with the eval's own deterministic `is_supported` under
   the bundle's pinned claim grammars: aggregates re-summed over exactly
   the cited rows, superlatives re-ranked over the whole packaged graph,
   containment re-checked. The re-derived verdict is compared with the
   recorded one.
2. **Answer re-derivation.** The domain's deterministic router re-runs
   the recorded question over the packaged graph + knowledge base and
   must re-yield the recorded answer — mode, route, claim texts,
   verdicts, refusal reason, and every serialized provenance field
   (the comparison is over canonical bytes, so a fabricated display
   pointer or `all_verified` summary fails too). This binds
   question → answer → claims to the corpus: without it, a re-sealed
   bundle whose claims were swapped for *different, individually true*
   claims from the same corpus would pass check 1. It is also what makes
   a **refusal bundle** re-derivable: the packaged corpus itself
   re-yields the refusal and its reason.

**Which evidence is load-bearing depends on the domain.** For the
business grammar, the claim shapes recompute over the packaged **graph**
(aggregates re-summed, superlatives re-ranked), so the graph is the
re-executed evidence and per-claim failure is localized. For the
lexical-route domains (devex, github_actions) the answer re-derives from
the **knowledge base** and each claim's cited evidence text; there the
graph snapshot is auxiliary, check 1 is a containment check against the
cited records, and a tampered cited record surfaces as a whole-answer
divergence (check 2) rather than a single localized claim. In every
case a bundle whose cited evidence is absent from the packaged closure
fails referential validation before re-execution — a named semantic
failure, never a crash and never a pass.

## Verdict taxonomy and exit codes

Degradation is always visible, never a false PASS:

| taxonomy | meaning |
|---|---|
| `RE-DERIVED` | re-execution ran; per-claim verdicts + recorded/derived match reported |
| `INTEGRITY-ONLY` | the evidence closure is not fully packaged: hashes checked, content **not** re-derivable — stated, not glossed |
| `NOT-EVALUABLE` | the installed engine cannot honestly judge: unknown domain, engine-version or claim-grammar mismatch (both sides named) |

| exit | meaning |
|---|---|
| `0` | integrity intact; every verdict re-derived, matching, verified; the answer re-derives |
| `2` | semantic failure: a verdict that does not re-derive, an answer divergence, a structural violation |
| `3` | degraded, nothing failed: `NOT-EVALUABLE` / `INTEGRITY-ONLY`, or an honestly-recorded unverified claim |
| `4` | envelope unreadable or broken: malformed file, wrong format major, any hash mismatch |

Precedence: 4 > 2 > 3 > 0. `--json` emits the full machine-readable
report.

## The file, briefly

Canonical JSON (`tessera-canonical-json-1` — deliberately *not* RFC 8785;
ADR 0031 records why), sections `format` / `engine` / `result` /
`evidence_closure` / `integrity`, plus `action`, `signature`, and
`anchor` reserved for Milestones 21–22. The integrity manifest carries
one leaf **per packaged record**, so tampering is named, not just
detected; the root is sha256 over the sorted manifest. The evidence
closure is the **full corpus snapshot** — whole-graph claim shapes
(superlatives, comparisons) cannot be re-derived from cited records
alone, and packaging everything closes the omit-a-row attack by
construction rather than by policy. Measured sizes on the committed
corpora: business 404,168 bytes, devex 150,534, github_actions 35,273.

## Honest limits

- **Unsigned bundles prove integrity and re-derivability, not origin.**
  Anyone can produce a valid bundle over their own corpus; signatures
  (Milestone 21) bind a bundle to a keyholder. What no attacker can do,
  signed or not, is make a *false* claim re-derive from evidence that
  contradicts it.
- **Verdicts are functions of the engine version.** Bundles pin the
  tessera version and the claim-grammar identifiers; `verify` under a
  different version reports `NOT-EVALUABLE` naming both sides rather
  than re-deriving under a different grammar and calling it the same
  verdict (ADR 0031).
- **The grammars are the boundary.** Claims inside the engine's checkable
  grammars are recomputed (sums, rankings, counts, conflicts); anything
  else falls to normalized containment against the cited records. This
  is not a "verify any LLM output" tool — that constraint is what makes
  third-party re-execution possible at all.
- **Two questions with the same answer are interchangeable.** If the
  router yields the identical answer for two questions, a question swap
  between them is undetectable — and the record remains *true*: the
  packaged corpus genuinely gives that answer to the recorded question.
  Nothing false can be attested this way.
- **Domains that share a router and grammars are verification-equivalent.**
  The `domain` label selects which router and claim grammars re-derive the
  answer; two domains with the same router and the same grammars will both
  re-derive the same answer over the same corpus, so relabelling between
  them is a cosmetic mislabel, not a false attestation — the packaged
  evidence (its source paths) is the ground truth and is inspectable. A
  domain whose grammars differ (e.g. business, with six shapes) is not
  interchangeable and degrades to `NOT-EVALUABLE`.
- **A degraded bundle is a visible downgrade, not a bypass.** Editing the
  pins or the closure kind and re-sealing yields exit 3, never a PASS.
- **The graph is auxiliary for lexical-route domains.** As noted above,
  a devex or github_actions answer re-derives from the knowledge base and
  the cited evidence text, not the graph; the packaged graph for those
  domains is context, not the load-bearing evidence. The docs above say
  which is which rather than implying the graph is always what gets
  re-executed.
- **Check 2's guarantee for non-grammar claims rests on the router
  echoing cited evidence into the answer.** On all three committed
  corpora every cited-record tamper surfaces into the re-derived answer
  (so it is caught); a future domain whose router *summarized* rather
  than quoted its evidence would need its own claim grammar to keep that
  guarantee — a claim outside a checkable grammar cannot ship a stronger
  promise than containment.
- The cryptographic envelope here (hashing, manifests, roots) is
  standard machinery, not the contribution; the re-execution of
  claim-vs-evidence verification from the packaged closure is the part
  we have not seen elsewhere (the prior-art record lives with the
  Milestone 22 write-up).
