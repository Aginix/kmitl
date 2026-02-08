# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementExceptionConfirm(models.TransientModel):
    _name = "disbursement.exception.confirm"
    _description = "Disbursement Exception Wizard"
    _inherit = ["exception.rule.confirm"]

    related_model_id = fields.Many2one(
        "disbursement.request",
        "Disbursement Request",
    )

    def action_confirm(self):
        self.ensure_one()
        if self.ignore:
            self.related_model_id.action_draft()
            self.related_model_id.ignore_exception = True
            self.related_model_id.action_submit()
        return super().action_confirm()
