#!/usr/bin/env python3
"""Generate the synthetic DevEx dataset under data/devex_synthetic/.

The DevEx Copilot's corpus (spec 0026): CI/CD pipeline runs with their logs,
pull requests with their diffs, ticket history, a service catalog, and an
on-call (ownership) export. Like ``data/salt_synthetic`` it is committed,
deterministic, and clone-and-run; *unlike* the SALT generator it uses **no
RNG at all** — the corpus is small enough that every record is a fixed,
reviewable literal, which makes the planted difficulty auditable line by line.

The difficulty is genuine, not planted-easy:

- **Recurrence.** Runs R-0987 and R-1042 (payments pipeline) fail with the
  same error signature, which also appears verbatim in resolved incident
  ticket DEVEX-187 — the "has this happened before?" anchor. The search
  pipeline carries a second recurring signature (R-1023 / R-1031), so
  recurrence is a class, not a one-off. R-1041 (payments) *passes* — the
  "why did it fail?" refusal target.
- **Entity-resolution variants with measured outcomes.** ``owners.csv`` names
  services in variant forms: exact/punctuation/typo variants that resolve at
  the 0.85 threshold, plus two abbreviations similarity cannot bridge —
  ``checkout-svc`` (0.846, a named near-miss, deliberately left undeclared)
  and ``notif-svc`` (0.429), which the eval *measured* as the Phase 3
  coverage miss and the catalog now closes with a **declared alias**
  (spec 0036 / ADR 0010).
- **Cross-source references.** PR descriptions cite their motivating tickets
  ("Fixes DEVEX-204"); PR-205 deliberately cites none.

Run with:  ``uv run python scripts/generate_devex_synthetic.py``
Pure stdlib — no third-party dependency.
"""

from __future__ import annotations

import csv
import json
import zlib
from pathlib import Path

SNAPSHOT_DATE = "2026-06-10"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "devex_synthetic"

# The recurring error signatures (verbatim, shared across sources on purpose).
SIG_PAYMENTS_TIMEOUT = "TimeoutError: connection to payments-db timed out after 30s"
SIG_CHECKOUT_TOTALS = "AssertionError: test_checkout_totals expected 3 items, got 2"
SIG_SEARCH_REPLICA = "ConnectionResetError: search-index replica unreachable"
SIG_AUTH_IMPORT = "ImportError: cannot import name 'verify_token' from 'auth.jwt'"


def _commit(run_or_pr: str) -> str:
    """A deterministic 8-hex 'commit sha' derived from a stable id."""
    return f"{zlib.crc32(run_or_pr.encode('utf-8')):08x}"


# --- service catalog (the canonical component master) --------------------------
# Component, Name, Team, Repo, Aliases (semicolon-separated; usually empty).
# SVC-NOTIF declares its `notif-svc` abbreviation — the remediation for the
# measured 0.917 coverage miss (spec 0036/ADR 0010): an alias someone *declared*
# in the catalog, exactly how a real organization closes this gap. SVC-CHK's
# `checkout-svc` abbreviation stays deliberately UNdeclared — the retained named
# near-miss (similarity 0.846) proving aliases only fix what someone declares.
COMPONENTS: tuple[tuple[str, str, str, str, str], ...] = (
    ("SVC-PAY", "payments-service", "Payments", "src/payments", ""),
    ("SVC-CHK", "checkout-service", "Storefront", "src/checkout", ""),
    ("SVC-AUTH", "auth-service", "Identity", "src/auth", ""),
    ("SVC-SRCH", "search-service", "Discovery", "src/search", ""),
    ("SVC-NOTIF", "notifications-service", "Comms", "src/notifications", "notif-svc"),
    ("SVC-INV", "inventory-service", "Warehouse", "src/inventory", ""),
)

