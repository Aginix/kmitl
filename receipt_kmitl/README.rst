==============
Receipt KMITL
==============

Cash receipting and suspense reclassification workflow for KMITL.

Overview
========

Brings the institute-wide receipt issuance, daily cash deposit, and income
reclassification process into Odoo. Replaces the legacy receipt system that
does not capture partner data and lets central finance reclassify suspense
balances to real income accounts after the fact.

Key features
============

* Custom ``receipt.kmitl`` document with multi-line entries
* Partner snapshot (Walk-in default + override per receipt)
* 6D analytic dimensions at the line level via
  ``analytic.distribution.mixin``
* Cash receipt posts ``Dr Cash GL / Cr Suspense sub-account`` immediately
* Per-department × per-fiscal-year sequence (``RC/{dept_code}/{FY2}/{####}``)
* Cash deposit slip (1-step auto-confirm; no JE — same GL account)
* Suspense Allocation document for central finance reclassification
  (multi-receipt batch with Smart Action from receipt list view)
* Cancel (before deposit) keeps the receipt number — no gap in sequence
* Refund document for posted receipts; picks correct debit account
  (income if reclassified, suspense otherwise)
* QWeb receipt printout with bilingual labels

Roles
=====

* ``Cashier`` — issues receipts and creates cash deposits for assigned
  departments (set via ``Users → KMITL Receipt → Departments``)
* ``Central Finance`` — creates Suspense Allocations and processes
  refund requests across all departments
* ``Central Finance Manager`` — posts allocations and refunds; manages
  receipt type master data

Configuration
=============

After install, the Central Finance Manager must:

1. Open ``Receipts → Configuration → Settings``:

   * Set the Walk-in Partner (a default ``Walk-in Customer`` is provided)
   * Set default cash and bank journals

2. Open ``Accounting → Configuration → Journals`` and enable
   ``KMITL Receipt Journal`` on each cash or bank journal that should
   accept receipts. Make sure each has a ``Default Account``.

3. Open ``Receipts → Configuration → Receipt Types`` and set
   ``Suspense Account`` (and optionally a ``Default Income Account``) for
   each type before use.

4. For each Cashier user, open ``Settings → Users``, switch to the
   ``KMITL Receipt`` tab, and select the departments the user may
   operate on.

Usage
=====

1. Cashier creates a receipt under ``Receipts → Operations → Receipts``
   and clicks **Issue Receipt**.
2. End of day: Cashier creates a ``Cash Deposit``, clicks
   **Pull Pending Cash Receipts**, then **Confirm**.
3. Central Finance opens the Receipts list, filters
   ``Pending Allocation``, selects lines, runs
   ``Action → Create Suspense Allocation``, assigns income accounts,
   saves the draft.
4. Manager opens the draft allocation and clicks **Post**. The receipts'
   state becomes ``Reclassified`` once all their lines are allocated.

Refunds are issued from the receipt form's ``Refund...`` button after the
receipt has been deposited or reclassified. Cancels are issued from the
``Cancel...`` button before deposit; cancellations preserve the original
receipt number and create a reversal JE.
