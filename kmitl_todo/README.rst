==================================
KMITL Todos (Unified Action Inbox)
==================================

หน้ารวม "สิ่งที่ต้องทำ" — one place where a user finds every piece of pending
work from every module, instead of opening each app to check. Each Todo is a
native ``mail.activity`` on its source record; this module adds the shared
language, the consolidated inbox page, a systray counter, group routing, and a
per-user read state.

See ``CONTEXT.md`` (glossary) and ``docs/adr/`` for the design rationale.

Concepts
========

A **Todo** is a ``mail.activity``. Four behavioural categories
(``todo_category`` on the activity type):

* **Approval / Execution** — cleared by acting on the source record
  (``activity_feedback`` on a state transition). No "Mark as Read".
* **Acknowledgement / FYI** — dismissed per-user with **Mark as Read**
  (recorded in ``kmitl.todo.read``); never removed for other recipients.

Assignment has two modes (ADR-0002):

* **Personal** — ``user_id`` set; the determinable single next actor.
* **Group (role-in-unit)** — ``responsible_role_id`` (a ``base_user_role``
  role) + ``operating_unit_id``; recipients = holders of that role who belong
  to that unit, **resolved live** (never a stored member list).

PoC scope (procurement_plan → พ.1)
==================================

* **UC1 Execution** — when a ``procurement.plan`` reaches ``new``, the
  เจ้าหน้าที่แผน of the plan's operating unit get a "กรอกแผนการดำเนินงาน" Todo;
  it clears when the plan reaches ``ready`` (or leaves ``new``).
* **UC2 Execution** — the existing purchase-request "create PA/PO" activities
  are tagged ``execution`` so they show in the inbox.
* **UC3 FYI** — when a พ.1 (``purchase.request.approval``) is approved or
  rejected (manual *or* Sarabun-auto path), the requester gets an FYI.

Configuration
=============

#. Assign the **เจ้าหน้าที่แผน (Procurement Plan Officer)** role
   (``res.users.role``) to the staff actually responsible for plan work.
#. Make sure those users belong to the right **Operating Unit(s)**
   (``operating.unit.user_ids``) — group routing = role ∩ OU.
#. Retention window for read FYI/Acknowledgement Todos is the system parameter
   ``kmitl_todo.fyi_retention_days`` (default **180**); a daily cron deletes
   read FYI/Ack Todos older than that.

Known limitations (v1)
======================

* **Dynamic group routing via ``tier.validation`` is out of scope** — group
  Todos route only by ``base_user_role`` role ∩ Operating Unit.
* **``base_user_role`` reconciles a user's groups from their roles** — assign
  the role deliberately; it is not just a label.
* Email / bus notifications are **not** sent for group Todos (v1 relies on the
  inbox + systray).
* The existing ``sarabun.inbox`` / ``work.acceptance.inbox`` are left as-is;
  converging them onto activities is a later step.
* Module name ``kmitl_todo`` is provisional.