# --- on-call export (a second master, from a different tool) -------------------
# Service (variant form!), OnCall, Channel. The variant forms are the corpus's
# entity-resolution challenge; measured similarities against the catalog name
# are pinned in tests (Unit 3):
#   "Payments Service"  -> 1.000  (punctuation/case fold)     resolves
#   "checkout-svc"      -> 0.846  (abbreviation, NEAR miss)   does not resolve
#   "auth-service"      -> 1.000  (exact)                     resolves
#   "search-servce"     -> 0.960  (typo)                      resolves
#   "notif-svc"         -> 0.429  (heavy abbreviation, miss)  does not resolve
#   "inventory service" -> 1.000  (punctuation fold)          resolves
OWNERS: tuple[tuple[str, str, str], ...] = (
    ("Payments Service", "Dana Petrov", "#payments-oncall"),
    ("checkout-svc", "Jonas Lindqvist", "#checkout-alerts"),
    ("auth-service", "Priya Raman", "#identity-oncall"),
    ("search-servce", "Mateo Alvarez", "#search-oncall"),
    ("notif-svc", "Aiko Tanaka", "#comms-oncall"),
    ("inventory service", "Lena Fischer", "#warehouse-oncall"),
)

# --- pipelines ------------------------------------------------------------------
# Pipeline, Name, Component (FK to COMPONENTS)
PIPELINES: tuple[tuple[str, str, str], ...] = (
    ("PIPE-PAY", "payments-service CI", "SVC-PAY"),
    ("PIPE-CHK", "checkout-service CI", "SVC-CHK"),
    ("PIPE-AUTH", "auth-service CI", "SVC-AUTH"),
    ("PIPE-SRCH", "search-service CI", "SVC-SRCH"),
    ("PIPE-NOTIF", "notifications-service CI", "SVC-NOTIF"),
    ("PIPE-INV", "inventory-service CI", "SVC-INV"),
)

# --- pipeline runs ----------------------------------------------------------------
# Run, Pipeline, Branch, Status, StartedAt, FailedJob, Signature ('' if passed).
# The signature column drives log generation only — it is NOT written to
# runs.csv (the signature lives in the log, where evidence belongs).
RUNS: tuple[tuple[str, str, str, str, str, str, str], ...] = (
    (
        "R-0987",
        "PIPE-PAY",
        "main",
        "failed",
        "2026-05-12T09:14:00Z",
        "integration-tests",
        SIG_PAYMENTS_TIMEOUT,
    ),
    ("R-1001", "PIPE-AUTH", "main", "passed", "2026-05-15T11:02:00Z", "", ""),
    ("R-1004", "PIPE-NOTIF", "main", "passed", "2026-05-18T08:25:00Z", "", ""),
    ("R-1007", "PIPE-INV", "main", "passed", "2026-05-20T19:41:00Z", "", ""),
    (
        "R-1012",
        "PIPE-AUTH",
        "main",
        "failed",
        "2026-05-23T07:58:00Z",
        "build",
        SIG_AUTH_IMPORT,
    ),
    ("R-1015", "PIPE-PAY", "main", "passed", "2026-05-26T10:33:00Z", "", ""),
    (
        "R-1018",
        "PIPE-CHK",
        "main",
        "failed",
        "2026-05-29T16:40:00Z",
        "unit-tests",
        SIG_CHECKOUT_TOTALS,
    ),
    (
        "R-1023",
        "PIPE-SRCH",
        "main",
        "failed",
        "2026-06-01T13:07:00Z",
        "integration-tests",
        SIG_SEARCH_REPLICA,
    ),
    ("R-1026", "PIPE-CHK", "main", "passed", "2026-06-02T09:55:00Z", "", ""),
    (
        "R-1031",
        "PIPE-SRCH",
        "main",
        "failed",
        "2026-06-04T15:12:00Z",
        "integration-tests",
        SIG_SEARCH_REPLICA,
    ),
    ("R-1035", "PIPE-INV", "main", "passed", "2026-06-05T12:20:00Z", "", ""),
    ("R-1041", "PIPE-PAY", "main", "passed", "2026-06-07T09:01:00Z", "", ""),
    (
        "R-1042",
        "PIPE-PAY",
        "main",
        "failed",
        "2026-06-08T14:02:11Z",
        "integration-tests",
        SIG_PAYMENTS_TIMEOUT,
    ),
    ("R-1044", "PIPE-NOTIF", "main", "passed", "2026-06-09T17:45:00Z", "", ""),
)

