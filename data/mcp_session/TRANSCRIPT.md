# Tessera MCP session — a real client ↔ server exchange

Captured by `uv run --extra agent python scripts/record_mcp_session.py`: a
real MCP client driving the `tessera-mcp` server over stdio (spec 0084). Not
run in CI (no MCP SDK); the structured tool results are deterministic.

**Server:** `tessera` v`1.28.1`

## Tools advertised

- **`list_domains`** — List the Tessera domains you can ground a question in, each with a description of what it covers. Call this first to choose a domain for ground().
- **`ground`** — Answer a question over a Tessera domain and return grounded, cited claims — or a principled refusal. Each claim carries its full provenance inline (the cited record id, source, locator, and text) and…
- **`assertions`** — Inspect the entity-resolution provenance touching a cited record: the additive, reversible resolution/mention assertions (with their reason and confidence) that say why two records were linked as the…

## The exchange

### → `ground` {"domain": "business", "question": "What is Müller Logistik's total order value?"}
_a grounded business lookup — a sourced aggregate_

  route: entity — names one entity (Mueller Logistik Gmbh) — cross-source composition
  grounded: True  refused: False  all_verified: True
  claim 1 [verified=True]: 'Mueller Logistik Gmbh' is one resolved entity spanning 1 customer record(s) and 1 address record(s).
      ↳ I_AddrOrgNamePostalAddress:A0007  (salt_synthetic/I_AddrOrgNamePostalAddress.csv; table I_AddrOrgNamePostalAddress, row 1)
      ↳ I_Customer:0010000007  (salt_synthetic/I_Customer.csv; table I_Customer, row 1)
  claim 2 [verified=True]: Total net order value across 5 order(s): EUR 77,500.00.
      ↳ I_SalesDocument:0000500001  (salt_synthetic/I_SalesDocument.csv; table I_SalesDocument, row 1)
      ↳ I_SalesDocument:0000500002  (salt_synthetic/I_SalesDocument.csv; table I_SalesDocument, row 2)
      ↳ I_SalesDocument:0000500020  (salt_synthetic/I_SalesDocument.csv; table I_SalesDocument, row 20)
      ↳ I_SalesDocument:0000500028  (salt_synthetic/I_SalesDocument.csv; table I_SalesDocument, row 28)
      ↳ I_SalesDocument:0000500060  (salt_synthetic/I_SalesDocument.csv; table I_SalesDocument, row 60)
  claim 3 [verified=True]: # Amendment No. 2 to the Master Service Agreement  This Amendment No. 2 (the "Amendment") modifies the Master Service Agreement between Tessera Demonstrations …
      ↳ mueller_logistik_amendment:chunk1  (business_docs/mueller_logistik_amendment.md; lines 1-4, chunk 1)
  claim 4 [verified=True]: ## 1. Change of renewal date  Section 2 of the Agreement is amended as follows: the Agreement auto-renews annually on 1 February, aligning the contract year wi…
      ↳ mueller_logistik_amendment:chunk2  (business_docs/mueller_logistik_amendment.md; lines 6-10, chunk 2)
  claim 5 [verified=True]: ## 2. No other changes  All other terms of the Agreement remain in full force and effect. In the event of inconsistency between this Amendment and the Agreemen…
      ↳ mueller_logistik_amendment:chunk3  (business_docs/mueller_logistik_amendment.md; lines 12-16, chunk 3)
  claim 6 [verified=True]: Signed for Müller Logistik GmbH and Tessera Demonstrations Ltd.
      ↳ mueller_logistik_amendment:chunk4  (business_docs/mueller_logistik_amendment.md; lines 18-18, chunk 4)
  claim 7 [verified=True]: # Master Service Agreement  This Master Service Agreement ("Agreement") is entered into between Tessera Demonstrations Ltd ("Provider") and Mueller Logistik Gm…
      ↳ mueller_logistik_msa:chunk1  (business_docs/mueller_logistik_msa.md; lines 1-5, chunk 1)
  claim 8 [verified=True]: ## 1. Scope  The Provider shall supply warehouse-handling equipment and related maintenance services to the Customer across its German distribution sites.
      ↳ mueller_logistik_msa:chunk2  (business_docs/mueller_logistik_msa.md; lines 7-10, chunk 2)
  claim 9 [verified=True]: ## 2. Term and renewal  The initial term of this Agreement is twelve (12) months. Thereafter the Agreement auto-renews annually on 1 August unless either party…
      ↳ mueller_logistik_msa:chunk3  (business_docs/mueller_logistik_msa.md; lines 12-16, chunk 3)
  claim 10 [verified=True]: ## 3. Payment terms  All invoices are payable net 30 days from the invoice date. Late payment accrues interest at 4% per annum above the statutory base rate.
      ↳ mueller_logistik_msa:chunk4  (business_docs/mueller_logistik_msa.md; lines 18-21, chunk 4)
  claim 11 [verified=True]: ## 4. Special conditions  The Customer is entitled to priority next-day dispatch on spare-part orders, a condition negotiated in recognition of its time-critic…
      ↳ mueller_logistik_msa:chunk5  (business_docs/mueller_logistik_msa.md; lines 23-26, chunk 5)
  claim 12 [verified=True]: Conflict: the cited documents disagree on the renewal date — '1 February' (business_docs/mueller_logistik_amendment.md); '1 August' (business_docs/mueller_logi…
      ↳ mueller_logistik_amendment:chunk2  (business_docs/mueller_logistik_amendment.md; lines 6-10, chunk 2)
      ↳ mueller_logistik_msa:chunk3  (business_docs/mueller_logistik_msa.md; lines 12-16, chunk 3)

### → `ground` {"domain": "devex", "question": "Why did run R-1042 fail, and has this happened before?"}
_a grounded DevEx root-cause with recurrence_

  route: rca — names pipeline run R-1042 — root-cause analysis
  grounded: True  refused: False  all_verified: True
  claim 1 [verified=True]: Run R-1042 of pipeline PIPE-PAY: status failed (failing job integration-tests), commit d6d43bc9, branch main, started 2026-06-08T14:02:11Z.
      ↳ Run:R-1042  (devex_synthetic/runs.csv; table Run, row 13)
  claim 2 [verified=True]: --- job: integration-tests --- 14:09 INFO  starting payments-service integration suite 14:09 ERROR payments-service: TimeoutError: connection to payments-db ti…
      ↳ run_R-1042:chunk5  (devex_synthetic/logs/run_R-1042.log; lines 16-19, section integration-tests, chunk 5)
  claim 3 [verified=True]: Recurring failure: "TimeoutError: connection to payments-db timed out after 30s" appears in 'devex_synthetic/logs/run_R-0987.log' and 'devex_synthetic/logs/run…
      ↳ run_R-0987:chunk5  (devex_synthetic/logs/run_R-0987.log; lines 15-18, section integration-tests, chunk 5)
      ↳ run_R-1042:chunk5  (devex_synthetic/logs/run_R-1042.log; lines 16-19, section integration-tests, chunk 5)
  claim 4 [verified=True]: Documented incident: "TimeoutError: connection to payments-db timed out after 30s" appears in 'devex_synthetic/logs/run_R-1042.log' and 'devex_synthetic/ticket…
      ↳ Ticket:DEVEX-187  (devex_synthetic/tickets.csv; table Ticket, row 5)
      ↳ run_R-1042:chunk5  (devex_synthetic/logs/run_R-1042.log; lines 16-19, section integration-tests, chunk 5)
  claim 5 [verified=True]: Ticket DEVEX-187 (incident, resolved) for component SVC-PAY: "Payments CI failing: database connection timeout" — The integration suite fails with TimeoutError…
      ↳ Ticket:DEVEX-187  (devex_synthetic/tickets.csv; table Ticket, row 5)
  claim 6 [verified=True]: Resolved by: "DEVEX-187" appears in 'devex_synthetic/prs.csv' and 'devex_synthetic/tickets.csv'.
      ↳ PR:PR-198  (devex_synthetic/prs.csv; table PR, row 3)
      ↳ Ticket:DEVEX-187  (devex_synthetic/tickets.csv; table Ticket, row 5)
  claim 7 [verified=True]: PR PR-198: "Raise payments-db pool timeout" by dana.petrov, branch fix/db-pool-timeout, merged commit aee8f89f on 2026-05-14 — Fixes DEVEX-187: raises the paym…
      ↳ PR:PR-198  (devex_synthetic/prs.csv; table PR, row 3)
  claim 8 [verified=True]: diff --git a/src/payments/db_client.py b/src/payments/db_client.py @@ -18,7 +18,7 @@ class PaymentsDbClient:      def connect(self) -> Connection: -        ret…
      ↳ PR-198.diff:hunk1  (devex_synthetic/prs/PR-198.diff; file src/payments/db_client.py, hunk 1, lines 4-7)

### → `ground` {"domain": "github_actions", "question": "Why did the pages deploy fail?"}
_a grounded answer over the real GitHub Actions connector_

  route: lookup — no run, PR, or service named — lexical lookup
  grounded: True  refused: False  all_verified: True
  claim 1 [verified=True]: "pages_build_version": "f705e117ff451936b37556d1a9b7710df75de843", 	"oidc_token": "***" } ##[error]Creating Pages deployment failed ##[error]HttpError: Not Fou…
      ↳ 27284786811.failed:error1  (github_actions/logs/27284786811.failed.log; lines 47-60, job deploy, step UNKNOWN STEP, section error1)
  claim 2 [verified=True]: "pages_build_version": "778e9ba8decee3c2c9ba0a47a01a6ec7f7abed08", 	"oidc_token": "***" } ##[error]Creating Pages deployment failed ##[error]HttpError: Not Fou…
      ↳ 27285174461.failed:error1  (github_actions/logs/27285174461.failed.log; lines 47-60, job deploy, step UNKNOWN STEP, section error1)
  claim 3 [verified=True]: Run 27284786811 of workflow "Docs" (push on main): status failed (failing step "Deploy to GitHub Pages" in job "deploy"), commit f705e117ff451936b37556d1a9b771…
      ↳ Run:27284786811  (github_actions/runs/27284786811.json; table Run, row 2)
  claim 4 [verified=True]: Run 27285174461 of workflow "Docs" (push on main): status failed (failing step "Deploy to GitHub Pages" in job "deploy"), commit 778e9ba8decee3c2c9ba0a47a01a6e…
      ↳ Run:27285174461  (github_actions/runs/27285174461.json; table Run, row 3)
  claim 5 [verified=True]: ﻿2026-06-10T14:50:57.3006680Z Current runner version: '2.334.0' ##[group]Runner Image Provisioner Hosted Compute Agent Version: 20260520.533 Commit: 189110e252…
      ↳ 27284786811.failed:chunk1  (github_actions/logs/27284786811.failed.log; lines 1-46, job deploy, step UNKNOWN STEP, section chunk1)

