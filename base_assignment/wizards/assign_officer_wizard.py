# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class AssignOfficerWizard(models.TransientModel):
    _name = "assign.officer.wizard"
    _description = "Assign Officer"

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned Officer",
        required=True,
        domain="[('id', 'in', allowed_user_ids)]",
    )
    allowed_user_ids = fields.Many2many(
        comodel_name="res.users",
        compute="_compute_allowed_user_ids",
    )

    def _get_target_model_group_xmlid(self):
        """Read ``_assign_user_group`` off the target model. Raise a friendly
        error when the target model does not inherit ``assignment.mixin`` —
        otherwise a bare AttributeError would leak up to the user."""
        self.ensure_one()
        if not self.res_model:
            return None
        Model = self.env[self.res_model]
        group_xmlid = getattr(Model, "_assign_user_group", None)
        if not group_xmlid:
            raise UserError(_(
                "Model %(model)s does not support officer assignment."
            ) % {"model": self.res_model})
        return group_xmlid

    @api.depends("res_model")
    def _compute_allowed_user_ids(self):
        for wiz in self:
            users = self.env["res.users"]
            if wiz.res_model:
                group_xmlid = wiz._get_target_model_group_xmlid()
                group = self.env.ref(group_xmlid, raise_if_not_found=False)
                if group:
                    users = group.users
            wiz.allowed_user_ids = users

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get("res_model") and res.get("res_id") and "user_id" in fields_list:
            record = self.env[res["res_model"]].browse(res["res_id"])
            if record.assigned_to:
                res["user_id"] = record.assigned_to.id
        return res

    def action_assign(self):
        self.ensure_one()
        record = self.env[self.res_model].browse(self.res_id)
        if not self.env.user.has_group(record._assign_manager_group):
            raise AccessError(_("Only a manager can assign another officer."))
        old_officer = record.assigned_to
        record.assigned_to = self.user_id
        if old_officer and old_officer != self.user_id:
            record._assignment_clear_activity(old_officer)
        if self.user_id and self.user_id != self.env.user:
            record._assignment_notify(self.user_id)
        # Fire the lifecycle hook on the same path claim / unassign use so a
        # consumer can react to any assigned_to write without overriding both
        # the mixin action and the wizard.
        record._assignment_on_assigned(self.user_id, old_officer)
        return {"type": "ir.actions.act_window_close"}
