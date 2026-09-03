# Withholding Tax Remittance KMITL

Clears the withholding tax payable (รอนำส่ง) that `l10n_th_account_tax` books every
time KMITL withholds tax from a vendor payment, by batching the certificates the
office actually remitted to the Revenue Department into one journal entry.

## Language

**WHT Remittance** (การนำส่งภาษีหัก ณ ที่จ่าย, `withholding.tax.remittance`):
The batch an accountant posts when the office writes a cheque to สรรพากร — one
per ภ.ง.ด. form, one journal entry (`Dr` the WHT payable account / `Cr` the bank
the cheque is drawn on). Bundles `withholding.tax.cert` records the way
`kmitl.receipt.remittance` bundles receipts. Numbered `WHTR/<FY>/nnnn`.
_Avoid_: bare "ล้างหนี้" — ambiguous with Vendor Clearing below.

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
