# advance_payment tracks debt operationally; accounting (GL) integration is deferred

Status: proposed / **parked** (2026-07 review — to be detailed later with the accounting team)

## Context & Decision

advance_payment tracks the loan debt as **operational amounts on the record** (loan amount, verified actual expenses, returned cash, remaining debt). It does **not** own the general-ledger accounting for clearing — in particular it does not post the expense-recognition entry (`Dr expense / Cr ลูกหนี้เงินยืม`) when actual expenses clear the debt. Expense-report lines therefore need no GL account/analytic for now. How the debt maps to GL accounts (ลูกหนี้เงินยืม), and when/where clearing entries post, is **deferred to the accounting team** and will be specified later.

## Why

- Lets the operational workflow (request → approve → disburse → report/return → close) be built and UAT'd now without blocking on the chart-of-accounts / ตั้งหนี้–ล้างหนี้ design.
- KMITL already has a dedicated accounting context (`accounting_kmitl`, ตั้งหนี้/ล้างหนี้); the GL treatment belongs there and should be designed with that team, not guessed here.

## Consequences

- Disbursement and cash return still go through `account.payment` (`จ่ายเงินยืม` / `รับคืนเงินยืม`), but the precise destination-account mapping is part of the deferred accounting work.
- The "amount remaining / debt" shown on the agreement is an operational figure, not a GL balance.
- When accounting is taken up later: revisit whether clearing posts a journal entry here or is reconciled from `accounting_kmitl`, and add account/analytic to expense-report lines if needed. Supersede/extend this ADR then.
