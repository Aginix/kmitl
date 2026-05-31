# -*- coding: utf-8 -*-
from odoo import _, api
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import str2bool

# The "To Do" activity scheduled on a document when an officer is assigned.
ASSIGN_ACTIVITY_XMLID = "mail.mail_activity_data_todo"

# ir.config_parameter that relaxes the self-claim guard (see Purchase settings).
TAKEOVER_PARAM = "procurement_assignment_kmitl.allow_takeover_assigned"


class AssignedOfficerMixin:
    """Shared behaviour for documents carrying an Assigned Officer
    (เจ้าหน้าที่ผู้รับผิดชอบ), stored in ``assigned_to``.

    This is a *plain Python* mixin used only to share method code between
    ``purchase.request`` and ``purchase.order``. It is intentionally **not** an
    Odoo ``AbstractModel``: when a non-purchase document needs the same
    behaviour, lift this into an ``assignment.mixin`` parameterised by the two
    group hooks below. See docs/adr/0001-assigned-officer-model.md.

    Each consuming model must declare:
      * the ``assigned_to`` field (Many2one res.users),
      * the ``assignment_can_assign_me`` computed Boolean, and
      * the two group hooks ``_assign_user_group`` / ``_assign_manager_group``.
    """

    # Empty slots: a plain mixin without ``__slots__`` would add a ``__dict__``
    # to the instance layout of the consuming Odoo model, breaking the
    # ``cls.__bases__`` reassignment Odoo performs in ``_prepare_setup``
    # ("object layout differs"). Odoo models are slotted, so we must be too.
    __slots__ = ()

    # Override per consuming model.
    _assign_user_group = None  # group allowed to self-claim unassigned work
    _assign_manager_group = None  # group allowed to assign others / unassign

    # -- guards ------------------------------------------------------------
    def _assignment_takeover_allowed(self):
        return str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(TAKEOVER_PARAM, default=False)
        )

    def _assignment_is_manager(self):
        return self.env.user.has_group(self._assign_manager_group)

    def _assignment_can_claim(self):
        """Whether the current user may self-assign this single record."""
        self.ensure_one()
        if not self.assigned_to:
            return True
        if self.assigned_to == self.env.user:
            return False
        return self._assignment_is_manager() or self._assignment_takeover_allowed()

    @api.depends("assigned_to")
    def _compute_assignment_can_assign_me(self):
        for rec in self:
            rec.assignment_can_assign_me = rec._assignment_can_claim()

    # -- activity bookkeeping ---------------------------------------------
    def _assignment_activity_summary(self):
        return _("Assigned as responsible procurement officer")

    def _assignment_notify(self, user):
        self.ensure_one()
        self.activity_schedule(
            ASSIGN_ACTIVITY_XMLID,
            user_id=user.id,
            summary=self._assignment_activity_summary(),
        )

    def _assignment_clear_activity(self, user):
        """Drop the open assignment to-do previously raised for ``user``."""
        self.ensure_one()
        activity_type = self.env.ref(ASSIGN_ACTIVITY_XMLID)
        summary = self._assignment_activity_summary()
        stale = self.activity_ids.filtered(
            lambda a: a.user_id == user
            and a.activity_type_id == activity_type
            and a.summary == summary
        )
        stale.unlink()

    # -- button actions ----------------------------------------------------
    def action_assignment_assign_me(self):
        me = self.env.user
        for rec in self:
            if rec.assigned_to == me:
                continue
            if not rec._assignment_can_claim():
                raise UserError(
                    _("This document is already assigned to %s.")
                    % rec.assigned_to.display_name
                )
            if rec.assigned_to:
                rec._assignment_clear_activity(rec.assigned_to)
            rec.assigned_to = me
        return True

    def action_assignment_unassign(self):
        if not self._assignment_is_manager():
            raise AccessError(_("Only a manager can unassign the officer."))
        for rec in self:
            if rec.assigned_to:
                rec._assignment_clear_activity(rec.assigned_to)
            rec.assigned_to = False
        return True

    def action_assignment_open_wizard(self):
        self.ensure_one()
        if not self._assignment_is_manager():
            raise AccessError(_("Only a manager can assign another officer."))
        return {
            "name": _("Assign Officer"),
            "type": "ir.actions.act_window",
            "res_model": "assign.officer.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
            },
        }
