=============================
Disbursement — Cash Movement
=============================

KMITL never pays out of its main savings account directly: the bank auto-sweeps
a single cheque covering many payees down through one or more intermediate
current accounts before it reaches the account a voucher is actually drawn on
(หัวจ่าย). Accounting does not book that sweep when it happens — one cheque
covers payees with different accounting dimensions — so it books the whole
chain instead, per payee, at the moment each voucher's payable is cleared.

A disbursement voucher already correctly books ``Dr เจ้าหนี้ / Cr หัวจ่าย``
(and the withholding tax, if any). This module adds the missing legs in
between, in the **same journal entry**:

===  ================  ==================  ==================
 #   Account           Dr / Cr             Amount
===  ================  ==================  ==================
 1   A1                Dr                  net amount paid
 1   A0 (source)        Cr                  net amount paid
 ...
 n   An (หัวจ่าย)       Dr                  net amount paid
 n   A(n-1)             Cr                  net amount paid
===  ================  ==================  ==================

Every leg carries the same net amount already credited at the paying account
and the voucher's own accounting dimensions, so the chain nets to zero except
at its two ends and reads as one document.

Configuration
=============

Accounting ▸ Configuration ▸ **Cash Routes** (also under Finance ▸ Settings;
only accounting may edit). One row per paying account and the sources of funds
it serves (`kmitl.cash.route`), listing the intermediate accounts in order:

* a row naming no intermediate account means the paying account is spent
  directly out of — accepted silently;
* a paying account with no row at all for a voucher's source of funds is a
  setup gap, surfaced as a non-blocking warning when the voucher is submitted.

18 routes are seeded on install, reverse-engineered from accounting's own
ledger. Three paying accounts this module adds (see ``account_kmitl/hooks.py``)
are not yet in every เรื่องที่จ่าย's allowed list — see ``CONTEXT.md``.

Behaviour
=========

Scoped to payments raised from a disbursement request. A route is looked up
from the payment's own source of funds and its paying account (the GL account
behind ``payment_method_line_id``); if one is found and names at least one
intermediate account, the legs are added when the voucher's entry is built,
kept in step through any later rebuild (e.g. finance correcting the payee's
bank), and re-checked once more just before the voucher posts.

See ``CONTEXT.md`` for the vocabulary and the accepted limitations, and
``docs/adr/`` for why the legs live in the voucher's own entry and why a route
is keyed by GL account rather than by หัวจ่าย.
