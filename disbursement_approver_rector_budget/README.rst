=================================================
Disbursement Approver (Rector Delegate) Budget
=================================================

Bridge between ``disbursement_approver_rector`` and ``disbursement_budget``.

Since the consume-budget act became its own act, the Rector-delegated approval only
recorded the sign-off. With this module the same press also consumes the budget of a
request that draws on it (``consumes_budget``), after a confirmation dialog:

* a request with a budget commitment consumes from it;
* a direct claim without one posts its direct consumption;
* a request that consumes no budget (deposits, guarantees) is only approved.

If the budget cannot be consumed (no commitment, not enough budget) the whole approval
is rolled back. The consume act is marked done, so a station that requires it does not
block the hand-over. Consuming is idempotent, so approving again after a return never
cuts the budget twice.

Installing
==========

The module is ``auto_install``, but ``-u`` does not install a new module: run
``-i disbursement_approver_rector_budget`` once on an existing database.