# --- tickets ---------------------------------------------------------------------
# Ticket, Component (FK), Type, Status, CreatedOn, ResolvedOn, Title, Description
TICKETS: tuple[tuple[str, str, str, str, str, str, str, str], ...] = (
    (
        "DEVEX-142",
        "SVC-AUTH",
        "task",
        "closed",
        "2026-04-02",
        "2026-04-20",
        "Rotate signing keys quarterly",
        "Automate quarterly rotation of the JWT signing keys with a grace window.",
    ),
    (
        "DEVEX-150",
        "SVC-CHK",
        "task",
        "closed",
        "2026-04-28",
        "2026-05-28",
        "Add multi-item discounts to checkout totals",
        "Customers buying three or more items should receive the tiered discount. "
        "Acceptance: checkout totals reflect the discount bands.",
    ),
    (
        "DEVEX-160",
        "SVC-NOTIF",
        "task",
        "open",
        "2026-05-05",
        "",
        "Template editor for notification e-mails",
        "Allow Comms to edit notification e-mail templates without a deploy.",
    ),
    (
        "DEVEX-171",
        "SVC-INV",
        "task",
        "closed",
        "2026-05-08",
        "2026-05-22",
        "Nightly stock reconciliation job",
        "Reconcile warehouse stock counts against the ledger every night.",
    ),
    (
        "DEVEX-187",
        "SVC-PAY",
        "incident",
        "resolved",
        "2026-05-12",
        "2026-05-14",
        "Payments CI failing: database connection timeout",
        f"The integration suite fails with {SIG_PAYMENTS_TIMEOUT}. "
        "Mitigated by raising the client pool timeout (PR-198).",
    ),
    (
        "DEVEX-195",
        "SVC-SRCH",
        "task",
        "open",
        "2026-05-19",
        "",
        "Synonym support in search queries",
        "Search should match configured synonyms (e.g. 'sofa' ~ 'couch').",
    ),
    (
        "DEVEX-204",
        "SVC-PAY",
        "task",
        "in progress",
        "2026-06-05",
        "",
        "Harden payments-db client against slow connections",
        "Follow-up to DEVEX-187: add retry with exponential backoff to the "
        "payments-db client so transient slowness does not fail the pipeline.",
    ),
    (
        "DEVEX-209",
        "SVC-CHK",
        "task",
        "open",
        "2026-06-06",
        "",
        "One-click reorder from order history",
        "Let a customer reorder a previous basket in one click.",
    ),
    (
        "DEVEX-215",
        "SVC-AUTH",
        "task",
        "open",
        "2026-06-07",
        "",
        "Audit log for admin logins",
        "Record every admin login with source address and outcome.",
    ),
    (
        "DEVEX-231",
        "SVC-SRCH",
        "incident",
        "open",
        "2026-06-01",
        "",
        "search-index replica unreachable during CI",
        f"Integration runs intermittently fail with {SIG_SEARCH_REPLICA}. "
        "Suspected replica eviction under memory pressure; investigating.",
    ),
)

# --- pull requests -----------------------------------------------------------------
# PR, Title, Author, Branch, MergedOn, Description. The merged commit is derived
# deterministically; PR-188's commit is shared with run R-1018 on purpose (the
# run that caught the regression the PR introduced).
PRS: tuple[tuple[str, str, str, str, str, str], ...] = (
    (
        "PR-188",
        "Add multi-item discounts to checkout totals",
        "mara.koch",
        "feat/checkout-discounts",
        "2026-05-28",
        "Fixes DEVEX-150: implements tiered discount bands in the totals "
        "calculator and extends the unit suite.",
    ),
    (
        "PR-190",
        "Notification e-mail templates: footer fix",
        "aiko.tanaka",
        "fix/notif-footer",
        "2026-05-21",
        "Refs DEVEX-160: first slice — corrects the footer variable in the "
        "notification templates.",
    ),
    (
        "PR-198",
        "Raise payments-db pool timeout",
        "dana.petrov",
        "fix/db-pool-timeout",
        "2026-05-14",
        "Fixes DEVEX-187: raises the payments-db client pool timeout from 10s "
        "to 30s so slow-but-healthy connections stop failing the suite.",
    ),
    (
        "PR-201",
        "Add retry with backoff to payments-db client",
        "dana.petrov",
        "feat/db-retry",
        "2026-06-09",
        "Fixes DEVEX-204: wraps payments-db calls in retry with exponential "
        "backoff (three attempts) and extends integration coverage.",
    ),
    (
        "PR-205",
        "Rename search index aliases for clarity",
        "mateo.alvarez",
        "chore/index-aliases",
        "2026-06-06",
        "Renames the search index aliases to the new naming scheme. "
        "No ticket — housekeeping.",
    ),
)

