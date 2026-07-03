# Tessera — a real Claude agent, grounded only through the MCP tools

A captured session (Milestone 17): Claude is given **only** Tessera's seven MCP tools and must answer from them alone. It cites grounded evidence, carries a refusal as a refusal, and its action ends at a *simulated* receipt — nothing is sent. Tool results are deterministic; the agent runs on `claude-sonnet-5`. Header note aside, this is a real run.

## Turn 1 — [devex] Why did run R-1042 fail, and has it happened before? Cite your evidence.

> 🔧 `list_domains({})`

> 🔧 `ground({"domain": "devex", "question": "Why did run R-1042 fail, and has it happened before?"})`
>   → grounded: `True`

**Claude:** ## Why R-1042 failed

Run **R-1042** (pipeline PIPE-PAY, commit `d6d43bc9`, branch `main`, started 2026-06-08T14:02:11Z) failed in the **integration-tests** job [Run:R-1042]. The log shows the payments-service integration suite hit:

```
14:09 ERROR payments-service: TimeoutError: connection to payments-db timed out after 30s
14:09 ERROR job integration-tests failed
```
[run_R-1042:chunk5]

## Has it happened before? Yes.

- The identical error (`TimeoutError: connection to payments-db timed out after 30s`) also occurred in **run R-0987** [run_R-0987:chunk5], confirming this is a recurring failure.
- It's a documented incident: **Ticket DEVEX-187** ("Payments CI failing: database connection timeout"), created 2026-05-12 and resolved 2026-05-14, describes this exact timeout in the integration suite [Ticket:DEVEX-187].
- That ticket was mitigated by **PR-198** ("Raise payments-db pool timeout"), merged 2026-05-14, which raised the client pool timeout from 10s to 30s [PR:PR-198]:
```
-        return self._pool.acquire(timeout=10)
+        return self._pool.acquire(timeout=30)
```
[PR-198.diff:hunk1]

**Conclusion:** R-1042 is a recurrence of the same payments-db connection timeout previously seen in R-0987 and "fixed" via DEVEX-187/PR-198. Since it resurfaced despite that mitigation (raising the timeout to 30s, which is exactly the threshold now being hit), the underlying DB latency/connectivity issue likely wasn't fully resolved — the fix may just have delayed the timeout rather than eliminating the root cause.

## Turn 2 — [devex] Why did run R-1041 fail?

> 🔧 `list_domains({})`

> 🔧 `ground({"domain": "devex", "question": "Why did run R-1041 fail?"})`
>   → grounded: `False`

**Claude:** Tessera reports that run **R-1041 did not fail — it actually passed.** There's no failure to explain, so no root-cause claims are available (no fabricated explanation is being offered).

## Turn 3 — [devex] Draft and (simulated) execute an incident issue for run R-1042.

> 🔧 `list_actions({})`

> 🔧 `draft_action({"action": "incident", "domain": "devex", "question": "Draft an incident issue for run R-1042"})`
>   → grounded: `True`

**Claude:** All fields grounded. Now preview payload and execute (simulated).

> 🔧 `preview_payload({"action": "incident", "domain": "devex", "question": "Draft an incident issue for run R-1042"})`

> 🔧 `execute_action({"action": "incident", "domain": "devex", "question": "Draft an incident issue for run R-1042"})`

**Claude:** ## Incident Draft for Run R-1042 — Simulated Execution Receipt

**Route:** RCA (root-cause analysis) — all fields verified ✅

**Would-be GitHub request:**
`POST /repos/{owner}/{repo}/issues`

**Title:** `TimeoutError: connection to payments-db timed out after 30s`

**Body (summarized):**
- **Failing run:** Run R-1042, pipeline PIPE-PAY, job `integration-tests` failed, commit `d6d43bc9`, branch `main`, started 2026-06-08T14:02:11Z *(source: runs.csv)*
- **Error log:** `TimeoutError: connection to payments-db timed out after 30s` *(source: logs/run_R-1042.log, lines 16-19)*
- **Prior occurrence:** Same timeout error also seen in run R-0987 *(source: logs/run_R-0987.log)*
- **Documented incident:** Ticket **DEVEX-187** ("Payments CI failing: database connection timeout"), created 2026-05-12, resolved 2026-05-14 *(source: tickets.csv)*
- **Resolving change:** **PR-198** "Raise payments-db pool timeout" by dana.petrov, merged commit `aee8f89f` on 2026-05-14 *(source: prs.csv)*
- **Code change:** `db_client.py` pool acquire timeout raised from 10s → 30s *(source: prs/PR-198.diff)*

**Status:**
- `all_grounded: true` — every field passed verification with cited provenance.
- Executed via **simulated actuator only** — `sent: false`, `simulated: true`. Nothing left Tessera; no issue was actually filed.
- `requires_approval: true` — a human or agent must approve and send this request outside Tessera to actually create the GitHub issue.
