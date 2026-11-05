# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    has_cheque = fields.Boolean(
        string="Cheque Payment",
        compute="_compute_has_cheque",
        store=True,
    )

    @api.depends("line_ids.payment_method")
    def _compute_has_cheque(self):
        for request in self:
            request.has_cheque = "cheque" in request.line_ids.mapped("payment_method")
