============================
Procurement Assignment KMITL
============================

Assign a responsible procurement officer (เจ้าหน้าที่ผู้รับผิดชอบ) to Purchase
Requests (PR), Purchase Request Approvals (PA) and Purchase Orders (PO), so each
officer can find the work assigned to them.

Features
========

* A single **Assigned Officer** per document, stored in ``assigned_to``
  (reused on PR, new on PO). A PA has no officer of its own — it derives from
  its parent PR (``request_id.assigned_to``).
* Three form buttons on PR and PO:

  * **Assign to me** — any officer can claim unassigned work.
  * **Assign…** — managers pick another officer through a wizard.
  * **Unassign** — managers clear the officer (shown only when assigned).

* Assigning *another* officer raises a "To Do" activity for them; self-assign
  does not. Reassigning or unassigning clears the previous officer's open
  activity.
* A top-level **My Work (งานของฉัน)** menu listing the current user's PRs, PAs
  and POs.
* A Purchase setting, *Allow officers to take over already-assigned documents*,
  that relaxes the default "claim unassigned only" rule.

See ``docs/adr/0001-assigned-officer-model.md`` for the design rationale.
