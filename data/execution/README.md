# `data/execution/` — the recorded real execution one-shot

This directory holds the **one real, maintainer-approved GitHub execution** Tessera
performs (Milestone 15, spec 0106) — the "ran on X" record for the execution boundary,
the analogue of the Milestone 6/7 "ran on SAP HANA" online run.

It is written by `scripts/record_real_execution.py` (a maintainer-run, credentialed
one-shot, **never run in CI**), which executes one grounded action through the opt-in real
`GithubActuator` and writes:

- `receipt.json` — the **scrubbed** `ExecutionReceipt` (`recording.redact_receipt`): the
  credential is absent by construction, and GitHub's echoed response is reduced to
  `number` / `html_url` / `state` / `title`.
- `MANIFEST.json` — provenance (`"synthetic": false`, the target repo, the grounded
  question, the recorded date).

Until the maintainer runs the one-shot (per `docs/DEPLOYMENT.md`), only this README is
present. Everywhere else — CI, clone-and-run, the MCP surface — the default actuator is
the simulated one and **nothing is sent**.
