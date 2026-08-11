==================
KMITL Finance Demo
==================

Demo data for the post-budget finance flow at KMITL. It continues the spend
lifecycle past budget control and exercises the accounting and treasury side of
the system so the related reports populate with realistic data.

This module owns three demo stories, all built in its ``post_init_hook``:

#. **Disbursement flow** (``PR -> PA -> PO -> Work Acceptance -> Disbursement
   Request``) for fiscal year 2568. This flow previously lived inside
   ``kmitl_demo`` and was moved here so the whole post-budget finance story is in
   one cohesive module. ``kmitl_demo`` keeps only master data and the purchase
   end-to-end flow.
#. **Vendor bills** — vendor bills (ตั้งหนี้) created and posted from the
   disbursement requests, leaving every request at ``bills_posted``. One case
   carries withholding tax (WHT).
#. **Fixed assets and depreciation** — assets created against the KMITL asset
   profiles, validated, and depreciated for a few periods.

The demo stops at ``bills_posted`` on purpose: no ``account.payment`` is created,
so the finance payment queue (audit -> authorize -> pay) and the bank payment
export are left to be exercised by hand in the UI.

Install this module only on demo or development databases.
