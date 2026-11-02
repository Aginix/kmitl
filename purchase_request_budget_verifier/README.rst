=================================
Purchase Request Budget Verifier
=================================

ผู้ยืนยันงบประมาณ พ.1 (Designated Budget Committer, root ADR-0012).

The พ.1's new ``budget_verifier_id`` field names the one member of
``purchase_request_budget.group_purchase_request_budget_commit`` who should
reserve the request's budget. It can be filled from ``draft``, must be set
before ตรวจสอบ (``to_verify → to_verify_budget``), cannot be cleared while
the request is at ``to_verify_budget``, and stays editable until the request
ends (done / rejected / cancelled).

The reserve Todo (``purchase_request_budget_todo``'s *จองงบประมาณ* type) now
goes to that person only:

* **Entering** ``to_verify_budget`` schedules it for the ผู้ยืนยันงบประมาณ.
  Reassigning at ``to_verify_budget`` moves it to the new person.
* **Leaving** ``to_verify_budget`` marks it done when the ผู้ยืนยันงบประมาณ
  moved the request to ``to_approve``, and withdraws it in every other case
  (another committer reserved, ตีกลับ, ดึงกลับ, reset, cancel).
* Installing switches off the role จองงบประมาณ พ.1 ∩ OU broadcast
  (``automation_pr_draft_to_verify``); uninstalling switches it back on.

Anyone in the group may still Reserve or ตีกลับ (ADR-0010 gate unchanged).
Naming someone only decides who receives the Todo.

``purchase_request_budget_verifier_operating_unit`` (auto-install) limits the
choice to committers of the request's own Operating Unit. Override
``_get_budget_verifier_candidates()`` to narrow the candidates further.
