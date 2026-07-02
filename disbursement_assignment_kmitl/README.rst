=============================
Disbursement Assignment KMITL
=============================

Auto-assign a responsible **verification officer** (เจ้าหน้าที่หมวดตรวจ) to a
disbursement request the moment the head of department signs it, so requests no
longer pile up in one shared queue when different officers handle different
kinds of money.

Features
========

* **Rule-based auto-assignment.** When a request reaches the ``signed`` state
  it is matched against a list of routing rules and the first matching rule's
  officer is stored in ``Assigned Officer`` (``assigned_to``). Rules combine
  any of these criteria; an empty criterion is a wildcard:

  * Department (ส่วนงาน)
  * Source (แหล่งเงิน)
  * Fund (กองทุน)
  * Activity (ด้าน/แผนงาน/กิจกรรม)
  * Partner Type (ประเภทคู่ค้า)

  Hierarchical dimensions match on the whole subtree: a rule set on a parent
  department / fund / activity covers every child. Rules are ordered by
  sequence and the first match wins, so an empty catch-all rule at the bottom
  acts as the default officer.

* **A To-Do for the officer.** Assignment schedules a "To Do" activity on the
  request so the officer is notified. Reassigning moves the To-Do; validating,
  resetting, or cancelling the request closes it.

* **Manual override.** Officers can claim an unassigned (or, by default,
  mis-routed) request with **Assign to me**; managers can reassign with
  **Assign…** or clear the officer with **Unassign**.

* **Advisory only.** Assignment never restricts who may validate a request --
  it only drives filtering (``My Verifications`` / ``Unassigned``) and the
  To-Do notification.

* **Backlog routing.** *Apply Rules to Pending Requests* (gear menu on the rule
  list) routes already-signed, still-unassigned requests after you add or edit
  rules.

Configuration
=============

* Rules live under **Disbursement ▸ Configuration ▸ Assignment Rules**
  (managers only).
* The system parameter ``disbursement_assignment_kmitl.allow_takeover_assigned``
  (default ``True``) controls whether an officer may claim a request already
  assigned to someone else. Set it to ``False`` to lock claims to the assigned
  officer and managers.

Credits
=======

Authors
-------

* Aginix Technologies

License
-------

LGPL-3
