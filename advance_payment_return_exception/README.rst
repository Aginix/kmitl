=========================================
Advance Payment - Sent Back Exception
=========================================

A สัญญายืมเงิน sent back to its borrower by the supervisor, the director
(Office route) or the loan officer shows the non-blocking exception
**ส่งกลับแก้ไข** — in the form banner and as a red row in the list — until its
next state change, normally the resubmit. The reason stays in the chatter.
The borrower's own pull-back and the un-cancel set no flag.

Deployment
==========

``-u`` does not install a new auto-install module: run
``-i advance_payment_return_exception`` on existing databases.