# PR-188 merged the commit that run R-1018 then failed on.
_PR_COMMIT_OVERRIDES = {"PR-188": _commit("R-1018")}


def _pr_commit(pr_id: str) -> str:
    return _PR_COMMIT_OVERRIDES.get(pr_id, _commit(pr_id))


# --- diffs --------------------------------------------------------------------------
DIFFS: dict[str, str] = {
    "PR-188": """\
diff --git a/src/checkout/totals.py b/src/checkout/totals.py
--- a/src/checkout/totals.py
+++ b/src/checkout/totals.py
@@ -41,9 +41,14 @@ def basket_total(items: list[Item]) -> Money:
     subtotal = sum(item.price * item.quantity for item in items)
-    return Money(subtotal)
+    band = _discount_band(len(items))
+    if band is not None:
+        subtotal -= subtotal * band.rate
+    return Money(subtotal)
+
+def _discount_band(count: int) -> Band | None:
+    return BANDS.get_band(count) if count >= 3 else None
diff --git a/tests/checkout/test_totals.py b/tests/checkout/test_totals.py
--- a/tests/checkout/test_totals.py
+++ b/tests/checkout/test_totals.py
@@ -12,6 +12,12 @@ def test_basket_total_plain():
     assert basket_total(two_items()).amount == 3998
+
+def test_basket_total_discounted():
+    items = three_items()
+    total = basket_total(items)
+    assert total.amount < undiscounted(items).amount
""",
    "PR-190": """\
diff --git a/src/notifications/footer.html b/src/notifications/footer.html
--- a/src/notifications/footer.html
+++ b/src/notifications/footer.html
@@ -3,5 +3,5 @@
 <footer>
-  <p>Sent by {{ compny_name }}</p>
+  <p>Sent by {{ company_name }}</p>
 </footer>
""",
    "PR-198": """\
diff --git a/src/payments/db_client.py b/src/payments/db_client.py
--- a/src/payments/db_client.py
+++ b/src/payments/db_client.py
@@ -18,7 +18,7 @@ class PaymentsDbClient:
     def connect(self) -> Connection:
-        return self._pool.acquire(timeout=10)
+        return self._pool.acquire(timeout=30)
""",
    "PR-201": """\
diff --git a/src/payments/db_client.py b/src/payments/db_client.py
--- a/src/payments/db_client.py
+++ b/src/payments/db_client.py
@@ -18,7 +18,13 @@ class PaymentsDbClient:
     def connect(self) -> Connection:
-        return self._pool.acquire(timeout=30)
+        last_error: Exception | None = None
+        for attempt in range(3):
+            try:
+                return self._pool.acquire(timeout=30)
+            except TimeoutError as error:
+                last_error = error
+                sleep(2**attempt)
+        raise last_error
diff --git a/src/payments/db_client.py b/src/payments/db_client.py
--- a/src/payments/db_client.py
+++ b/src/payments/db_client.py
@@ -44,4 +50,5 @@ class PaymentsDbClient:
     def close(self) -> None:
+        self._retry_metrics.flush()
         self._pool.release_all()
diff --git a/tests/payments/test_db_client.py b/tests/payments/test_db_client.py
--- a/tests/payments/test_db_client.py
+++ b/tests/payments/test_db_client.py
@@ -30,3 +30,10 @@ def test_connect_happy_path():
     assert client.connect() is not None
+
+def test_connect_retries_on_timeout():
+    pool = FlakyPool(failures=2)
+    client = PaymentsDbClient(pool)
+    assert client.connect() is not None
+    assert pool.acquire_calls == 3
""",
    "PR-205": """\
diff --git a/src/search/indexes.py b/src/search/indexes.py
--- a/src/search/indexes.py
+++ b/src/search/indexes.py
@@ -7,8 +7,8 @@
-PRIMARY_ALIAS = "idx-main"
-REPLICA_ALIAS = "idx-shadow"
+PRIMARY_ALIAS = "search-primary"
+REPLICA_ALIAS = "search-replica"
""",
}


