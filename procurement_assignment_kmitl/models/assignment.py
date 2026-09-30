# -*- coding: utf-8 -*-
from odoo import _
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import str2bool

# The "To Do" activity scheduled on a document when an officer is assigned.
ASSIGN_ACTIVITY_XMLID = "mail.mail_activity_data_todo"

# ir.config_parameter that relaxes the self-claim guard (see Purchase settings).
TAKEOVER_PARAM = "procurement_assignment_kmitl.allow_takeover_assigned"


class AssignedOfficerMixin:
    """Shared behaviour for documents carrying an Assigned Officer
    (เจ้าหน้าที่ผู้รับผิดชอบ).

    This is a *plain Python* mixin used to share method code between
    ``purchase.request``, ``purchase.request.approval`` and
    ``purchase.order``. It is intentionally **not** an Odoo ``AbstractModel``:
    when a non-purchase document needs the same behaviour, lift this into an
    ``assignment.mixin`` parameterised by the three hooks below. See
    docs/adr/0001-assigned-officer-model.md and
    docs/adr/0006-pa-independent-assigned-officer.md.

    Each consuming model must declare:
      * a Many2one field to ``res.users`` holding the officer (name given by
        ``_assign_field``; defaults to ``assigned_to``),
      * the ``assignment_can_assign_me`` computed Boolean *with its own*
        ``@api.depends`` referring to the consumer's own field name, and
      * the two group hooks ``_assign_user_group`` / ``_assign_manager_group``.
    """

    # Empty slots: a plain mixin without ``__slots__`` would add a ``__dict__``
    # to the instance layout of the consuming Odoo model, breaking the
    # ``cls.__bases__`` reassignment Odoo performs in ``_prepare_setup``
    # ("object layout differs"). Odoo models are slotted, so we must be too.
    __slots__ = ()

    # Override per consuming model.
    _assign_field = "assigned_to"  # name of the res.users Many2one holding the officer
    _assign_user_group = None  # group allowed to self-claim unassigned work
    _assign_manager_group = None  # group allowed to assign others / unassign

    # -- accessors --------------------------------------------------------
    def _assignment_get_officer(self):
        self.ensure_one()
        return self[self._assign_field]

    def _assignment_set_officer(self, user):
        self.ensure_one()
        self[self._assign_field] = user

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
        officer = self._assignment_get_officer()
        if not officer:
            return True
        if officer == self.env.user:
            return False
        return self._assignment_is_manager() or self._assignment_takeover_allowed()

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
            officer = rec._assignment_get_officer()
            if officer == me:
                continue
            if not rec._assignment_can_claim():
                raise UserError(
                    _("This document is already assigned to %s.")
                    % officer.display_name
                )
            if officer:
                rec._assignment_clear_activity(officer)
            rec._assignment_set_officer(me)
            # Schedule a Todo for the assignee unconditionally so the doc lands
            # in their unified inbox (mail_activity_todo). See ADR-0001 note.
            rec._assignment_notify(me)
        return True

    def action_assignment_unassign(self):
        if not self._assignment_is_manager():
            raise AccessError(_("Only a manager can unassign the officer."))
        for rec in self:
            officer = rec._assignment_get_officer()
            if officer:
                rec._assignment_clear_activity(officer)
            rec._assignment_set_officer(self.env["res.users"])
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
