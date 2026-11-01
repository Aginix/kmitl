=====================================
Advance Payment - Exception Rules
=====================================

Adds ``base_exception`` rule checks to สัญญายืมเงิน (``advance.payment``).
A draft that fails a rule stops at the exceptions popup when the borrower
presses ส่งคำขอ; blocking rules are re-checked on the loan officer's own
corrections in ``to_endorse`` / ``to_verify``.

Every rule lives here, including the mandatory ones: amount limits, missing
bank account (an unlisted account declared in full passes), missing source
document and missing supervisor. The module is ``auto_install`` so a database
with ``advance_payment`` always gets them (advance_payment ADR-0024).

Configuration
=============

สัญญายืมเงิน → Configuration → Exception Rules.

Deployment
==========

``-u`` does not install a new auto-install module: run
``-i advance_payment_exception`` on existing databases, **in the same
command** as ``-u advance_payment``. Upgrading ``advance_payment`` alone
first drops the ``advance.payment`` value of ``exception.rule.model``
(``ondelete`` cascade), which deletes every advance-payment rule, custom
ones included, before ``pre_init_hook`` can adopt them.
