# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    is_student_payee = fields.Boolean(compute="_compute_is_student_payee")

    # Any line pays a student: the form then suggests the Excel import.
    @api.depends("line_ids.partner_type_id")
    def _compute_is_student_payee(self):
        student_type = self.env.ref("partner_type_kmitl.partner_type_student")
        for request in self:
            request.is_student_payee = student_type in request.line_ids.partner_type_id

    def action_open_student_import(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Import Students"),
            "res_model": "disbursement.student.import",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }
