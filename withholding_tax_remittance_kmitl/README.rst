=================================
Withholding Tax Remittance KMITL
=================================

Batch clearing of the withholding tax payable (ล้างหนี้ภาษีหัก ณ ที่จ่าย) that
``l10n_th_account_tax`` books every time KMITL withholds tax from a vendor
payment, but never clears on its own.

Overview
========

When KMITL pays a vendor and withholds tax, the amount withheld is booked as a
credit to a WHT payable account ("ภาษีหัก ณ ที่จ่ายรอนำส่ง") — ``2120000010`` for
PND1 or ``2120000099`` for PND53 — and that credit accumulates forever. The
monthly PND filing wizard only reports the filing; it posts no journal entry.
This module lets an accountant select the certificates actually remitted to
the Revenue Department and, in one action, post the clearing journal entry
and durably mark those certificates "นำส่งแล้ว".

Key features
============

* From the WHT Certificate list, select several ``done``, unremitted
  certificates and click **สร้างใบนำส่ง** to open a draft
  ``withholding.tax.remittance`` pre-loaded with them. All selected
  certificates must share one ภ.ง.ด. form and one withholding tax account.
* The remittance document can also be created empty and filled via
  **โหลดรายการยังไม่นำส่ง**, which pulls every unremitted, done certificate for
  the chosen form.
* **ยืนยัน / ล้างหนี้** posts a single journal entry — ``Dr`` the WHT payable
  account / ``Cr`` the bank account the cheque is drawn on — for the sum of
  the selected certificates, and marks every certificate on the document
  "นำส่งแล้ว" via its ``remittance_id`` link.
* **ยกเลิก** reverses the journal entry (if posted) and returns every
  certificate to "ยังไม่นำส่ง".
* The WHT Certificate list gains a Remittance Status column and
  "ยังไม่นำส่ง" / "นำส่งแล้ว" filters.

Out of scope
============

* No printable remittance cover sheet — the journal entry and the existing
  PND filing wizard are enough for v1.
* No GL reconciliation of the WHT payable accounts; see
  ``docs/adr/0001-wht-remittance-plain-je-no-reconcile.md``.
* No payment-voucher, cheque-register, or bank-export integration — the
  cheque to the Revenue Department is handled manually outside this module.
* A certificate is remitted whole or not at all; partial remittance of a
  single certificate is not supported.

Usage
=====

1. An accountant (``accounting_kmitl`` User) opens **Finance ▸ Payment Out ▸
   Withholding Tax Certificates**, filters to "ยังไม่นำส่ง", ticks the
   certificates for one ภ.ง.ด. form, and clicks **สร้างใบนำส่ง**.
2. On the draft remittance, set the bank account the cheque is drawn on, the
   remittance date, and optionally the cheque number and RD reference.
3. Click **ยืนยัน / ล้างหนี้**. The journal entry posts and every certificate on
   the document leaves the "ยังไม่นำส่ง" list.
4. To undo, open the remittance and click **ยกเลิก** — the entry is reversed
   and the certificates return to "ยังไม่นำส่ง".
