============================
Identity & Access Management
============================

A standalone backend app that brings user / security administration together
in one place — **Users, Roles, Groups, Access Rights and Record Rules** — so it
can be delegated **without handing out full Settings (Administration) access**.

This module targets **internal (backend) users only**. Portal/public user
administration is out of scope.

How it works
============

The app adds a single security group, **IAM Manager**
(``iam.group_iam_manager``), which *implies* ``base.group_erp_manager``.

In Odoo core, ``base.group_erp_manager`` ("Administration: Access Rights")
already owns full CRUD on ``res.users``, ``res.groups``, ``ir.rule`` and
``ir.model.access`` (see ``base/security/ir.model.access.csv``), and — through
``base_user_role`` — on ``res.users.role`` and ``res.users.role.line``. Core
only *hides the menus* for groups/rules/access (under Settings ▸ Technical,
gated on the menu by ``base.group_no_one`` / ``base.group_system``); it never
gates the ORM rights themselves.

So this module is almost pure **reuse**: it re-homes those existing actions
under a dedicated top-level app menu. It adds **no new models** beyond a small
``res.users`` constraint, and **no new actions**.

================  ==================================================
Menu              Action reused
================  ==================================================
Users             ``base.action_res_users``
Roles             ``base_user_role.action_res_users_role_tree``
Groups            ``base.action_res_groups``
Access Rights     ``base.ir_access_act``
Record Rules      ``base.action_rule``
================  ==================================================

(Operating Units are added by the companion module ``iam_operating_unit``.)

Under **Configuration ▸ Default Access Rights**, the app opens the
``base.default_user`` template: its groups are the defaults applied to every
new internal user (the same template Settings edits via *Default Access
Rights*).

Read-only inspection surfaces (no new write capability) reuse existing OCA
modules:

================  ====================  =============================================
Surface           Where                 Reuses
================  ====================  =============================================
Effective         User form button      ``base_user_effective_permissions`` (re-gated
permissions                             from dev-mode to the IAM Manager)
Role Change       Audit ▸ Role          ``base_user_role_history`` (model + views; we
History           Change History        add the missing action + menu)
================  ====================  =============================================

The privilege boundary
======================

An IAM Manager can write ``res.users.groups_id`` with no core gate, so in
principle they could grant themselves ``base.group_system`` and become a full
admin. The **one boundary the app keeps closed** is exactly that:
``res.users._check_iam_no_system_escalation`` (an ``@api.constrains`` on
``groups_id``) forbids any non-system user from causing a user to hold
``base.group_system`` — directly, through an implied group/role, or via
``res.groups.users``. Only an existing full administrator can mint another.

Known limitations / TODO (Phase 1)
==================================

The IAM Manager is a **trusted delegated administrator**, one tier below a full
system admin — not a boundary hardened against a *hostile* insider:

* The Manager retains write on ``ir.model.access`` and ``ir.rule`` and could, in
  principle, author a permissive rule to gain capabilities indirectly. **TODO**:
  a ``write()`` override forbidding ACL/rule rows that reference
  ``group_system`` / ``group_erp_manager`` / ``group_iam_manager``.
* The group form's *Views* tab stays hidden (core gates it on
  ``base.group_system``); managing ``view_access`` still needs Settings.

Roadmap
=======

* **TODO** — re-add **Authentication Logs** (depend on ``user_log_view``; a
  global, unfiltered action over ``res.users.log`` under *Audit*). Removed for
  now; to be done later.
* **Phase 2** — an OWL dashboard (counts, recent changes, quick links).
* **Future** — surface ``activity_team`` and other technical-permission menus
  under *Configuration*; the hardening override above.
