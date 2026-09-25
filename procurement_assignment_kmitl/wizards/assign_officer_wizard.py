# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class AssignOfficerWizard(models.TransientModel):
    _name = "assign.officer.wizard"
    _description = "Assign Procurement Officer"

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

    @api.depends("res_model")
    def _compute_allowed_user_ids(self):
        for wiz in self:
            users = self.env["res.users"]
            if wiz.res_model:
                group_xmlid = self.env[wiz.res_model]._assign_user_group
                group = self.env.ref(group_xmlid, raise_if_not_found=False)
                if group:
                    users = group.users
            wiz.allowed_user_ids = users

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get("res_model") and res.get("res_id") and "user_id" in fields_list:
            record = self.env[res["res_model"]].browse(res["res_id"])
            current_officer = record._assignment_get_officer()
            if current_officer:
                res["user_id"] = current_officer.id
        return res

    def action_assign(self):
        self.ensure_one()
        record = self.env[self.res_model].browse(self.res_id)
        if not self.env.user.has_group(record._assign_manager_group):
            raise AccessError(_("Only a manager can assign another officer."))
        old_officer = record._assignment_get_officer()
        record._assignment_set_officer(self.user_id)
        if old_officer and old_officer != self.user_id:
            record._assignment_clear_activity(old_officer)
        if self.user_id:
            record._assignment_notify(self.user_id)
        return {"type": "ir.actions.act_window_close"}
