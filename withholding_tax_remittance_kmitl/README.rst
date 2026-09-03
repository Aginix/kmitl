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

* Every remittance declares a **งวด** (tax month) up front — ``period_month``
  / ``period_year`` — that the accountant sets, not one derived from the
  certificates. Only one remittance per ภ.ง.ด. form per month may be
  ``draft`` or ``posted`` at a time; a cancelled one doesn't block redoing
  that month.
* From the WHT Certificate list, select several ``done``, unremitted
  certificates and click **สร้างใบนำส่ง** to open a draft
  ``withholding.tax.remittance`` pre-loaded with them, its งวด filled in from
  their dates. All selected certificates must share one ภ.ง.ด. form, one
  withholding tax account, and one calendar month.
* The remittance document can also be created empty (set the งวด first) and
  filled via **โหลดรายการยังไม่นำส่ง**, which pulls every unremitted, done
  certificate for the chosen form that falls inside that month.
* **ยืนยัน / ล้างหนี้** posts a single journal entry per remittance, but with
  one ``Dr``/``Cr`` line pair — WHT payable account / bank account — per
  certificate, each pair carrying that certificate's own analytic
  distribution (read back from its source entry) so both sides of the entry
  stay attributable to the same department/fund/activity/etc. It marks every
  certificate on the document "นำส่งแล้ว" via its ``remittance_id`` link. A
  certificate whose source entry carries no analytic dimensions, or whose
  date falls outside the declared งวด, blocks posting.
* **ยกเลิก** reverses the journal entry (if posted), returns every
  certificate to "ยังไม่นำส่ง", and posts a chatter note recording which
  certificates and how much the remittance held before it let go of them.
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
   certificates for one ภ.ง.ด. form and one month, and clicks **สร้างใบนำส่ง**.
2. On the draft remittance, check the งวด (pre-filled from the certificates),
   set the bank account the cheque is drawn on, the remittance date, and
   optionally the cheque number and RD reference.
3. Click **ยืนยัน / ล้างหนี้**. The journal entry posts and every certificate on
   the document leaves the "ยังไม่นำส่ง" list.
4. To undo, open the remittance and click **ยกเลิก** — the entry is reversed
   and the certificates return to "ยังไม่นำส่ง".
