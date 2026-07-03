# `data/execution/` — the recorded real execution one-shot

This directory holds the **one real, maintainer-approved GitHub execution** Tessera
performs (Milestone 15, specs 0103/0111) — the "ran on X" record for the execution
boundary, the analogue of the Milestone 6/7 "ran on SAP HANA" online run.

It is written by `scripts/record_real_execution.py` (a maintainer-run, credentialed
one-shot, **never run in CI**), which executes one grounded action through the opt-in
real `GithubActuator` and — only for a **consummated** outcome (`created`, or `exists`
as the crash-recovery case; any other approved ending is printed, never persisted) —
writes, exactly once (`recording.guard_no_clobber` refuses any approved re-run before
network once a receipt exists; nothing here is ever overwritten — spec 0109):

- `receipt.json` — the **scrubbed** `ExecutionReceipt` (`recording.redact_receipt`): the
  credential is absent by construction, and GitHub's echoed response is reduced to
  `number` / `html_url` / `state` / `title`.
- `MANIFEST.json` — provenance (`"synthetic": false`, the target repo, the grounded
  question, the recorded date).

**The record exists** (2026-07-03): the one-shot created
[`tessera-exec-oneshot#1`](https://github.com/robert-vetter/tessera-exec-oneshot/issues/1)
— a grounded incident over the real CI failure of run 27014662820, `outcome="created"`,
status 201, idempotency key `sha256:08dc3d0c…`. Everywhere else — CI, clone-and-run, the
MCP surface — the default actuator remains the simulated one and **nothing is sent**.
