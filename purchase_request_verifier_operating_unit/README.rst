=============================================
Purchase Request Verifier - Operating Unit
=============================================

Narrows ผู้ยืนยันตรวจสอบ พ.1 candidates (``purchase_request_verifier``) to
verifiers who belong to the request's ``operating_unit_id``:

* the dropdown only offers them;
* the server rejects anyone else;
* changing the OU clears an assignee who is not in the new OU;
* the field auto-fills when the OU has exactly one verifier.

Installs automatically with ``purchase_request_verifier``.
