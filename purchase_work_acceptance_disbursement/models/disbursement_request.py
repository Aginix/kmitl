# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    wa_ids = fields.One2many(
        comodel_name="work.acceptance",
        inverse_name="disbursement_request_id",
        string="Work Acceptances",
        readonly=True,
    )

    wa_count = fields.Integer(
        compute="_compute_wa_count",
        store=True,
    )

    def _compute_wa_count(self):
        for rec in self:
            rec.wa_count = len(rec.wa_ids)

    def action_validate(self):
        """Override: mark WA as disbursed เมื่อ submitted → unlock สร้าง WA ใหม่ได้"""
        res = super().action_validate()
        for rec in self:
            if rec.wa_ids:
                rec.wa_ids.write({"is_disbursed": True})
        return res

    def action_draft(self):
        """Override: reset WA flag เมื่อ reset to draft"""
        res = super().action_draft()
        for rec in self:
            if rec.wa_ids:
                rec.wa_ids.write({"is_disbursed": False})
        return res

    def action_view_work_acceptances(self):
        self.ensure_one()
        if not self.wa_ids:
            raise UserError(_("No Work Acceptances linked to this request."))
        if len(self.wa_ids) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Work Acceptance"),
                "res_model": "work.acceptance",
                "view_mode": "form",
                "res_id": self.wa_ids.id,
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Work Acceptances"),
            "res_model": "work.acceptance",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.wa_ids.ids)],
            "target": "current",
        }
