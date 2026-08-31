# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    kmitl_receipt_ids = fields.Many2many(
        comodel_name="kmitl.receipt",
        string="Receipts",
    )
    model = fields.Selection(
        selection_add=[
            ("kmitl.receipt", "KMITL Receipt"),
        ],
        ondelete={"kmitl.receipt": "cascade"},
    )