### → `ground` {"domain": "business", "question": "What is the capital of France?"}
_a principled refusal — carried across the protocol, never an answer_

  route: lookup — no entity named — lexical lookup
  grounded: False  refused: True  all_verified: True
  refusal: I don't have enough evidence to answer that.

### → `assertions` {"domain": "business", "record_id": "I_AddrOrgNamePostalAddress:A0007"}
_the entity-resolution trail behind a cited record_

  record: I_AddrOrgNamePostalAddress:A0007
  • resolution I_Customer:0010000007 ↔ I_AddrOrgNamePostalAddress:A0007 (confidence 1.0): name match: 'muellerlogistikgmbh' ~ 'muellerlogistikgmbh' (similarity 1.000; shared distinctive token 'mueller'; vat_re…
  • mention mueller_logistik_amendment:chunk1 ↔ I_AddrOrgNamePostalAddress:A0007 (confidence 1.0): document text contains 'muellerlogistikgmbh'
  • mention mueller_logistik_amendment:chunk4 ↔ I_AddrOrgNamePostalAddress:A0007 (confidence 1.0): document text contains 'muellerlogistikgmbh'
  • mention mueller_logistik_msa:chunk1 ↔ I_AddrOrgNamePostalAddress:A0007 (confidence 1.0): document text contains 'muellerlogistikgmbh'