# --- log rendering -----------------------------------------------------------------

_JOBS = ("checkout", "build", "unit-tests", "integration-tests", "publish")


def _hhmm(started: str, offset_minutes: int) -> str:
    """A deterministic in-log clock derived from the run's start time."""
    hours = int(started[11:13])
    minutes = int(started[14:16]) + offset_minutes
    return f"{(hours + minutes // 60) % 24:02d}:{minutes % 60:02d}"


def _render_log(
    run: str,
    pipeline_name: str,
    component_name: str,
    branch: str,
    status: str,
    started: str,
    failed_job: str,
    signature: str,
) -> str:
    """One pipeline log: a header, blank-line-separated job sections (the
    engine's chunk contract), and a result footer."""
    commit = _commit(run)
    lines: list[str] = [
        f"=== run {run} | pipeline {pipeline_name} | commit {commit} "
        f"| branch {branch} | started {started} ===",
        "",
    ]
    for index, job in enumerate(_JOBS):
        if job == "publish" and status == "failed":
            break  # the pipeline stops at the failed job; publish never runs
        t0 = _hhmm(started, 2 * index + 1)
        lines.append(f"--- job: {job} ---")
        if job == "checkout":
            lines.append(f"{t0} INFO  fetching sources at {commit}")
            lines.append(f"{t0} INFO  checkout complete")
        elif job == "build":
            lines.append(f"{t0} INFO  building {component_name} image")
            if run == "R-1042":
                # A deliberately variant service name; catalog-form mentions
                # link, this one is a documented non-link (spec 0026).
                lines.append(f"{t0} INFO  pulling base image payments-svc:1.42.0")
            if failed_job == "build":
                lines.append(f"{t0} ERROR {component_name}: {signature}")
                lines.append(f"{t0} ERROR job build failed")
                break
            lines.append(f"{t0} INFO  image built")
        elif job == "unit-tests":
            lines.append(f"{t0} INFO  running {component_name} unit suite")
            if failed_job == "unit-tests":
                lines.append(f"{t0} ERROR {component_name}: {signature}")
                lines.append(f"{t0} ERROR job unit-tests failed")
                break
            lines.append(f"{t0} INFO  unit suite passed")
        elif job == "integration-tests":
            lines.append(f"{t0} INFO  starting {component_name} integration suite")
            if failed_job == "integration-tests":
                lines.append(f"{t0} ERROR {component_name}: {signature}")
                lines.append(f"{t0} ERROR job integration-tests failed")
                break
            lines.append(f"{t0} INFO  integration suite passed")
        else:  # publish
            lines.append(f"{t0} INFO  publishing {component_name} image")
            lines.append(f"{t0} INFO  publish complete")
        lines.append("")
    if lines[-1] != "":
        lines.append("")
    verdict = f"FAILED (job {failed_job})" if status == "failed" else "PASSED"
    lines.append(f"=== result: {verdict} | run {run} ===")
    lines.append("")
    return "\n".join(lines)


# --- output ------------------------------------------------------------------------


