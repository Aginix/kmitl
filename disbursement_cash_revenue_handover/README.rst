=====================================
Disbursement — Cash & Revenue Handover
=====================================

Government-budget money arrives in a central bank account and is recognised as
revenue under central's accounting dimensions. When a unit other than central
spends it, the cash and the revenue have to be re-recognised under that unit's
dimensions, or the unit's financial statements read as expense with nothing
funding it.

This module raises that entry (**โอนเงินและรายได้**) automatically. When the
vendor bill for a qualifying disbursement request is created, a four-line journal
entry is drafted:

===  ==============  ================================  ==================
 #   Account         Dr / Cr                           Dimensions
===  ==============  ================================  ==================
 1   Cash/bank       Cr  gross request total           central's
 2   Revenue         Dr  gross request total           central's
 3   Revenue         Cr  gross request total           the unit's
 4   Cash/bank       Dr  gross request total           the unit's
===  ==============  ================================  ==================

The same GL accounts appear on both sides — the money does not move, only its
dimensions change.

Configuration
=============

Accounting ‣ Configuration ‣ **Central Funding Profiles**
(`kmitl.central.funding`). One row per source of funds and fiscal year:

* the cash/bank account the money sits in and the revenue account that recognised
  it;
* central's department and fund;
* the **Central Activity Level** — the level of the activity hierarchy central
  holds the money at, read off the activity code's length (default *Secondary
  Activity*, 11 digits). Central's side of a handover uses the deepest
  ancestor-or-self of the disbursement's own activity within that level.

A source of funds with no profile is never handed over, so widening or narrowing
scope is configuration, not code.

Behaviour
=========

A handover is drafted when **all** of the following hold:

* a profile matches the request's source of funds, fiscal year and company;
* the request's department is neither central nor a department beneath it;
* the request has no live handover already;
* the gross total is positive.

The entry is left in ``draft``. Accounting reviews it and takes it through the
usual Submit → Approve, and owns cancelling or reversing it — nothing here follows
the request's lifecycle afterwards. A non-blocking warning fires when a vendor bill
is submitted while its request's handover is still unposted.

The budget ledger is untouched: budget is obligated and consumed at the request's
final approval, long before the bill exists.

See ``CONTEXT.md`` for the vocabulary and the accepted limitations, and
``docs/adr/0001-dr-triggered-decoupled-handover.md`` for why the entry is raised
here and then let go.
