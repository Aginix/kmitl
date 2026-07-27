==================
KMITL Finance Demo
==================

Demo data for the post-budget finance flow at KMITL. It continues the spend
lifecycle past budget control and exercises the accounting and treasury side of
the system so the related reports populate with realistic data.

This module owns four demo stories, all built in its ``post_init_hook``:

#. **Disbursement flow** (``PR -> PA -> PO -> Work Acceptance -> Disbursement
   Request``) for fiscal year 2568. This flow previously lived inside
   ``kmitl_demo`` and was moved here so the whole post-budget finance story is in
   one cohesive module. ``kmitl_demo`` keeps only master data and the purchase
   end-to-end flow.
#. **Bills, payments and bank export** — vendor bills (ตั้งหนี้) created and
   posted from the disbursement requests, payments (ล้างหนี้/จ่าย) registered,
   submitted, exported through a KTB bank payment file, and posted. One case
   carries withholding tax (WHT).
#. **Fixed assets and depreciation** — assets created against the KMITL asset
   profiles, validated, and depreciated for a few periods.
#. **Standalone vendor payments** — 50 outbound (supplier) payments created
   directly (not from a bill), cycling through the demo vendors, dimensions,
   amounts and dates. Half are left in ``draft`` and half ``submitted`` to fill
   the payment list and treasury reports with data.

Records are left across a realistic mix of workflow states so every stage of
each flow is visible in the UI.

Install this module only on demo or development databases.
