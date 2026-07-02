"""Record ONE real GitHub execution — the Milestone 15 one-shot (spec 0106).

The "ran on X" honesty for the execution boundary (the M6/M7 "ran on SAP" analogue):
this constructs the opt-in real ``GithubActuator`` from environment credentials and
executes ONE grounded action against a real GitHub repository, with approval — the first
(and only) real, credentialed, irreversible side effect Tessera performs. It is NOT run
in CI and is never imported at runtime; it is a maintainer-run, credentialed one-shot.

The credential NEVER enters the agent's environment: the maintainer supplies it via a
gitignored ``.env``. Reproduce (maintainer only), per ``docs/DEPLOYMENT.md``:

    # 1. create a throwaway sandbox repo, e.g. <you>/tessera-exec-oneshot
    # 2. mint a fine-grained PAT with Issues: Read and write on that ONE repo
    # 3. put the values in .env (gitignored), then:
    set -a; source .env; set +a
    TESSERA_EXEC_APPROVE=true uv run python scripts/record_real_execution.py

Environment:
    TESSERA_EXEC_OWNER    the sandbox repo owner (required to send)
    TESSERA_EXEC_REPO     the sandbox repo name  (required to send)
    TESSERA_GITHUB_TOKEN  the fine-grained PAT   (or GITHUB_TOKEN; required to send)
    TESSERA_EXEC_APPROVE  must equal "true" to actually send (explicit approval gate)
    TESSERA_EXEC_ACTION / _DOMAIN / _QUESTION  optional overrides (default: a real
                          github_actions incident over a real failed Tessera CI run)

Without owner/repo/token it prints instructions and sends nothing. With them but WITHOUT
``TESSERA_EXEC_APPROVE=true`` the real actuator returns ``outcome="blocked"`` (nothing
sent, nothing written) — a safe rehearsal. Only an approved, **consummated** attempt
(``created`` or ``exists``) scrubs the receipt (``recording.redact_receipt``) and writes
it to ``data/execution/``; an approved attempt ending ``blocked``/``inconclusive``/
``error`` is printed for inspection and exits non-zero, persisting nothing, so a failed
attempt neither blocks a retry nor overwrites anything (audit B1). An already-recorded
receipt is never clobbered: an approved re-run refuses *before any network*
(``recording.guard_no_clobber``). Re-running before the record exists is best-effort
idempotent (ADR 0026): the pre-check finds the embedded marker and returns
``outcome="exists"``, creating no duplicate.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from tessera.agent.execution import ExecutionReceipt, GithubActuator, execute_action
from tessera.agent.recording import guard_no_clobber, redact_receipt, should_persist
from tessera.devex.knowledge import build_github_actions_graph

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "execution"

_INSTRUCTIONS = """\
Nothing sent — no credential configured. This is the maintainer-only one-shot.

  1. Create a throwaway sandbox repo (e.g. <you>/tessera-exec-oneshot).
  2. Mint a fine-grained PAT with Issues: Read and write on that ONE repo.
  3. Fill .env (gitignored) and run:
       set -a; source .env; set +a
       TESSERA_EXEC_APPROVE=true uv run python scripts/record_real_execution.py

