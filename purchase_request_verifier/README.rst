==========================
Purchase Request Verifier
==========================

ผู้ยืนยันตรวจสอบ พ.1 (Designated Verifier, root ADR-0011).

The พ.1's ``assigned_to`` field names the one member of
``purchase_request_kmitl.group_purchase_request_verify`` who should check the
request. It must be set before ส่งคำขอ, cannot be cleared while the request
is at ``to_verify``, and stays editable until the request ends (done /
rejected / cancelled).

Todos (``mail_activity_todo`` Execution Todos):

* **Entering** ``to_verify`` (submit, ตีกลับ from the budget step, ดึงกลับ)
  schedules *ยืนยันตรวจสอบ* for the Designated Verifier. Reassigning at
  ``to_verify`` moves it to the new person.
* **Leaving** ``to_verify`` marks it done when the Designated Verifier pressed
  ตรวจสอบ, and withdraws it in every other case (another verifier pressed,
  ตีกลับ, ดึงกลับ, cancel).
* The verifier's **ตีกลับ** to ``draft`` schedules *แก้ไข พ.1 ที่ถูกตีกลับ* for
  the requester and the creator (one Todo when they are the same person),
  with the reason as the note. On resubmit, the presser's Todo is done and the
  other is withdrawn. On cancel, both are withdrawn.

Anyone in the Verifier group may still press ตรวจสอบ/ตีกลับ (ADR-0010 gate
unchanged). Naming someone only decides who receives the Todo.

``purchase_request_verifier_operating_unit`` (auto-install) limits the choice
to verifiers of the request's own Operating Unit. Override
``_get_verifier_candidates()`` to narrow the candidates further. The
field domain, constraint, onchange clearing and single-candidate auto-pick all
follow it.
