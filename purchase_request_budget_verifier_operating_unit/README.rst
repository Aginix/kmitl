=====================================================
Purchase Request Budget Verifier - Operating Unit
=====================================================

Narrows ผู้ยืนยันงบประมาณ พ.1 candidates (``purchase_request_budget_verifier``)
to budget committers who belong to the request's ``operating_unit_id``:

* the dropdown only offers them;
* the server rejects anyone else;
* changing the OU clears an assignee who is not in the new OU;
* the field auto-fills when the OU has exactly one committer.

Installs automatically with ``purchase_request_budget_verifier``.
