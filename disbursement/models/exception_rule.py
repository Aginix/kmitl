# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    disbursement_request_ids = fields.Many2many(
        comodel_name="disbursement.request",
        string="Disbursement Requests",
    )
    model = fields.Selection(
        selection_add=[
            ("disbursement.request", "Disbursement Requests"),
            ("disbursement.request.line", "Disbursement Requests line"),
        ],
        ondelete={
            "disbursement.request": "cascade",
            "disbursement.request.line": "cascade",
        },
    )