Required: TESSERA_EXEC_OWNER, TESSERA_EXEC_REPO, TESSERA_GITHUB_TOKEN (or GITHUB_TOKEN).
Set TESSERA_EXEC_APPROVE=true to actually send; leave it unset for a safe rehearsal
(the real actuator returns outcome="blocked" and sends nothing).
"""


def _default_question() -> str:
    """The default grounded content: an incident over the first REAL Tessera CI failed
    run in the committed ``data/github_actions`` snapshot."""
    failed = sorted(
        node.record.id.removeprefix("Run:")
        for node in build_github_actions_graph().nodes
        if node.kind == "Run" and node.attr("status") == "failed"
    )
    if not failed:
        raise SystemExit("no failed github_actions run in the snapshot to ground.")
    return f"Why did run {failed[0]} fail?"


def _write(
    scrubbed: dict[str, object],
    *,
    owner: str,
    repo: str,
    action: str,
    domain: str,
    question: str,
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "receipt.json").write_text(
        json.dumps(scrubbed, indent=2, ensure_ascii=False) + "\n", "utf-8"
    )
    manifest = {
        "dataset": "execution",
        "synthetic": False,
        "recorded_by": "scripts/record_real_execution.py",
        "recorded": datetime.now(UTC).date().isoformat(),
        "target": f"github.com/{owner}/{repo}",
        "action": action,
        "domain": domain,
        "question": question,
        "note": (
            "One real, maintainer-approved GitHub execution (Milestone 15, spec 0106). "
            "The credential is never committed (the receipt carries no token by "
            "construction); GitHub's echoed response is scrubbed to number/html_url/"
            "state/title. Best-effort idempotent (ADR 0026): a re-run returns 'exists'."
        ),
    }
    (OUT_DIR / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", "utf-8"
    )


def _summarize(receipt: ExecutionReceipt) -> None:
    print(
        f"outcome: {receipt.outcome}  sent: {receipt.sent}  "
        f"actuator: {receipt.actuator}"
    )
    print(f"idempotency_key: {receipt.idempotency_key}")
    result = receipt.result
    if receipt.outcome == "created":
        response = result.get("response")
        url = response.get("html_url") if isinstance(response, dict) else None
        print(f"created: {url}  ← paste this back to record the one-shot")
    elif receipt.outcome == "exists":
        existing = result.get("existing")
        url = existing.get("html_url") if isinstance(existing, dict) else None
        print(f"already existed (idempotent no-op): {url}")
    elif receipt.outcome in ("blocked", "inconclusive", "error"):
        print(f"nothing created: {result.get('reason') or result}")


def main() -> None:
    owner = os.environ.get("TESSERA_EXEC_OWNER")
    repo = os.environ.get("TESSERA_EXEC_REPO")
    token = os.environ.get("TESSERA_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    approve = os.environ.get("TESSERA_EXEC_APPROVE") == "true"
    action = os.environ.get("TESSERA_EXEC_ACTION", "incident")
    domain = os.environ.get("TESSERA_EXEC_DOMAIN", "github_actions")
    question = os.environ.get("TESSERA_EXEC_QUESTION") or _default_question()

    if not (owner and repo and token):
        print(_INSTRUCTIONS)
        return

    # An approved run may write — so refuse a clobber BEFORE any network activity
    # (audit B1): if the one-shot is already recorded, nothing is sent or touched.
    if approve:
        guard_no_clobber(OUT_DIR)

    actuator = GithubActuator(owner=owner, repo=repo, token=token)
    receipt = execute_action(
        action, domain, question, actuator=actuator, approve=approve
    )
    _summarize(receipt)

    # Only an approved (real) attempt is recorded — a rehearsal (approve unset →
    # outcome="blocked", no network) writes nothing, so it can never be mistaken for,
    # or committed as, the one-shot.
    if not approve:
        print(
            "(rehearsal — nothing sent, nothing written; "
            "set TESSERA_EXEC_APPROVE=true to send and record.)"
        )
        return
    scrubbed = redact_receipt(receipt.to_dict())
    # Persist only a consummated outcome (created/exists). A blocked/inconclusive/
    # error attempt is printed for inspection and exits non-zero — nothing written,
    # so the failed attempt neither blocks the retry nor overwrites history (B1).
    if not should_persist(receipt.outcome):
        print(json.dumps(scrubbed, indent=2, ensure_ascii=False))
        raise SystemExit(
            f"approved attempt ended outcome={receipt.outcome!r} — nothing persisted. "
            "Inspect the receipt above, fix the cause, and re-run."
        )
    _write(
        scrubbed,
        owner=owner,
        repo=repo,
        action=action,
        domain=domain,
        question=question,
    )
    print(f"wrote {OUT_DIR / 'receipt.json'} and MANIFEST.json (scrubbed)")


if __name__ == "__main__":
    main()
