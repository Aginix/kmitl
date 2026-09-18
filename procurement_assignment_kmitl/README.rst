============================
Procurement Assignment KMITL
============================

Assign a responsible procurement officer (เจ้าหน้าที่ผู้รับผิดชอบ) to Purchase
Requests (PR), Purchase Request Approvals (PA) and Purchase Orders (PO), so each
officer can find the work assigned to them.

Features
========

* An **Assigned Officer** on every document, held independently per document:

  * PR uses ``assigned_to`` (repurposed OCA field).
  * PO uses ``assigned_to`` (new field).
  * PA uses ``pa_assigned_to`` (new field — PA's own ``assigned_to`` is the
    Approver, a different role).

  PA is *not* derived from its parent PR: a new PA starts unassigned, and
  changes on one document never touch the other. The PR's officer is still
  shown on the PA (tree + search) for coordination context.
* Three form buttons on PR, PA and PO:

  * **Assign to me** — any officer can claim unassigned work.
  * **Assign…** — managers pick another officer through a wizard.
  * **Unassign** — managers clear the officer (shown only when assigned).

* Assigning an officer — yourself or someone else, via banner button or
  wizard — always raises a "To Do" activity for that officer, so the document
  lands in their unified inbox (``mail_activity_todo``). Reassigning clears
  the previous officer's activity; unassigning clears it entirely.
* An **Assigned to me** search filter on PR and PO, and two filters on PA
  ("Assigned to me (พ.1)" and "Assigned to me (พจ.1)") so officers can list the
  documents assigned to them at each stage. (A dedicated landing/app page is
  intentionally left to a future ``mail_activity_todo`` app.)
* A Purchase setting, *Allow officers to take over already-assigned documents*,
  that relaxes the default "claim unassigned only" rule.

See ``docs/adr/0001-assigned-officer-model.md`` and
``docs/adr/0006-pa-independent-assigned-officer.md`` for the design rationale.
