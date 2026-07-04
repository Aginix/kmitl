# -*- coding: utf-8 -*-
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import frozendict, str2bool

# The activity scheduled on a document when an officer is assigned. A dedicated
# type (not mail.mail_activity_data_todo) so the Todo-inbox bridge can tag it
# with a todo_category without affecting every native To-Do in the system, and
# so _assignment_clear_activity never collides with user-scheduled To-Dos.
ASSIGN_ACTIVITY_XMLID = "procurement_assignment_kmitl.mail_activity_assignment"

# ir.config_parameter that relaxes the self-claim guard (see Purchase settings).
TAKEOVER_PARAM = "procurement_assignment_kmitl.allow_takeover_assigned"


class AssignmentMixin(models.AbstractModel):
    """Shared behaviour for documents carrying an Assigned Officer
    (เจ้าหน้าที่ผู้รับผิดชอบ), stored in ``assigned_to``.

    Inheriting this mixin auto-injects the assignment alert (Assign to me /
    Assign… / Unassign) above the form's sheet — mirroring how
    ``base_tier_validation`` injects its label via a ``get_view`` override —
    so consumers never edit their own form XML and the buttons stay out of
    the header's workflow buttons.

    Each consuming model must declare:
      * the ``assigned_to`` field (Many2one res.users) — not declared here, so
        ``purchase.request`` keeps the OCA field's attributes untouched, and
      * the two group hooks ``_assign_user_group`` / ``_assign_manager_group``.
    """

    _name = "assignment.mixin"
    _description = "Assigned Officer (mixin)"

    # Override per consuming model.
    _assign_user_group = None  # group allowed to self-claim unassigned work
    _assign_manager_group = None  # group allowed to assign others / unassign

    assignment_can_assign_me = fields.Boolean(
        compute="_compute_assignment_can_assign_me",
    )

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
        stale = self.activity_ids.filtered(
            lambda a: a.user_id == user and a.activity_type_id == activity_type
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

    # ------------------------------------------------------------------
    # Auto-inject the assignment alert above the sheet, following the
    # base_tier_validation label pattern (tier_validation.py get_view).
    # ------------------------------------------------------------------
    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != "form":
            return res
        if not (self._assign_user_group and self._assign_manager_group):
            return res
        doc = etree.XML(res["arch"])
        sheet_nodes = doc.xpath("/form/sheet")
        if not sheet_nodes:
            return res
        View = self.env["ir.ui.view"]
        rendered = self.env["ir.qweb"]._render(
            "procurement_assignment_kmitl.assignment_buttons_alert",
            {
                "user_group": self._assign_user_group,
                "manager_group": self._assign_manager_group,
            },
        )
        template_node = etree.fromstring(rendered)
        new_arch, new_models = View.postprocess_and_fields(template_node, self._name)
        template_node = etree.fromstring(new_arch)
        for sheet in sheet_nodes:
            for child in template_node:
                sheet.addprevious(child)
        all_models = dict(res["models"])
        for model, view_fields in new_models.items():
            if model in all_models:
                all_models[model] = tuple(set(all_models[model]) | set(view_fields))
            else:
                all_models[model] = tuple(view_fields)
        res["arch"] = etree.tostring(doc)
        res["models"] = frozendict(all_models)
        return res
