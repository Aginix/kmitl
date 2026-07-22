==================================
Mail Activity Todo (Unified Action Inbox)
==================================

หน้ารวม "สิ่งที่ต้องทำ" — one place where a user finds every piece of pending
work from every module, instead of opening each app to check. Each Todo is a
native ``mail.activity`` on its source record; this module adds the shared
language, the consolidated inbox page, a systray counter, a per-user read
state, and a completed-Todo history.

This is the **reusable core** and depends only on ``mail``. Group routing and
the KMITL-specific integrations are separate modules layered on top (see
*Module layout* and ``docs/adr/0005``).

See ``CONTEXT.md`` (glossary) and ``docs/adr/`` for the design rationale.

Module layout
=============

``mail_activity_todo`` (this module — core, depends ``mail``)
    The engine: ``todo_category`` on activity types, the ``is_my_todo`` /
    ``is_read_by_me`` searchable computes (``is_my_todo`` matches **personal**
    Todos and is an extension point), the ``todo.read`` per-user read state, the
    ``todo.log`` completed history, the Inbox + Completed views, the systray, and
    the retention cron. Knows nothing about roles, operating units, or any
    business module.

``mail_activity_todo_role_unit`` (layer, depends ``base_user_role`` + ``operating_unit``)
    Adds **group routing**: ``responsible_role_id`` + ``operating_unit_id`` tags
    on the activity, relaxes ``user_id``, extends ``_my_todo_domain`` to OR-in
    "a role I hold in one of my units", adds Claim/Release, and snapshots the
    routing into ``todo.log``. ADR-0002.

``procurement_plan_todo`` (bridge, depends the layer)
    UC1: routes a "complete the operating plan" Todo to the plan officers of the
    plan's operating unit.

``purchase_request_todo`` (bridge, depends **core only**)
    UC2/UC3: tags the PR approval/creation activities as Execution, and sends
    the requester an Acknowledgement on approve/reject. Personal (``user_id``) —
    proof the core stands alone without the role-in-unit layer.

Concepts
========

A **Todo** is a ``mail.activity``. The inbox shows **every open activity
assigned to you** — built-in, OCA, hand-scheduled, or workflow-emitted; the
category is not a gate (ADR-0006). ``todo_category`` (set on the activity type)
only refines how a Todo clears, in **two** behavioural values:

* **Execution** — cleared by acting on the source record (``activity_feedback``
  on a state transition). No "Mark as Read".
* **Acknowledgement** — dismissed per-user with **Mark as Read** (recorded in
  ``todo.read``); never removed for other recipients. **Uncategorised**
  activities (a plain Call, etc.) behave the same way — Mark as Read is the one
  user-driven clear gesture; there is no "Mark Done" button.

Assignment has two modes (ADR-0002, provided by the role-in-unit layer):

* **Personal** — ``user_id`` set; the determinable single next actor. Handled
  by the core alone.
* **Group (role-in-unit)** — ``responsible_role_id`` (a ``base_user_role``
  role) + ``operating_unit_id``; recipients = holders of that role who belong
  to that unit, **resolved live** (never a stored member list).

KMITL use cases (bridges)
=========================

* **UC1 Execution** — when a ``procurement.plan`` reaches ``new``, the
  เจ้าหน้าที่แผน of the plan's operating unit get a "กรอกแผนการดำเนินงาน" Todo;
  it clears when the plan reaches ``ready`` (or leaves ``new``).
  (``procurement_plan_todo``)
* **UC2 Execution** — the existing purchase-request "create PA/PO" activities
  are tagged ``execution`` so they show in the inbox. (``purchase_request_todo``)
* **UC3 Acknowledgement** — when a พ.1 (``purchase.request.approval``) is
  approved or rejected (manual *or* Sarabun-auto path), the requester gets an
  Acknowledgement Todo. (``purchase_request_todo``)

The core app has two menus: **Inbox** (open Todos) and **Completed** (history).
A done activity is unlinked by core, so completed Todos are snapshotted into
``todo.log`` for the Completed view (ADR-0004). From the systray, clicking a
Todo opens it inside the app; the form's *Open Source Document* button makes the
jump to the originating record.

The systray bell groups open Todos by source model (native Activities-menu
style) with per-model icons and counts. It **replaces** Odoo's native
Activities menu (removed via a small service), because that menu is
``user_id``-only and cannot surface role-in-unit group Todos — the unified bell
lists **every** activity assigned to you (personal, group, and plain built-in
ones alike) in one place, so nothing the native menu showed is lost.

Configuration
=============

#. Install ``procurement_plan_todo`` and/or ``purchase_request_todo`` for the
   KMITL flows (each pulls in the core, and the layer where needed).
#. Assign the **เจ้าหน้าที่แผน (Procurement Plan Officer)** role
   (``res.users.role``) to the staff actually responsible for plan work.
#. Make sure those users belong to the right **Operating Unit(s)**
   (``operating.unit.user_ids``) — group routing = role ∩ OU.
#. Retention window for read dismissable Todos (Acknowledgement + uncategorised)
   is the system parameter ``mail_activity_todo.dismissed_retention_days``
   (default **180**); a daily cron deletes read dismissable Todos older than that.

Known limitations (v1)
======================

* **Dynamic group routing via ``tier.validation`` is out of scope** — group
  Todos route only by ``base_user_role`` role ∩ Operating Unit.
* **``base_user_role`` reconciles a user's groups from their roles** — assign
  the role deliberately; it is not just a label.
* **Email** notifications are not sent for group Todos. The systray badge does
  update **live** via ``bus.bus`` (a ``mail_activity_todo/updated`` ping to each
  affected recipient — assignee for personal Todos, live role∩OU members for
  group ones) whenever a Todo is created, cleared, read or claimed.
* The existing ``sarabun.inbox`` / ``work.acceptance.inbox`` are left as-is;
  converging them onto activities is a later step.