def _write_csv(
    out_dir: Path, name: str, rows: list[dict[str, str]], header: list[str]
) -> None:
    with (out_dir / name).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(out_dir: Path = OUT_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "logs").mkdir(exist_ok=True)
    (out_dir / "prs").mkdir(exist_ok=True)

    _write_csv(
        out_dir,
        "components.csv",
        [
            {"Component": c, "Name": n, "Team": t, "Repo": r, "Aliases": a}
            for c, n, t, r, a in COMPONENTS
        ],
        ["Component", "Name", "Team", "Repo", "Aliases"],
    )
    _write_csv(
        out_dir,
        "owners.csv",
        [{"Service": s, "OnCall": o, "Channel": ch} for s, o, ch in OWNERS],
        ["Service", "OnCall", "Channel"],
    )
    _write_csv(
        out_dir,
        "pipelines.csv",
        [{"Pipeline": p, "Name": n, "Component": c} for p, n, c in PIPELINES],
        ["Pipeline", "Name", "Component"],
    )
    _write_csv(
        out_dir,
        "runs.csv",
        [
            {
                "Run": run,
                "Pipeline": pipe,
                "Commit": _commit(run),
                "Branch": branch,
                "Status": status,
                "StartedAt": started,
                "FailedJob": failed_job,
            }
            for run, pipe, branch, status, started, failed_job, _sig in RUNS
        ],
        ["Run", "Pipeline", "Commit", "Branch", "Status", "StartedAt", "FailedJob"],
    )
    _write_csv(
        out_dir,
        "tickets.csv",
        [
            {
                "Ticket": t,
                "Component": c,
                "Type": ty,
                "Status": st,
                "CreatedOn": cr,
                "ResolvedOn": re_,
                "Title": ti,
                "Description": d,
            }
            for t, c, ty, st, cr, re_, ti, d in TICKETS
        ],
        [
            "Ticket",
            "Component",
            "Type",
            "Status",
            "CreatedOn",
            "ResolvedOn",
            "Title",
            "Description",
        ],
    )
    _write_csv(
        out_dir,
        "prs.csv",
        [
            {
                "PR": pr,
                "Title": title,
                "Author": author,
                "Branch": branch,
                "MergedCommit": _pr_commit(pr),
                "MergedOn": merged,
                "Description": desc,
            }
            for pr, title, author, branch, merged, desc in PRS
        ],
        ["PR", "Title", "Author", "Branch", "MergedCommit", "MergedOn", "Description"],
    )

    pipeline_names = {p: (n, c) for p, n, c in PIPELINES}
    component_names = dict((c, n) for c, n, _t, _r, _a in COMPONENTS)
    log_count = 0
    for run, pipe, branch, status, started, failed_job, signature in RUNS:
        pipeline_name, component_id = pipeline_names[pipe]
        text = _render_log(
            run,
            pipeline_name,
            component_names[component_id],
            branch,
            status,
            started,
            failed_job,
            signature,
        )
        (out_dir / "logs" / f"run_{run}.log").write_text(text, encoding="utf-8")
        log_count += 1

    for pr_id, diff in DIFFS.items():
        (out_dir / "prs" / f"{pr_id}.diff").write_text(diff, encoding="utf-8")

    manifest = {
        "dataset": "devex_synthetic",
        "synthetic": True,
        "schema_reference": (
            "Generic CI/CD + tracker export shapes (runs, logs, PRs, diffs, "
            "tickets, service catalog, on-call) — no real system's data"
        ),
        "generator": "scripts/generate_devex_synthetic.py",
        "snapshot_date": SNAPSHOT_DATE,
        "row_counts": {
            "components.csv": len(COMPONENTS),
            "owners.csv": len(OWNERS),
            "pipelines.csv": len(PIPELINES),
            "runs.csv": len(RUNS),
            "tickets.csv": len(TICKETS),
            "prs.csv": len(PRS),
        },
        "log_files": log_count,
        "diff_files": len(DIFFS),
    }
    (out_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    readme = """\
# devex_synthetic

A small, fully deterministic synthetic corpus for the DevEx Copilot vertical
(spec 0026): CI/CD pipeline runs (`runs.csv` + `logs/`), pull requests
(`prs.csv` + `prs/*.diff`), ticket history (`tickets.csv`), the service
catalog (`components.csv`), and an on-call export (`owners.csv`).

Generated by `scripts/generate_devex_synthetic.py` — no RNG; every record is
a fixed, reviewable literal. The planted (and *measured*) difficulty:
recurring failure signatures across runs and an incident ticket; PR↔ticket
references; service-name variants in `owners.csv` that similarity cannot
bridge. `notif-svc` (0.429) was the eval's measured Phase 3 coverage miss
and is now closed by a **declared alias** in `components.csv` (spec 0036);
`checkout-svc` (0.846) stays undeclared and unresolved — a named near-miss,
not a hidden one.

All names, services, and incidents are fictional. No real system's data,
schema, or logs are included.
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    total = sum(int(v) for v in manifest["row_counts"].values())  # type: ignore[union-attr]
    print(
        f"Wrote {total} rows across 6 tables, {log_count} logs, "
        f"{len(DIFFS)} diffs to {out_dir}"
    )


if __name__ == "__main__":
    main()
