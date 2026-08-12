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
   disbursement requests, leaving every request at ``bills_posted`` with one
   payment line per payee. One case carries withholding tax (WHT).
#. **Fixed assets and depreciation** — assets created against the KMITL asset
   profiles, validated, and depreciated for a few periods.

The demo stops at ``bills_posted`` on purpose: no ``account.payment`` is created,
so the finance payment queue (audit -> authorize -> pay) and the bank payment
export are left to be exercised by hand in the UI.

Each request does arrive at that queue with its payment lines already made — one
per payee, carrying the payee's bank and the net amount to pay. What is left
blank is the payment subject (เรื่องที่จ่าย), because choosing it is the
auditor's step and it is what derives the paying account (หัวจ่าย) of every row:
pick one on a demo request and watch the accounts and their match badges fill in.

Regenerating the demo data
==========================

``post_init_hook`` only fires on a fresh install — never on ``-u`` — so a
developer who wants another batch of demo records would otherwise have to
rebuild the database. **Settings > Technical > Regenerate Demo Data** re-runs the
seeding on demand, with a checkbox per story so one slow story can be run on its
own. It reuses the very same story functions the install hooks call, so there is
only ever one seeding code path.

Three layers keep it away from real data:

#. this module is demo data, so it is only ever installed on a demo or
   development database;
#. the menu carries ``base.group_no_one``, which hides it unless developer mode
   is on;
#. the wizard's ACL is restricted to ``base.group_system``, which is what
   actually enforces privilege — every internal user already implies
   ``base.group_no_one``, so hiding the menu is not protection on its own.

**It appends, it never resets.** Each run adds a fresh batch alongside the
previous ones; tell batches apart by their creation date. This is a deliberate
limitation rather than an omission: the hooks stamp no ``ir.model.data``, so
there is no reliable handle on "the last run's records" — the posted
appropriation ``budget.move`` rows in particular carry no marker at all and are
indistinguishable from figures a demo user entered by hand. On top of that,
``sarabun.document.number.document_id`` is a database-level ``ondelete="restrict"``
foreign key, so deleting demo sarabun documents would mean destroying the
register's audit ledger, and ``ir.sequence`` numbers never roll back. A true
reset therefore means recreating the database, not clicking a button.

The ``kmitl_demo`` stories are offered too, except for its language setup: that
block installs a language pack across every module, overwrites a hardcoded
``ir.default`` row and rewrites ``lang`` on every user, so it stays install-only
and is unreachable from the wizard.

Install this module only on demo or development databases.
