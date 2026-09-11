# Accounting Reports

Financial-statement reports for KMITL — Trial Balance, Profit and Loss, Balance Sheet, Cash Flow Statement and Aged Receivable/Payable — computed over the standard `account.move.line` ledger and filterable by the KMITL accounting dimensions.

## Language

**Trial Balance (งบทดลอง)**:
A per-account listing, over a date range, of the opening balance, the period movement and the ending balance — each shown as Debit, Credit and Balance. Opens straight from the menu as an OWL client action and prints as a QWeb PDF that shares the same compute.
_Avoid_: trial sheet, TB

**General Ledger (บัญชีแยกประเภท)**:
The detailed sibling of the Trial Balance, laid out like the KMITL web ledger. The menu opens a **wizard** (which accounts to report + the date range; empty accounts = all) whose button launches the report. The report is an **OWL screen**: per selected account, an opening line (ยอดยกมา), then one **row per journal item** of that account in date order, then a carried-forward line (ยอดยกไป). Each row's columns are **Date | Issue | Remark | Debit | Credit | Balance** (running) — where *Issue* is the journal entry number (`account.move.name`) and *Remark* is the entry narration (`account.move.narration`). Clicking a row **expands** it (the same panel style as the workflow module's Approval List): an info block with the date, maker + date, partner and the KMITL budget dimensions (fund / department / activity / source, resolved from the line's `analytic_distribution`), the narration, and a bordered table of the **full journal entry's Dr/Cr lines** (Account, Label, Debit, Credit) lazily fetched from `account.move.line`; the panel also links to the journal entry (`account.move`). Debit rows are listed before credit rows within that table. Computed by the OCA `general_ledger` engine (flat — `grouped_by="none"`, no centralization, single company, company currency); the wizard params travel to the client action in `action.params`. Shares its compute with the QWeb PDF and XLSX exports (flat, no expand).
_Avoid_: GL, journal report (a journal report lists by journal, not by account)

**Running balance / cumulative balance (ยอดสะสม)**:
On the General Ledger, each move line's Balance column is the account's opening balance plus every line up to and including that one — not the line's own signed amount. Reset per account.
_Avoid_: line balance, period balance

**Balance section (หมวด)**:
One of the Trial Balance's three column groups — **Opening** (ยอดยกมา), **During the year** (ระหว่างงวด) and **Ending** (ยอดคงเหลือ). Each section carries a Debit, a Credit and a Balance sub-column. In this report "หมวด" means a balance section — **not** an account category/type (asset/liability/…) and not an account group.
_Avoid_: category, account type, group (those name a chart-of-accounts grouping, not a column section)

**Balance (a section's sub-column)**:
The signed net of a section = Debit − Credit, negative when Credit exceeds Debit. Shown as the third sub-column under each balance section.
_Avoid_: net, total

**Accounting dimension (มิติทางบัญชี)**:
A KMITL analytic plan used to filter the report, selected by `root_plan_id.code`. The Trial Balance filters the four core dimensions — Departments (ส่วนงาน), Sources (แหล่งเงิน), Funds (กองทุน) and Activities (ด้าน/แผนงาน/กิจกรรม) — read from each move line's `analytic_distribution`. Within one dimension the picks are OR-ed (a hierarchical pick also matches its descendants); across dimensions they are AND-ed.
_Avoid_: analytic tag, segment

**Aged Receivable / Aged Payable (รายงานอายุลูกหนี้/เจ้าหนี้)**:
A partner-level listing, as of a chosen date, of each open (unreconciled) residual split into ageing buckets by how far past its due date it is — **Current** (not yet due), **1-30**, **31-60**, **61-90**, **91-120** and **120+** days. Aged Receivable covers `asset_receivable` accounts; Aged Payable covers `liability_payable`. Computed by the OCA `aged_partner_balance` engine. Opens straight from the menu as an OWL client action and shares its compute with the QWeb PDF and XLSX exports.
_Avoid_: aging, overdue report

**Accounting dimension on ageing (มิติทางบัญชีในรายงานอายุ)**:
Because the receivable/payable control line carries no `analytic_distribution`, a dimension filter on the ageing reports works at the **move** level: it keeps only the residuals whose invoice contains a line matching the selected dimensions — not the control line itself.
_Avoid_: line-level filter

**Cash Flow Statement (งบกระแสเงินสด)**:
A statement, over a date range, of how cash moved across three **activities** — **Operating** (ดำเนินงาน), **Investing** (ลงทุน) and **Financing** (จัดหาเงิน) — netting to the period's increase/decrease in cash, then reconciled to cash at the beginning and end of the period. Opens straight from the menu as an OWL client action and shares its compute with the QWeb PDF and XLSX exports.
_Avoid_: cash flow forecast (that is the unrelated `mis_builder_cash_flow` liquidity projection, not this statement)

**Balance-variation method (วิธีผลต่างยอดบัญชี / indirect)**:
How the statement is computed. Because every entry is balanced, the period change in cash equals the negative of the period movement of every non-cash account, so each activity's figure is `-(Σ debit − credit)` of the accounts assigned to it. Accounts are assigned to an activity by `account_type` (every on-balance, non-cash type belongs to exactly one activity), so the three activities always net to the change in cash. **Operating** starts from `Net profit (loss)` (the P&L account types) and adds the `Changes in operating assets and liabilities` (operating receivables/payables and other current asset/liability types).
_Avoid_: direct method (the GL has no cash-basis tagging to split receipts/payments)

**Cash flow classification (การจัดประเภทกิจกรรม)**:
The fixed `account_type` → activity map. **Cash** (measured, not an activity): `asset_cash`. **Operating**: P&L types (`income`, `income_other`, `expense`, `expense_depreciation`, `expense_direct_cost`) plus operating balance-sheet types (`asset_receivable`, `asset_current`, `asset_prepayments`, `liability_payable`, `liability_current`). **Investing**: `asset_fixed`, `asset_non_current`. **Financing**: `liability_non_current`, `liability_credit_card`, `equity`, `equity_unaffected`. **Excluded**: `off_balance`.
_Caveats_: the net change is always exact, but (1) depreciation is not added back across activities — `expense_depreciation` sits in Operating while the matching accumulated depreciation sits in Investing, so that split is approximate; and (2) when a dimension filter is applied, cash beginning/end may not reconcile to the activities if the cash lines carry no `analytic_distribution`.
_Avoid_: per-account cash-flow tagging (not used — classification is by type only)
