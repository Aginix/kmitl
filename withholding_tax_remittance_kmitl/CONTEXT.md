# Withholding Tax Remittance KMITL

Clears the withholding tax payable (รอนำส่ง) that `l10n_th_account_tax` books every
time KMITL withholds tax from a vendor payment, by batching the certificates the
office actually remitted to the Revenue Department into one journal entry.

## Language

**WHT Remittance** (การนำส่งภาษีหัก ณ ที่จ่าย, `withholding.tax.remittance`):
The batch an accountant posts when the office writes a cheque to สรรพากร — one
per (ภ.ง.ด. form, งวด, แหล่งเงิน), one journal entry. Bundles
`withholding.tax.cert` records the way `kmitl.receipt.remittance` bundles
receipts. Numbered `WHTR/<FY>/nnnn`.
_Avoid_: bare "ล้างหนี้" — ambiguous with Vendor Clearing below.

**แหล่งเงิน (funding source, `source_analytic_id`)**:
The `sources` dimension of the 6D framework, entered on the remittance and
required. The office files one cheque per funding source, so the document is
scoped by it: only certificates whose source dimension matches are loadable,
and a certificate spanning more than one source cannot be remitted at all
(`remittance_id` is a Many2one — a certificate belongs to one remittance,
whole). Read off the certificate's source WHT line, never off the certificate
itself, which has no analytic fields of its own.

**บัญชีออมทรัพย์ / บัญชีกระแสรายวัน** (`savings_account_id`,
`current_account_id`): the cheque is drawn on the savings account, but the bank
first moves the cheque amount into the current account and the cheque is then
cleared from there. Both movements are booked, so both accounts reconcile
against their statements: the current account is debited and credited the same
amount (net zero) and the money genuinely leaves the savings account.

**Vendor Clearing** (ล้างเจ้าหนี้ / Vendor Clearing Vouchers):
A **different, pre-existing** concept: settling a *vendor's* payable by paying
the vendor. Nothing in this module. Never conflate the two just because both
are colloquially "ล้างหนี้" — one clears a vendor's account, this one clears the
tax office's.

**WHT payable / รอนำส่ง**:
The accumulated credit on the withholding tax account (`account.withholding.tax.account_id`,
e.g. `2120000010` for PND1 or `2120000099` for PND53) owed to the Revenue
Department. Booked automatically by `l10n_th_account_tax` every time a
`withholding.tax.cert` line is created; never cleared by core or by the PND
filing wizard. This module is the only thing that clears it, and it does so
with a **plain journal entry**, deliberately not GL reconciliation — see
[ADR-0001](./docs/adr/0001-wht-remittance-plain-je-no-reconcile.md).

**Remittance Status** (`withholding.tax.cert.remit_state`):
Computed, stored: `remitted` once the cert's `remittance_id` points at a
`posted` remittance, else `pending`. This is the durable "นำส่งแล้ว" mark — it
survives the source payment being reset to draft and re-posted, because
nothing in `l10n_th_account_tax` ever touches `remittance_id`.

`remittance_id` is **current membership, not history**: it always points at
whichever remittance currently holds the certificate (or nothing). It is not
an audit trail of every remittance a certificate was ever attached to —
`action_cancel` clears it back to empty, and the chatter (not the field) is
what records what a cancelled remittance used to hold.

**งวด (Period)**: `period_month` + `period_year` are a **user-entered input**,
not derived from the certificates' dates. An accountant declares the month
they are filing for before loading certificates; the certificate dates then
have to fall inside that declared month (`date_from`–`date_to`, computed from
`period_month`/`period_year`), not the other way around. `action_post`
enforces this — a certificate outside the declared period raises. Creating a
remittance from the WHT Certificate list (`action_create_remittance`)
auto-fills the period from the selected certificates' dates as a convenience,
and raises if they span more than one month.

**One form per month per source**: at most one non-cancelled remittance
(`draft` or `posted`) may exist per
`(company, ภ.ง.ด., period_month, period_year, source_analytic_id)`.
Cancelled remittances don't count, so a botched month can be redone. This is
a Python `@api.constrains`, not a SQL unique index, precisely so cancelled
records are excluded.

**Analytic dimensions on the clearing JE**: every line of the remittance's JE
carries an `analytic_distribution`, and the lines come in groups of four per
certificate per distinct distribution — `Dr` WHT payable / `Cr` current
account (the cheque) and `Dr` current account / `Cr` savings account (the
bank's sweep that funds it) — all four with the same distribution, so every
dimension nets to zero inside the one entry. The header-level
`analytic_distribution` on `account.move` is **never** set (see
[ADR-0002](./docs/adr/0002-remittance-period-and-per-cert-analytic-lines.md)
for why). The distribution is read back from each certificate's *source*
journal entry (`cert.move_id`, the entry the WHT line was booked on), not
recomputed — `finance_kmitl` already stamps the payment's dimensions onto
that line when the cert is created. See
[ADR-0003](./docs/adr/0003-source-scoped-remittance-and-two-bank-accounts.md)
for the funding-source scoping and the two bank accounts.
